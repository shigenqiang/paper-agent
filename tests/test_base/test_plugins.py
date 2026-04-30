"""
插件系统测试
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.agents_v2.core.plugins import (
    PluginType,
    PluginState,
    PluginMetadata,
    PluginInfo,
    PluginInterface,
    AgentPlugin,
    ToolPlugin,
    PluginSandbox,
    PluginManager,
    PluginError,
    SecurityError,
    agent_plugin,
    tool_plugin,
    get_plugin_manager
)


class TestPluginMetadata:
    """测试插件元数据"""

    def test_metadata_creation(self):
        """测试元数据创建"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            plugin_type=PluginType.TOOL,
            entry_point="TestPlugin",
            tags=["test", "demo"]
        )

        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.plugin_type == PluginType.TOOL


class TestPluginInfo:
    """测试插件信息"""

    def test_info_creation(self):
        """测试信息创建"""
        metadata = PluginMetadata(
            name="test",
            version="1.0",
            description="Test",
            author="Author",
            plugin_type=PluginType.AGENT,
            entry_point="Test"
        )

        info = PluginInfo(
            metadata=metadata,
            state=PluginState.UNLOADED
        )

        assert info.state == PluginState.UNLOADED
        assert info.loaded_at is None


class TestPluginSandbox:
    """测试插件沙箱"""

    def test_sandbox_execution(self):
        """测试沙箱执行"""
        sandbox = PluginSandbox()

        code = "result = 2 + 2"
        result = sandbox.execute_code(code)

        assert result == 4

    def test_sandbox_with_context(self):
        """测试带上下文的执行"""
        sandbox = PluginSandbox()

        code = "result = x * y"
        context = {"x": 3, "y": 4}
        result = sandbox.execute_code(code, context)

        assert result == 12

    def test_sandbox_forbidden_import(self):
        """测试禁止的导入"""
        sandbox = PluginSandbox()

        code = "import os\nresult = os.system('ls')"

        with pytest.raises(SecurityError):
            sandbox.execute_code(code)

    def test_sandbox_forbidden_function(self):
        """测试禁止的函数"""
        sandbox = PluginSandbox()

        code = "result = eval('2+2')"

        with pytest.raises(SecurityError):
            sandbox.execute_code(code)

    def test_restricted_mode(self):
        """测试限制模式"""
        sandbox = PluginSandbox()
        sandbox._restricted = True

        with pytest.raises(SecurityError):
            sandbox.execute_code("result = 1 + 1")


class MockAgentPlugin(AgentPlugin):
    """模拟Agent插件"""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mock_agent",
            version="1.0.0",
            description="A mock agent plugin",
            author="Test",
            plugin_type=PluginType.AGENT,
            entry_point="MockAgentPlugin"
        )

    def initialize(self, config) -> bool:
        return True

    def activate(self) -> bool:
        return True

    def deactivate(self) -> bool:
        return True

    def create_agent(self, config):
        return MagicMock()


class MockToolPlugin(ToolPlugin):
    """模拟工具插件"""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mock_tool",
            version="1.0.0",
            description="A mock tool plugin",
            author="Test",
            plugin_type=PluginType.TOOL,
            entry_point="MockToolPlugin"
        )

    def initialize(self, config) -> bool:
        return True

    def activate(self) -> bool:
        return True

    def deactivate(self) -> bool:
        return True

    def get_tool_spec(self):
        return MagicMock()


