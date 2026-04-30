"""
MCP Client 单元测试
"""
import pytest
from src.agents_v2._archive.mcp.client import (
    MCPClient,
    MCPClientPool,
    MCPConnectionState,
    MCPMessage
)


class TestMCPMessage:
    """MCPMessage 测试"""

    def test_create_message(self):
        """测试创建消息"""
        msg = MCPMessage(id="1", method="test", params={"key": "value"})
        assert msg.id == "1"
        assert msg.method == "test"
        assert msg.params["key"] == "value"

    def test_message_with_result(self):
        """测试带结果的消息"""
        msg = MCPMessage(id="1", method="test", result={"status": "ok"})
        assert msg.result["status"] == "ok"

    def test_message_with_error(self):
        """测试带错误的消息"""
        msg = MCPMessage(id="1", method="test", error="Something went wrong")
        assert msg.error == "Something went wrong"


class TestMCPClient:
    """MCPClient 测试"""

    def test_client_init(self):
        """测试客户端初始化"""
        client = MCPClient(url="http://localhost:8080")
        assert client.url == "http://localhost:8080"
        assert client.state == MCPConnectionState.DISCONNECTED
        assert client.timeout == 30.0
        assert client.max_retries == 3

    def test_client_custom_config(self):
        """测试自定义配置"""
        client = MCPClient(
            url="http://localhost:8080",
            timeout=60.0,
            max_retries=5,
            heartbeat_interval=60.0
        )
        assert client.timeout == 60.0
        assert client.max_retries == 5
        assert client.heartbeat_interval == 60.0

    @pytest.mark.asyncio
    async def test_connect(self):
        """测试连接"""
        client = MCPClient(url="http://localhost:8080")
        result = await client.connect()
        assert result is True
        assert client.state == MCPConnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """测试断开连接"""
        client = MCPClient(url="http://localhost:8080")
        await client.connect()
        await client.disconnect()
        assert client.state == MCPConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_send_request(self):
        """测试发送请求"""
        client = MCPClient(url="http://localhost:8080")
        await client.connect()

        result = await client.send_request("test_method", {"param": "value"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_double_connect(self):
        """测试重复连接"""
        client = MCPClient(url="http://localhost:8080")
        await client.connect()
        await client.connect()  # 应该直接返回
        assert client.state == MCPConnectionState.CONNECTED

    def test_next_message_id(self):
        """测试消息ID生成"""
        client = MCPClient(url="http://localhost:8080")
        id1 = client._next_message_id()
        id2 = client._next_message_id()
        assert id1 != id2
        assert id1 == "msg_1"
        assert id2 == "msg_2"

    def test_get_stats(self):
        """测试获取统计信息"""
        client = MCPClient(url="http://localhost:8080")
        stats = client.get_stats()

        assert stats["url"] == "http://localhost:8080"
        assert stats["state"] == "disconnected"
        assert stats["message_id"] == 0
        assert stats["pending_requests"] == 0


class TestMCPClientPool:
    """MCPClientPool 测试"""

    def test_pool_init(self):
        """测试池初始化"""
        pool = MCPClientPool()
        assert len(pool._clients) == 0

    def test_add_client(self):
        """测试添加客户端"""
        pool = MCPClientPool()
        client = pool.add_client("test", "http://localhost:8080")

        assert client is not None
        assert client.url == "http://localhost:8080"
        assert pool.get_client("test") is client

    def test_get_client(self):
        """测试获取客户端"""
        pool = MCPClientPool()
        pool.add_client("test", "http://localhost:8080")

        client = pool.get_client("test")
        assert client is not None

    def test_get_client_not_found(self):
        """测试获取不存在的客户端"""
        pool = MCPClientPool()
        client = pool.get_client("nonexistent")
        assert client is None

    def test_get_connected_client(self):
        """测试获取已连接的客户端"""
        pool = MCPClientPool()
        pool.add_client("test1", "http://localhost:8080")
        pool.add_client("test2", "http://localhost:8081")

        # 默认没有连接的客户端
        client = pool.get_connected_client()
        assert client is None

    def test_list_clients(self):
        """测试列出客户端"""
        pool = MCPClientPool()
        pool.add_client("test1", "http://localhost:8080")
        pool.add_client("test2", "http://localhost:8081")

        names = pool.list_clients()
        assert "test1" in names
        assert "test2" in names
        assert len(names) == 2

    @pytest.mark.asyncio
    async def test_connect_all(self):
        """测试连接所有客户端"""
        pool = MCPClientPool()
        pool.add_client("test1", "http://localhost:8080")
        pool.add_client("test2", "http://localhost:8081")

        count = await pool.connect_all()
        assert count == 2

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """测试断开所有连接"""
        pool = MCPClientPool()
        pool.add_client("test1", "http://localhost:8080")

        await pool.connect_all()
        await pool.disconnect_all()

        # 所有客户端应该已断开
        for name in pool.list_clients():
            client = pool.get_client(name)
            assert client.state == MCPConnectionState.DISCONNECTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])