"""
Plugin System - 插件扩展机制

功能：
- 插件接口定义
- 插件注册与管理
- 动态插件加载
- 插件沙箱执行
- 插件生命周期管理
"""
from typing import Any, Callable, Dict, List, Optional, Protocol, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import importlib
import importlib.util
import os
import sys
import json
import logging
import hashlib
from pathlib import Path
import tempfile
import ast

logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """插件类型"""
    AGENT = "agent"                    # Agent插件
    TOOL = "tool"                      # 工具插件
    MEMORY = "memory"                  # 记忆插件
    RETRIEVER = "retriever"           # 检索插件
    OUTPUT_FORMAT = "output_format"   # 输出格式插件
    VALIDATOR = "validator"           # 验证器插件
    CUSTOM = "custom"                 # 自定义插件


class PluginState(str, Enum):
    """插件状态"""
    UNLOADED = "unloaded"     # 未加载
    LOADING = "loading"        # 加载中
    LOADED = "loaded"          # 已加载
    ACTIVE = "active"          # 激活
    DISABLED = "disabled"       # 禁用
    ERROR = "error"             # 错误


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str                    # 入口函数/类
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    config_schema: Optional[Dict] = None
    min_system_version: str = "1.0"    # 最低系统版本


@dataclass
class PluginInfo:
    """插件信息"""
    metadata: PluginMetadata
    state: PluginState
    loaded_at: Optional[float] = None
    error_message: Optional[str] = None
    instance: Optional[Any] = None


class PluginInterface(ABC):
    """
    插件接口基类

    所有插件必须实现此接口
    """

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化插件

        Args:
            config: 插件配置

        Returns:
            是否初始化成功
        """
        pass

    @abstractmethod
    def activate(self) -> bool:
        """
        激活插件

        Returns:
            是否激活成功
        """
        pass

    @abstractmethod
    def deactivate(self) -> bool:
        """
        停用插件

        Returns:
            是否停用成功
        """
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证插件配置

        Args:
            config: 待验证的配置

        Returns:
            配置是否有效
        """
        return True


class AgentPlugin(PluginInterface):
    """
    Agent插件基类

    用于扩展Agent功能
    """

    @abstractmethod
    def create_agent(self, config: Dict[str, Any]) -> Any:
        """创建Agent实例"""
        pass


class ToolPlugin(PluginInterface):
    """
    工具插件基类

    用于扩展工具功能
    """

    @abstractmethod
    def get_tool_spec(self) -> Any:  # ToolSpec
        """获取工具规格"""
        pass