class TestPluginManager:
    """测试插件管理器"""

    @pytest.fixture
    def manager(self):
        """创建测试用插件管理器"""
        return PluginManager(plugin_dir=None)

    def test_manager_init(self, manager):
        """测试管理器初始化"""
        assert manager._initialized is False
        assert len(manager._plugins) == 0

    @pytest.mark.asyncio
    async def test_register_plugin(self, manager):
        """测试插件注册"""
        plugin = MockAgentPlugin()
        result = await manager.register_plugin(plugin)

        assert result is True
        assert "mock_agent" in manager._plugins

    @pytest.mark.asyncio
    async def test_load_plugin(self, manager):
        """测试插件加载"""
        await manager.register_plugin(MockAgentPlugin())
        result = await manager.load_plugin("mock_agent")

        assert result is True
        assert manager._plugins["mock_agent"].state == PluginState.LOADED

    @pytest.mark.asyncio
    async def test_activate_plugin(self, manager):
        """测试插件激活"""
        await manager.register_plugin(MockAgentPlugin())
        result = await manager.activate_plugin("mock_agent")

        assert result is True
        assert manager._plugins["mock_agent"].state == PluginState.ACTIVE

    @pytest.mark.asyncio
    async def test_deactivate_plugin(self, manager):
        """测试插件停用"""
        await manager.register_plugin(MockAgentPlugin())
        await manager.activate_plugin("mock_agent")
        result = await manager.deactivate_plugin("mock_agent")

        assert result is True
        assert manager._plugins["mock_agent"].state == PluginState.LOADED

    @pytest.mark.asyncio
    async def test_uninstall_plugin(self, manager):
        """测试插件卸载"""
        await manager.register_plugin(MockAgentPlugin())
        await manager.activate_plugin("mock_agent")
        result = await manager.uninstall_plugin("mock_agent")

        assert result is True
        assert "mock_agent" not in manager._plugins

    @pytest.mark.asyncio
    async def test_plugin_not_found(self, manager):
        """测试插件不存在"""
        result = await manager.load_plugin("nonexistent")
        assert result is False

    def test_list_plugins(self, manager):
        """测试列出插件"""
        assert manager.list_plugins() == []

    def test_get_plugin_info(self, manager):
        """测试获取插件信息"""
        info = manager.get_plugin_info("nonexistent")
        assert info is None


class TestDecorators:
    """测试装饰器"""

    def test_agent_plugin_decorator(self):
        """测试agent插件装饰器"""
        @agent_plugin(
            name="test_agent",
            version="1.0.0",
            description="Test agent",
            author="Test Author",
            tags=["test"]
        )
        class TestAgent(AgentPlugin):
            def get_metadata(self):
                return self._plugin_metadata
            def initialize(self, config):
                return True
            def activate(self):
                return True
            def deactivate(self):
                return True
            def create_agent(self, config):
                return MagicMock()

        assert TestAgent._plugin_metadata.name == "test_agent"
        assert TestAgent._plugin_metadata.plugin_type == PluginType.AGENT

    def test_tool_plugin_decorator(self):
        """测试tool插件装饰器"""
        @tool_plugin(
            name="test_tool",
            version="1.0.0",
            description="Test tool",
            author="Test Author",
            category="test"
        )
        class TestTool(ToolPlugin):
            def get_metadata(self):
                return self._plugin_metadata
            def initialize(self, config):
                return True
            def activate(self):
                return True
            def deactivate(self):
                return True
            def get_tool_spec(self):
                return MagicMock()

        assert TestTool._plugin_metadata.name == "test_tool"
        assert TestTool._plugin_metadata.plugin_type == PluginType.TOOL
        assert "test" in TestTool._plugin_metadata.tags


class TestPluginHooks:
    """测试插件钩子"""

    @pytest.mark.asyncio
    async def test_hook_registration(self):
        """测试钩子注册"""
        manager = PluginManager()
        hook_called = []

        def test_callback(plugin_name):
            hook_called.append(plugin_name)

        manager.register_hook('on_plugin_activated', test_callback)

        await manager.register_plugin(MockAgentPlugin())
        await manager.activate_plugin("mock_agent")

        assert "mock_agent" in hook_called


class TestPluginStates:
    """测试插件状态"""

    def test_all_states(self):
        """测试所有状态枚举"""
        assert PluginState.UNLOADED.value == "unloaded"
        assert PluginState.LOADING.value == "loading"
        assert PluginState.LOADED.value == "loaded"
        assert PluginState.ACTIVE.value == "active"
        assert PluginState.DISABLED.value == "disabled"
        assert PluginState.ERROR.value == "error"


class TestPluginTypes:
    """测试插件类型"""

    def test_all_types(self):
        """测试所有类型枚举"""
        assert PluginType.AGENT.value == "agent"
        assert PluginType.TOOL.value == "tool"
        assert PluginType.MEMORY.value == "memory"
        assert PluginType.RETRIEVER.value == "retriever"
        assert PluginType.OUTPUT_FORMAT.value == "output_format"
        assert PluginType.VALIDATOR.value == "validator"
        assert PluginType.CUSTOM.value == "custom"


class TestGlobalManager:
    """测试全局管理器"""

    def test_get_plugin_manager(self):
        """测试获取全局管理器"""
        # 重置全局实例
        import src.agents_v2.core.plugins as plugins_module
        plugins_module._plugin_manager = None

        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()

        assert manager1 is manager2
        assert isinstance(manager1, PluginManager)