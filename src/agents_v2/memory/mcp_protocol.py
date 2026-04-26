"""
MCP协议兼容的记忆服务

Model Context Protocol (MCP) 开放协议支持
用于AI应用与外部数据源和工具的连接
"""
import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass

from .types import MemoryType, MemoryEntry

if TYPE_CHECKING:
    from .unified import UnifiedMemoryManager


@dataclass
class MCPMemoryResource:
    """MCP记忆资源"""
    uri: str
    name: str
    memory_type: MemoryType
    description: str
    created_at: float
    updated_at: float


@dataclass
class MCPToolResult:
    """MCP工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class MCPMemoryProtocol:
    """
    MCP协议兼容的记忆服务

    支持:
    - 标准化接口 (符合MCP协议规范)
    - 跨应用记忆共享
    - 远程记忆检索
    - 资源注册和发现

    MCP资源 URI格式:
    - memory://user_profile/{user_id}
    - memory://session/{session_id}
    - memory://task/{task_id}
    - memory://procedure/{procedure_id}
    - memory://episodic/{episode_id}
    """

    def __init__(
        self,
        memory_manager: Optional["UnifiedMemoryManager"] = None,
        protocol_version: str = "1.0"
    ):
        self.memory_manager = memory_manager
        self.protocol_version = protocol_version
        self._registered_resources: Dict[str, MCPMemoryResource] = {}
        self._client_sessions: Dict[str, Dict[str, Any]] = {}  # client_id -> session info
        self._lock = asyncio.Lock()

    def get_protocol_info(self) -> Dict[str, Any]:
        """获取协议信息"""
        return {
            "protocol_version": self.protocol_version,
            "name": "MCP Memory Protocol",
            "description": "AI Memory System MCP Protocol",
            "capabilities": [
                "memory_search",
                "memory_create",
                "memory_update",
                "memory_delete",
                "memory_get_context",
                "resource_list",
                "resource_subscribe"
            ],
            "resource_types": [
                "user_profile",
                "session",
                "task",
                "procedure",
                "episodic",
                "short_term",
                "long_term"
            ]
        }

    # ========== 资源管理 ==========

    async def register_resource(
        self,
        uri: str,
        name: str,
        memory_type: MemoryType,
        description: str = ""
    ) -> bool:
        """
        注册MCP资源

        Args:
            uri: 资源URI (e.g., memory://user_profile/user_123)
            name: 资源名称
            memory_type: 记忆类型
            description: 描述

        Returns:
            是否成功
        """
        async with self._lock:
            resource = MCPMemoryResource(
                uri=uri,
                name=name,
                memory_type=memory_type,
                description=description,
                created_at=time.time(),
                updated_at=time.time()
            )
            self._registered_resources[uri] = resource
            return True

    async def list_resources(
        self,
        memory_type: Optional[MemoryType] = None
    ) -> List[MCPMemoryResource]:
        """
        列出已注册资源

        Args:
            memory_type: 可选的过滤条件

        Returns:
            资源列表
        """
        resources = list(self._registered_resources.values())

        if memory_type:
            resources = [r for r in resources if r.memory_type == memory_type]

        return resources

    async def get_resource(self, uri: str) -> Optional[MCPMemoryResource]:
        """获取指定URI的资源"""
        return self._registered_resources.get(uri)

    def parse_memory_uri(self, uri: str) -> Optional[Dict[str, str]]:
        """
        解析MCP URI

        Args:
            uri: memory://type/id

        Returns:
            {type, id} 或 None
        """
        if not uri.startswith("memory://"):
            return None

        parts = uri[9:].split("/", 1)
        if len(parts) != 2:
            return None

        return {"memory_type": parts[0], "id": parts[1]}

    # ========== 客户端会话 ==========

    async def create_client_session(
        self,
        client_id: str,
        client_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建客户端会话

        Args:
            client_id: 客户端ID
            client_info: 客户端信息

        Returns:
            会话信息
        """
        async with self._lock:
            session = {
                "client_id": client_id,
                "created_at": time.time(),
                "last_accessed": time.time(),
                "memory_count": 0,
                "info": client_info or {}
            }
            self._client_sessions[client_id] = session
            return session

    async def get_client_session(self, client_id: str) -> Optional[Dict[str, Any]]:
        """获取客户端会话"""
        session = self._client_sessions.get(client_id)
        if session:
            session["last_accessed"] = time.time()
        return session

    async def delete_client_session(self, client_id: str) -> bool:
        """删除客户端会话"""
        async with self._lock:
            if client_id in self._client_sessions:
                del self._client_sessions[client_id]
                return True
            return False

    # ========== 记忆操作 (MCP Tools) ==========

    async def create_memory(
        self,
        client_id: str,
        memory_type: MemoryType,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MCPToolResult:
        """
        创建记忆 (MCP tool: memory_create)

        Args:
            client_id: 客户端ID
            memory_type: 记忆类型
            key: 记忆键
            value: 记忆值
            tags: 标签
            importance: 重要性
            metadata: 元数据

        Returns:
            MCPToolResult
        """
        try:
            if not self.memory_manager:
                return MCPToolResult(
                    success=False,
                    error="Memory manager not initialized"
                )

            await self.memory_manager.remember(
                key=key,
                value=value,
                memory_type=memory_type,
                tags=tags,
                persist=True,
                importance=importance,
                metadata=metadata
            )

            # 更新会话统计
            if client_id in self._client_sessions:
                self._client_sessions[client_id]["memory_count"] += 1

            return MCPToolResult(
                success=True,
                data={"memory_id": key, "created": True}
            )

        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    async def get_memory(
        self,
        client_id: str,
        memory_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> MCPToolResult:
        """
        获取记忆 (MCP tool: memory_get)

        Args:
            client_id: 客户端ID
            memory_id: 记忆ID
            memory_type: 记忆类型

        Returns:
            MCPToolResult
        """
        try:
            if not self.memory_manager:
                return MCPToolResult(
                    success=False,
                    error="Memory manager not initialized"
                )

            # 根据memory_type获取
            result = await self.memory_manager.recall(memory_id)

            return MCPToolResult(success=True, data=result)

        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    async def update_memory(
        self,
        client_id: str,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> MCPToolResult:
        """
        更新记忆 (MCP tool: memory_update)

        Args:
            client_id: 客户端ID
            memory_id: 记忆ID
            updates: 更新内容 {value, tags, importance}

        Returns:
            MCPToolResult
        """
        try:
            if not self.memory_manager:
                return MCPToolResult(
                    success=False,
                    error="Memory manager not initialized"
                )

            # 获取现有值
            existing = await self.memory_manager.recall(memory_id)
            if not existing:
                return MCPToolResult(
                    success=False,
                    error=f"Memory {memory_id} not found"
                )

            # 更新
            new_value = updates.get("value", existing.content if hasattr(existing, 'content') else existing)
            new_tags = updates.get("tags", existing.tags if hasattr(existing, 'tags') else [])
            new_importance = updates.get("importance", existing.importance if hasattr(existing, 'importance') else 0.5)

            await self.memory_manager.remember(
                key=memory_id,
                value=new_value,
                tags=new_tags,
                persist=True,
                importance=new_importance
            )

            return MCPToolResult(
                success=True,
                data={"memory_id": memory_id, "updated": True}
            )

        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    async def delete_memory(
        self,
        client_id: str,
        memory_id: str
    ) -> MCPToolResult:
        """
        删除记忆 (MCP tool: memory_delete)

        Args:
            client_id: 客户端ID
            memory_id: 记忆ID

        Returns:
            MCPToolResult
        """
        try:
            if not self.memory_manager:
                return MCPToolResult(
                    success=False,
                    error="Memory manager not initialized"
                )

            # 调用记忆管理器的删除
            if hasattr(self.memory_manager, 'forget'):
                await self.memory_manager.forget(memory_id)
            else:
                return MCPToolResult(
                    success=False,
                    error="Delete not supported"
                )

            return MCPToolResult(
                success=True,
                data={"memory_id": memory_id, "deleted": True}
            )

        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    async def search_memories(
        self,
        client_id: str,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> MCPToolResult:
        """
        搜索记忆 (MCP tool: memory_search)

        Args:
            client_id: 客户端ID
            query: 搜索查询
            memory_types: 记忆类型列表
            limit: 返回数量
            filters: 过滤条件

        Returns:
            MCPToolResult
        """
        try:
            if not self.memory_manager:
                return MCPToolResult(
                    success=False,
                    error="Memory manager not initialized"
                )

            # 确定记忆类型
            mem_types = memory_types or [MemoryType.LONG_TERM]

            # 执行搜索
            results = await self.memory_manager.search(
                query=query,
                memory_types=mem_types,
                limit=limit,
                filters=filters
            )

            # 转换结果
            result_data = []
            for entry in results:
                result_data.append({
                    "memory_id": entry.id if hasattr(entry, 'id') else str(entry),
                    "content": entry.content if hasattr(entry, 'content') else str(entry),
                    "memory_type": entry.memory_type.value if hasattr(entry, 'memory_type') else "unknown",
                    "importance": entry.importance if hasattr(entry, 'importance') else 0.5,
                    "tags": entry.tags if hasattr(entry, 'tags') else []
                })

            return MCPToolResult(success=True, data=result_data)

        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    async def list_memories(
        self,
        client_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100
    ) -> MCPToolResult:
        """
        列出记忆 (MCP tool: memory_list)

        Args:
            client_id: 客户端ID
            memory_type: 记忆类型
            limit: 返回数量

        Returns:
            MCPToolResult
        """
        try:
            if not self.memory_manager:
                return MCPToolResult(
                    success=False,
                    error="Memory manager not initialized"
                )

            # 获取会话信息
            session = self._client_sessions.get(client_id)

            # 根据memory_type获取记忆
            if memory_type == MemoryType.SHORT_TERM:
                if hasattr(self.memory_manager, 'short_term'):
                    entries = await self.memory_manager.short_term.get_recent(limit)
                else:
                    entries = []
            elif memory_type == MemoryType.SESSION:
                if hasattr(self.memory_manager, 'session'):
                    messages = await self.memory_manager.session.get_messages(limit=limit)
                    entries = messages
                else:
                    entries = []
            elif memory_type == MemoryType.LONG_TERM:
                if hasattr(self.memory_manager, 'long_term'):
                    results = await self.memory_manager.long_term.search("", limit=limit)
                    entries = results
                else:
                    entries = []
            else:
                entries = []

            return MCPToolResult(success=True, data=entries)

        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    async def get_context_for_agent(
        self,
        client_id: str,
        agent_id: str,
        task_id: str,
        max_tokens: int = 4096
    ) -> MCPToolResult:
        """
        获取Agent上下文 (MCP tool: memory_get_context)

        Args:
            client_id: 客户端ID
            agent_id: Agent ID
            task_id: 任务ID
            max_tokens: 最大token数

        Returns:
            MCPToolResult
        """
        try:
            if not self.memory_manager:
                return MCPToolResult(
                    success=False,
                    error="Memory manager not initialized"
                )

            context = await self.memory_manager.get_context_for_agent(
                agent_id=agent_id,
                task_id=task_id,
                max_tokens=max_tokens
            )

            return MCPToolResult(success=True, data={"context": context})

        except Exception as e:
            return MCPToolResult(success=False, error=str(e))

    # ========== 订阅功能 ==========

    async def subscribe_to_changes(
        self,
        client_id: str,
        memory_type: MemoryType,
        callback: Optional[callable] = None
    ) -> str:
        """
        订阅记忆变更

        Args:
            client_id: 客户端ID
            memory_type: 记忆类型
            callback: 回调函数

        Returns:
            订阅ID
        """
        subscription_id = str(uuid.uuid4())

        # 存储订阅信息
        async with self._lock:
            if f"_subscriptions_{client_id}" not in dir():
                setattr(self, f"_subscriptions_{client_id}", [])

            subscriptions = getattr(self, f"_subscriptions_{client_id}")
            subscriptions.append({
                "subscription_id": subscription_id,
                "memory_type": memory_type,
                "callback": callback,
                "created_at": time.time()
            })

        return subscription_id

    async def unsubscribe(self, client_id: str, subscription_id: str) -> bool:
        """
        取消订阅

        Args:
            client_id: 客户端ID
            subscription_id: 订阅ID

        Returns:
            是否成功
        """
        subscriptions = getattr(self, f"_subscriptions_{client_id}", [])
        subscriptions = [s for s in subscriptions if s["subscription_id"] != subscription_id]
        setattr(self, f"_subscriptions_{client_id}", subscriptions)
        return True

    # ========== 统计信息 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取协议统计"""
        return {
            "protocol_version": self.protocol_version,
            "registered_resources": len(self._registered_resources),
            "active_sessions": len(self._client_sessions),
            "supported_memory_types": [mt.value for mt in MemoryType]
        }
