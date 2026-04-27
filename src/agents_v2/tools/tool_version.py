"""
Tool Version Management - 工具版本管理

支持工具的版本控制、热更新和回滚。
"""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    """版本状态"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass
class ToolVersion:
    """工具版本"""
    version: str
    tool_func: Callable
    schema: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    status: VersionStatus = VersionStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0
    success_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Tool:
    """工具定义"""
    tool_id: str
    name: str
    description: str
    category: str = ""
    versions: List[ToolVersion] = field(default_factory=list)
    current_version: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolVersionManager:
    """
    工具版本管理器

    功能:
    - 注册工具和版本
    - 版本切换
    - 热更新
    - 回滚

    使用示例:
        manager = ToolVersionManager()

        # 注册工具
        manager.register_tool(
            tool_id="search",
            name="文献搜索",
            tool_func=search_func,
            version="1.0.0"
        )

        # 添加新版本
        manager.add_version("search", search_func_v2, "2.0.0")

        # 切换版本
        manager.switch_version("search", "2.0.0")
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register_tool(
        self,
        tool_id: str,
        name: str,
        tool_func: Callable,
        version: str = "1.0.0",
        description: str = "",
        category: str = "",
        schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        注册工具

        Args:
            tool_id: 工具ID
            name: 工具名称
            tool_func: 工具函数
            version: 版本号
            description: 描述
            category: 类别
            schema: 参数schema
            metadata: 元数据
        """
        tool_version = ToolVersion(
            version=version,
            tool_func=tool_func,
            schema=schema or {},
            description=description
        )

        tool = Tool(
            tool_id=tool_id,
            name=name,
            description=description,
            category=category,
            versions=[tool_version],
            current_version=version,
            metadata=metadata or {}
        )

        self._tools[tool_id] = tool
        logger.info(f"Registered tool: {tool_id} v{version}")

    def add_version(
        self,
        tool_id: str,
        tool_func: Callable,
        version: str,
        description: str = "",
        schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加新版本

        Returns:
            bool: 是否成功
        """
        tool = self._tools.get(tool_id)
        if not tool:
            logger.error(f"Tool not found: {tool_id}")
            return False

        # 检查版本是否已存在
        if any(v.version == version for v in tool.versions):
            logger.warning(f"Version {version} already exists for {tool_id}")
            return False

        tool_version = ToolVersion(
            version=version,
            tool_func=tool_func,
            schema=schema or {},
            description=description
        )

        tool.versions.append(tool_version)
        logger.info(f"Added version {version} to tool: {tool_id}")
        return True

    def switch_version(self, tool_id: str, version: str) -> bool:
        """切换版本"""
        tool = self._tools.get(tool_id)
        if not tool:
            logger.error(f"Tool not found: {tool_id}")
            return False

        # 检查版本是否存在
        if not any(v.version == version for v in tool.versions):
            logger.error(f"Version {version} not found for {tool_id}")
            return False

        tool.current_version = version
        logger.info(f"Switched {tool_id} to version {version}")
        return True

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(tool_id)

    def get_current_version(self, tool_id: str) -> Optional[ToolVersion]:
        """获取当前版本"""
        tool = self._tools.get(tool_id)
        if not tool or not tool.current_version:
            return None

        return next(
            (v for v in tool.versions if v.version == tool.current_version),
            None
        )

    def get_version(self, tool_id: str, version: str) -> Optional[ToolVersion]:
        """获取指定版本"""
        tool = self._tools.get(tool_id)
        if not tool:
            return None

        return next((v for v in tool.versions if v.version == version), None)

    def deprecate_version(self, tool_id: str, version: str) -> bool:
        """弃用版本"""
        tool_version = self.get_version(tool_id, version)
        if not tool_version:
            return False

        tool_version.status = VersionStatus.DEPRECATED
        logger.info(f"Deprecated {tool_id} v{version}")
        return True

    def retire_version(self, tool_id: str, version: str) -> bool:
        """退休版本"""
        tool_version = self.get_version(tool_id, version)
        if not tool_version:
            return False

        tool_version.status = VersionStatus.RETIRED
        logger.info(f"Retired {tool_id} v{version}")
        return True

    def rollback(self, tool_id: str) -> Optional[str]:
        """
        回滚到上一个版本

        Returns:
            Optional[str]: 回滚到的版本号
        """
        tool = self._tools.get(tool_id)
        if not tool:
            return None

        # 获取按时间排序的版本
        sorted_versions = sorted(
            tool.versions,
            key=lambda v: v.created_at,
            reverse=True
        )

        # 找到当前版本的前一个
        current_idx = None
        for i, v in enumerate(sorted_versions):
            if v.version == tool.current_version:
                current_idx = i
                break

        if current_idx is None or current_idx + 1 >= len(sorted_versions):
            logger.warning(f"No previous version to rollback to for {tool_id}")
            return None

        previous_version = sorted_versions[current_idx + 1]
        tool.current_version = previous_version.version

        logger.info(f"Rolled back {tool_id} to v{previous_version.version}")
        return previous_version.version

    def record_usage(
        self,
        tool_id: str,
        version: Optional[str] = None,
        success: bool = True
    ) -> None:
        """记录工具使用"""
        if version:
            tool_version = self.get_version(tool_id, version)
        else:
            tool_version = self.get_current_version(tool_id)

        if not tool_version:
            return

        tool_version.usage_count += 1

        # 更新成功率
        n = tool_version.usage_count
        if success:
            tool_version.success_rate = (
                tool_version.success_rate * (n - 1) + 1.0
            ) / n
        else:
            tool_version.success_rate = (
                tool_version.success_rate * (n - 1)
            ) / n

    def get_tool_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """获取工具信息"""
        tool = self._tools.get(tool_id)
        if not tool:
            return None

        current = self.get_current_version(tool_id)

        return {
            "tool_id": tool.tool_id,
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "current_version": tool.current_version,
            "version_count": len(tool.versions),
            "versions": [
                {
                    "version": v.version,
                    "status": v.status.value,
                    "usage_count": v.usage_count,
                    "success_rate": v.success_rate,
                    "created_at": v.created_at
                }
                for v in tool.versions
            ],
            "current_version_info": {
                "usage_count": current.usage_count if current else 0,
                "success_rate": current.success_rate if current else 0
            } if current else None
        }

    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        """列出工具"""
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def list_versions(self, tool_id: str) -> List[str]:
        """列出版本"""
        tool = self._tools.get(tool_id)
        if not tool:
            return []
        return [v.version for v in tool.versions]


def create_version_manager() -> ToolVersionManager:
    """创建版本管理器"""
    return ToolVersionManager()