class PluginSandbox:
    """
    插件沙箱

    提供安全的插件执行环境
    """

    ALLOWED_MODULES = {
        'typing', 'datetime', 'time', 'json', 're', 'math',
        'collections', 'itertools', 'functools', 'operator',
        'pathlib', 'uuid', 'hashlib', 'base64'
    }

    def __init__(self, allowed_modules: Optional[set] = None):
        self.allowed_modules = allowed_modules or self.ALLOWED_MODULES.copy()
        self._restricted = False

    def execute_code(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        在沙箱中执行代码

        Args:
            code: 待执行的代码
            context: 执行上下文

        Returns:
            执行结果
        """
        if self._restricted:
            raise SecurityError("Sandbox is in restricted mode")

        # 代码安全检查
        self._validate_code(code)

        # 创建安全的执行环境
        safe_globals = {
            '__builtins__': self._get_safe_builtins(),
            '__name__': '__plugin_sandbox__'
        }

        safe_locals = context or {}

        try:
            exec(code, safe_globals, safe_locals)
            return safe_locals.get('result')
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            raise

    def _validate_code(self, code: str) -> None:
        """验证代码安全性"""
        forbidden = [
            'import os', 'import sys', 'import subprocess',
            'import socket', 'import requests', 'import urllib',
            '__import__', 'eval', 'exec', 'open(', 'file(',
            'os.system', 'os.popen', 'subprocess', 'socket.socket'
        ]

        code_lower = code.lower()
        for pattern in forbidden:
            if pattern.lower() in code_lower:
                raise SecurityError(f"Forbidden pattern detected: {pattern}")

    def _get_safe_builtins(self) -> Dict:
        """获取安全的内置函数"""
        safe_builtins = {}
        for name in dir(__builtins__):
            if name in ('print', 'len', 'range', 'str', 'int', 'float',
                       'list', 'dict', 'set', 'tuple', 'bool', 'type',
                       'isinstance', 'issubclass', 'hasattr', 'getattr',
                       'setattr', 'sorted', 'reversed', 'enumerate', 'zip',
                       'map', 'filter', 'sum', 'min', 'max', 'abs', 'round',
                       'any', 'all', 'format', 'chr', 'ord'):
                safe_builtins[name] = getattr(__builtins__, name)
        return safe_builtins


class SecurityError(Exception):
    """安全错误"""
    pass


class PluginManager:
    """
    插件管理器

    统一管理插件的加载、激活、停用和卸载
    """

    def __init__(self, plugin_dir: Optional[str] = None):
        self._plugins: Dict[str, PluginInfo] = {}
        self._plugin_dir = plugin_dir or self._get_default_plugin_dir()
        self._sandbox = PluginSandbox()
        self._hooks: Dict[str, List[Callable]] = {}  # 插件钩子
        self._initialized = False

    def _get_default_plugin_dir(self) -> str:
        """获取默认插件目录"""
        return os.path.join(os.path.dirname(__file__), "plugins")

    async def initialize(self) -> bool:
        """
        初始化插件管理器

        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True

        try:
            # 创建插件目录
            os.makedirs(self._plugin_dir, exist_ok=True)

            # 加载预定义插件
            await self._load_builtin_plugins()

            # 扫描并加载插件
            await self._scan_and_load_plugins()

            self._initialized = True
            logger.info(f"Plugin manager initialized with {len(self._plugins)} plugins")
            return True

        except Exception as e:
            logger.error(f"Plugin manager initialization failed: {e}")
            return False

    async def _load_builtin_plugins(self) -> None:
        """加载内置插件"""
        try:
            from .builtin_plugins import WebSearchPlugin, PDFParserPlugin, CitationPlugin
            for plugin_cls in [WebSearchPlugin, PDFParserPlugin, CitationPlugin]:
                await self.register_plugin(plugin_cls())
        except ImportError:
            logger.debug("Built-in plugins not available")

    async def _scan_and_load_plugins(self) -> None:
        """扫描并加载插件目录中的插件"""
        if not os.path.exists(self._plugin_dir):
            return

        for filename in os.listdir(self._plugin_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                plugin_path = os.path.join(self._plugin_dir, filename)
                await self._load_plugin_from_file(plugin_path)

    async def _load_plugin_from_file(self, plugin_path: str) -> bool:
        """
        从文件加载插件

        Args:
            plugin_path: 插件文件路径

        Returns:
            是否加载成功
        """
        try:
            module_name = os.path.basename(plugin_path)[:-3]

            # 使用importlib动态加载
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # 查找插件类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, PluginInterface) and
                        attr is not PluginInterface):
                        await self.register_plugin(attr())
                        return True

            return False

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            return False

    async def register_plugin(self, plugin: PluginInterface) -> bool:
        """
        注册插件

        Args:
            plugin: 插件实例

        Returns:
            是否注册成功
        """
        try:
            metadata = plugin.get_metadata()

            if metadata.name in self._plugins:
                logger.warning(f"Plugin {metadata.name} already registered, replacing")

            plugin_info = PluginInfo(
                metadata=metadata,
                state=PluginState.UNLOADED,
                instance=plugin
            )

            self._plugins[metadata.name] = plugin_info
            logger.info(f"Registered plugin: {metadata.name} v{metadata.version}")

            return True

        except Exception as e:
            logger.error(f"Plugin registration failed: {e}")
            return False

    async def load_plugin(self, name: str) -> bool:
        """
        加载插件

        Args:
            name: 插件名称

        Returns:
            是否加载成功
        """
        plugin_info = self._plugins.get(name)
        if not plugin_info:
            logger.error(f"Plugin not found: {name}")
            return False

        if plugin_info.state not in (PluginState.UNLOADED, PluginState.DISABLED):
            logger.warning(f"Plugin {name} is already loaded")
            return True

        try:
            plugin_info.state = PluginState.LOADING

            # 验证依赖
            deps_result = self._verify_dependencies(plugin_info)
            if asyncio.iscoroutine(deps_result):
                deps_result = await deps_result
            if not deps_result:
                raise DependencyError(f"Dependencies not satisfied for {name}")

            # 初始化插件
            if hasattr(plugin_info.instance, 'initialize'):
                config = self._get_plugin_config(name)
                init_result = plugin_info.instance.initialize(config)
                if asyncio.iscoroutine(init_result):
                    init_result = await init_result
                if not init_result:
                    raise PluginError(f"Plugin {name} initialization failed")

            plugin_info.state = PluginState.LOADED
            plugin_info.loaded_at = None  # 可以添加时间戳
            logger.info(f"Loaded plugin: {name}")

            # 触发钩子
            await self._trigger_hook('on_plugin_loaded', name)

            return True

        except Exception as e:
            plugin_info.state = PluginState.ERROR
            plugin_info.error_message = str(e)
            logger.error(f"Failed to load plugin {name}: {e}")
            return False

    async def activate_plugin(self, name: str) -> bool:
        """
        激活插件

        Args:
            name: 插件名称

        Returns:
            是否激活成功
        """
        plugin_info = self._plugins.get(name)
        if not plugin_info:
            logger.error(f"Plugin not found: {name}")
            return False

        if plugin_info.state == PluginState.ACTIVE:
            return True

        if plugin_info.state != PluginState.LOADED:
            # 自动加载
            if not await self.load_plugin(name):
                return False

        try:
            if hasattr(plugin_info.instance, 'activate'):
                act_result = plugin_info.instance.activate()
                if asyncio.iscoroutine(act_result):
                    act_result = await act_result
                if not act_result:
                    raise PluginError(f"Plugin {name} activation failed")

            plugin_info.state = PluginState.ACTIVE
            logger.info(f"Activated plugin: {name}")

            # 触发钩子
            await self._trigger_hook('on_plugin_activated', name)

            return True

        except Exception as e:
            logger.error(f"Failed to activate plugin {name}: {e}")
            return False

    async def deactivate_plugin(self, name: str) -> bool:
        """
        停用插件

        Args:
            name: 插件名称

        Returns:
            是否停用成功
        """
        plugin_info = self._plugins.get(name)
        if not plugin_info:
            return True  # 不存在的插件视为已停用

        if plugin_info.state != PluginState.ACTIVE:
            return True

        try:
            if hasattr(plugin_info.instance, 'deactivate'):
                deact_result = plugin_info.instance.deactivate()
                if asyncio.iscoroutine(deact_result):
                    deact_result = await deact_result
                if not deact_result:
                    raise PluginError(f"Plugin {name} deactivation failed")

            plugin_info.state = PluginState.LOADED
            logger.info(f"Deactivated plugin: {name}")

            # 触发钩子
            await self._trigger_hook('on_plugin_deactivated', name)

            return True

        except Exception as e:
            logger.error(f"Failed to deactivate plugin {name}: {e}")
            return False

    async def uninstall_plugin(self, name: str) -> bool:
        """
        卸载插件

        Args:
            name: 插件名称

        Returns:
            是否卸载成功
        """
        if name not in self._plugins:
            return True

        # 先停用
        await self.deactivate_plugin(name)

        del self._plugins[name]
        logger.info(f"Uninstalled plugin: {name}")

        # 触发钩子
        await self._trigger_hook('on_plugin_uninstalled', name)

        return True

    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """获取插件实例"""
        info = self._plugins.get(name)
        return info.instance if info else None

    def get_plugin_info(self, name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._plugins.get(name)

    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        state: Optional[PluginState] = None
    ) -> List[PluginInfo]:
        """
        列出插件

        Args:
            plugin_type: 按类型过滤
            state: 按状态过滤

        Returns:
            插件信息列表
        """
        plugins = list(self._plugins.values())

        if plugin_type:
            plugins = [p for p in plugins if p.metadata.plugin_type == plugin_type]

        if state:
            plugins = [p for p in plugins if p.state == state]

        return plugins

    def register_hook(self, event: str, callback: Callable) -> None:
        """
        注册插件钩子

        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    async def _trigger_hook(self, event: str, *args, **kwargs) -> None:
        """触发插件钩子"""
        callbacks = self._hooks.get(event, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook callback failed for {event}: {e}")

    async def _verify_dependencies(self, plugin_info: PluginInfo) -> bool:
        """验证插件依赖"""
        for dep in plugin_info.metadata.dependencies:
            if dep not in self._plugins:
                return False
            dep_info = self._plugins[dep]
            if dep_info.state != PluginState.ACTIVE:
                return False
        return True

    def _get_plugin_config(self, name: str) -> Dict[str, Any]:
        """获取插件配置"""
        # 从配置文件加载（如果有）
        config_path = os.path.join(self._plugin_dir, f"{name}.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    async def execute_in_sandbox(
        self,
        plugin_name: str,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        在沙箱中执行插件代码

        Args:
            plugin_name: 插件名称
            code: 待执行的代码
            context: 执行上下文

        Returns:
            执行结果
        """
        plugin_info = self._plugins.get(plugin_name)
        if not plugin_info or plugin_info.state != PluginState.ACTIVE:
            raise PluginError(f"Plugin {plugin_name} is not active")

        return self._sandbox.execute_code(code, context)


class PluginError(Exception):
    """插件错误"""
    pass


class DependencyError(Exception):
    """依赖错误"""
    pass


# 全局插件管理器实例
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


# 便捷装饰器
def agent_plugin(
    name: str,
    version: str,
    description: str,
    author: str,
    tags: Optional[List[str]] = None
):
    """
    Agent插件装饰器

    用法:
        @agent_plugin(
            name="my_agent",
            version="1.0.0",
            description="My custom agent",
            author="Author Name"
        )
        class MyAgent(AgentPlugin):
            ...
    """
    def decorator(cls):
        cls._plugin_metadata = PluginMetadata(
            name=name,
            version=version,
            description=description,
            author=author,
            plugin_type=PluginType.AGENT,
            entry_point=cls.__name__,
            tags=tags or []
        )
        return cls
    return decorator


def tool_plugin(
    name: str,
    version: str,
    description: str,
    author: str,
    category: str = "general"
):
    """
    工具插件装饰器

    用法:
        @tool_plugin(
            name="my_tool",
            version="1.0.0",
            description="My custom tool",
            author="Author Name",
            category="custom"
        )
        class MyTool(ToolPlugin):
            ...
    """
    def decorator(cls):
        cls._plugin_metadata = PluginMetadata(
            name=name,
            version=version,
            description=description,
            author=author,
            plugin_type=PluginType.TOOL,
            entry_point=cls.__name__,
            tags=[category]
        )
        return cls
    return decorator


# 导入需要的模块
import asyncio