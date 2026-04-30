"""
MCP Client - MCP协议客户端

Model Context Protocol客户端实现。
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MCPConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPMessage:
    """MCP消息"""
    id: str
    method: str
    params: Dict[str, Any] = None
    result: Any = None
    error: str = ""


class MCPClient:
    """MCP协议客户端

    支持:
    - 连接管理
    - 心跳检测
    - 请求/响应
    - 自动重连
    """

    def __init__(
        self,
        url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        heartbeat_interval: float = 30.0
    ):
        """初始化MCP客户端

        Args:
            url: MCP服务器URL
            timeout: 请求超时时间
            max_retries: 最大重试次数
            heartbeat_interval: 心跳间隔
        """
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self.heartbeat_interval = heartbeat_interval

        self._state = MCPConnectionState.DISCONNECTED
        self._message_id = 0
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_heartbeat: float = 0

    @property
    def state(self) -> MCPConnectionState:
        """获取连接状态"""
        return self._state

    async def connect(self) -> bool:
        """连接到MCP服务器

        Returns:
            bool: 连接是否成功
        """
        if self._state == MCPConnectionState.CONNECTED:
            return True

        try:
            self._state = MCPConnectionState.CONNECTING
            logger.info(f"Connecting to MCP server: {self.url}")

            # 模拟连接（实际应使用WebSocket或HTTP）
            await asyncio.sleep(0.1)  # 模拟网络延迟

            self._state = MCPConnectionState.CONNECTED
            self._start_heartbeat()
            logger.info(f"Connected to MCP server: {self.url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self._state = MCPConnectionState.ERROR
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        self._stop_heartbeat()

        if self._state != MCPConnectionState.DISCONNECTED:
            logger.info(f"Disconnecting from MCP server: {self.url}")
            self._state = MCPConnectionState.DISCONNECTED

    async def send_request(
        self,
        method: str,
        params: Optional[Dict] = None
    ) -> Any:
        """发送请求

        Args:
            method: 方法名
            params: 参数

        Returns:
            Any: 响应结果

        Raises:
            TimeoutError: 请求超时
            ConnectionError: 连接错误
        """
        if self._state != MCPConnectionState.CONNECTED:
            if not await self.connect():
                raise ConnectionError("Not connected to MCP server")

        message_id = self._next_message_id()
        message = MCPMessage(id=message_id, method=method, params=params or {})

        try:
            # 模拟发送请求并直接返回
            logger.debug(f"Sending MCP request: {method}")
            await asyncio.sleep(0.05)  # 模拟网络延迟

            # 模拟成功响应
            return {"status": "ok", "method": method}

        except asyncio.TimeoutError:
            logger.error(f"MCP request timeout: {method}")
            raise TimeoutError(f"Request {method} timed out")
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            raise ConnectionError(f"Request failed: {e}")

    def _next_message_id(self) -> str:
        """生成下一个消息ID"""
        self._message_id += 1
        return f"msg_{self._message_id}"

    def _start_heartbeat(self) -> None:
        """启动心跳"""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def _stop_heartbeat(self) -> None:
        """停止心跳"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._state == MCPConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

    async def _send_heartbeat(self) -> None:
        """发送心跳"""
        try:
            await self.send_request("ping", {})
            self._last_heartbeat = asyncio.get_event_loop().time()
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
            # 可能需要重连
            await self._handle_disconnect()

    async def _handle_disconnect(self) -> None:
        """处理断开连接"""
        self._state = MCPConnectionState.DISCONNECTED
        # 尝试重连
        for attempt in range(self.max_retries):
            if await self.connect():
                return
            await asyncio.sleep(2 ** attempt)  # 指数退避

        self._state = MCPConnectionState.ERROR

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict containing connection stats
        """
        return {
            "state": self._state.value,
            "url": self.url,
            "message_id": self._message_id,
            "pending_requests": len(self._pending_requests),
            "last_heartbeat": self._last_heartbeat
        }


class MCPClientPool:
    """MCP客户端池

    管理多个MCP客户端，支持负载均衡。
    """

    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}

    def add_client(self, name: str, url: str, **kwargs) -> MCPClient:
        """添加客户端

        Args:
            name: 客户端名称
            url: 服务器URL
            **kwargs: 客户端配置

        Returns:
            MCPClient instance
        """
        client = MCPClient(url, **kwargs)
        self._clients[name] = client
        return client

    def get_client(self, name: str) -> Optional[MCPClient]:
        """获取客户端

        Args:
            name: 客户端名称

        Returns:
            MCPClient or None
        """
        return self._clients.get(name)

    def get_connected_client(self) -> Optional[MCPClient]:
        """获取已连接的客户端（负载均衡）

        Returns:
            MCPClient or None
        """
        for client in self._clients.values():
            if client.state == MCPConnectionState.CONNECTED:
                return client
        return None

    async def connect_all(self) -> int:
        """连接所有客户端

        Returns:
            Number of successfully connected clients
        """
        count = 0
        for client in self._clients.values():
            if await client.connect():
                count += 1
        return count

    async def disconnect_all(self) -> None:
        """断开所有连接"""
        for client in self._clients.values():
            await client.disconnect()

    def list_clients(self) -> List[str]:
        """列出所有客户端名称"""
        return list(self._clients.keys())
