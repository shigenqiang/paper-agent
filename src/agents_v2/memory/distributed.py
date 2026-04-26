"""
分布式记忆系统 - Distributed Memory System

提供:
- DistributedMemoryManager: 分布式记忆管理器
- MemoryNode: 记忆节点
- NodeRegistry: 节点注册表
- LoadBalancer: 负载均衡器
"""
import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import json

if TYPE_CHECKING:
    from .unified import UnifiedMemoryManager


class NodeStatus(Enum):
    """节点状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"


@dataclass
class MemoryNode:
    """记忆节点"""
    node_id: str
    host: str
    port: int
    status: NodeStatus = NodeStatus.ACTIVE
    weight: int = 1  # 权重(用于负载均衡)
    last_heartbeat: float = field(default_factory=time.time)
    memory_capacity: int = 10000  # 可存储的记忆数量
    current_load: int = 0  # 当前负载


@dataclass
class DistributedOperationResult:
    """分布式操作结果"""
    success: bool
    node_id: Optional[str] = None
    data: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0


class LoadBalancer:
    """
    负载均衡器

    支持:
    - Round Robin
    - Weighted Round Robin
    - Least Loaded
    """

    def __init__(self, strategy: str = "weighted_round_robin"):
        self._strategy = strategy
        self._round_robin_index: Dict[str, int] = {}  # node_id -> index

    def select_node(self, nodes: List[MemoryNode], key: Optional[str] = None) -> Optional[MemoryNode]:
        """
        选择节点

        Args:
            nodes: 可用节点列表
            key: 记忆键(用于一致性哈希)

        Returns:
            选中的节点
        """
        active_nodes = [n for n in nodes if n.status == NodeStatus.ACTIVE]

        if not active_nodes:
            return None

        if self._strategy == "round_robin":
            return self._round_robin(active_nodes)
        elif self._strategy == "weighted_round_robin":
            return self._weighted_round_robin(active_nodes)
        elif self._strategy == "least_loaded":
            return self._least_loaded(active_nodes)
        else:
            return active_nodes[0]

    def _round_robin(self, nodes: List[MemoryNode]) -> MemoryNode:
        """Round Robin"""
        if not nodes:
            return None

        node = nodes[0]
        return node

    def _weighted_round_robin(self, nodes: List[MemoryNode]) -> MemoryNode:
        """加权Round Robin"""
        if not nodes:
            return None

        # 简单实现:按权重选择
        total_weight = sum(n.weight for n in nodes)
        if total_weight == 0:
            return nodes[0]

        # 模拟加权随机选择
        import random
        r = random.randint(0, total_weight - 1)
        cumulative = 0
        for node in nodes:
            cumulative += node.weight
            if r < cumulative:
                return node

        return nodes[0]

    def _least_loaded(self, nodes: List[MemoryNode]) -> MemoryNode:
        """最少加载"""
        if not nodes:
            return None

        return min(nodes, key=lambda n: n.current_load / n.memory_capacity if n.memory_capacity > 0 else 1)


class NodeRegistry:
    """
    节点注册表

    职责:
    - 节点注册/注销
    - 健康检查
    - 节点发现
    """

    def __init__(self, heartbeat_interval: float = 10.0):
        self._nodes: Dict[str, MemoryNode] = {}
        self._heartbeat_interval = heartbeat_interval
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def register_node(self, node: MemoryNode) -> bool:
        """
        注册节点

        Args:
            node: 节点信息

        Returns:
            是否成功
        """
        async with self._lock:
            node.last_heartbeat = time.time()
            self._nodes[node.node_id] = node
            return True

    async def unregister_node(self, node_id: str) -> bool:
        """
        注销节点

        Args:
            node_id: 节点ID

        Returns:
            是否成功
        """
        async with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                return True
            return False

    async def get_node(self, node_id: str) -> Optional[MemoryNode]:
        """获取节点"""
        return self._nodes.get(node_id)

    async def get_active_nodes(self) -> List[MemoryNode]:
        """获取活跃节点"""
        async with self._lock:
            return [
                n for n in self._nodes.values()
                if n.status == NodeStatus.ACTIVE
            ]

    async def health_check(self, node_id: str) -> bool:
        """
        健康检查

        Args:
            node_id: 节点ID

        Returns:
            是否健康
        """
        node = await self.get_node(node_id)
        if not node:
            return False

        # 检查心跳超时
        if time.time() - node.last_heartbeat > self._heartbeat_interval * 3:
            return False

        return True

    async def update_heartbeat(self, node_id: str) -> None:
        """更新心跳"""
        async with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].last_heartbeat = time.time()

    async def start_health_checker(self) -> None:
        """启动健康检查"""
        async def checker():
            while True:
                try:
                    async with self._lock:
                        for node_id, node in self._nodes.items():
                            if time.time() - node.last_heartbeat > self._heartbeat_interval * 3:
                                node.status = NodeStatus.INACTIVE

                    await asyncio.sleep(self._heartbeat_interval)
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

        self._health_check_task = asyncio.create_task(checker())

    async def stop_health_checker(self) -> None:
        """停止健康检查"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass


class DistributedMemoryManager:
    """
    分布式记忆管理器

    职责:
    - 跨节点数据分片
    - 负载均衡
    - 故障转移
    """

    def __init__(
        self,
        registry: Optional[NodeRegistry] = None,
        load_balancer: Optional[LoadBalancer] = None
    ):
        self._registry = registry or NodeRegistry()
        self._load_balancer = load_balancer or LoadBalancer()
        self._local_node_id = "local_node"
        self._local_memory: Dict[str, Any] = {}
        self._operations: Dict[str, asyncio.Lock] = {}  # key -> lock

    async def remember(
        self,
        key: str,
        value: Any,
        node_hint: Optional[str] = None,
        memory_type: str = "default"
    ) -> DistributedOperationResult:
        """
        存储记忆

        Args:
            key: 记忆键
            value: 记忆值
            node_hint: 节点提示
            memory_type: 记忆类型

        Returns:
            操作结果
        """
        start_time = time.perf_counter()

        try:
            # 确定目标节点
            nodes = await self._registry.get_active_nodes()
            node = None

            if node_hint:
                node = await self._registry.get_node(node_hint)
            elif nodes:
                node = self._load_balancer.select_node(nodes, key)

            if node and node.node_id != self._local_node_id:
                # 远程节点操作(模拟)
                return await self._remote_remember(node, key, value, memory_type)
            else:
                # 本地操作
                return await self._local_remember(key, value, memory_type, start_time)

        except Exception as e:
            return DistributedOperationResult(
                success=False,
                error=str(e),
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

    async def _local_remember(
        self,
        key: str,
        value: Any,
        memory_type: str,
        start_time: float
    ) -> DistributedOperationResult:
        """本地存储"""
        # 获取或创建操作的锁
        if key not in self._operations:
            self._operations[key] = asyncio.Lock()

        async with self._operations[key]:
            self._local_memory[key] = {
                "value": value,
                "type": memory_type,
                "timestamp": time.time()
            }

        return DistributedOperationResult(
            success=True,
            node_id=self._local_node_id,
            latency_ms=(time.perf_counter() - start_time) * 1000
        )

    async def _remote_remember(
        self,
        node: MemoryNode,
        key: str,
        value: Any,
        memory_type: str
    ) -> DistributedOperationResult:
        """远程存储(模拟)"""
        # 实际应该使用RPC调用远程节点
        # 这里模拟远程调用
        return DistributedOperationResult(
            success=True,
            node_id=node.node_id,
            latency_ms=10.0  # 模拟网络延迟
        )

    async def recall(
        self,
        key: str,
        memory_type: str = "default"
    ) -> DistributedOperationResult:
        """
        检索记忆

        Args:
            key: 记忆键
            memory_type: 记忆类型

        Returns:
            操作结果
        """
        start_time = time.perf_counter()

        try:
            # 本地查找
            if key in self._local_memory:
                entry = self._local_memory[key]
                if memory_type == "default" or entry["type"] == memory_type:
                    return DistributedOperationResult(
                        success=True,
                        node_id=self._local_node_id,
                        data=entry["value"],
                        latency_ms=(time.perf_counter() - start_time) * 1000
                    )

            # 远程查找(模拟)
            nodes = await self._registry.get_active_nodes()
            for node in nodes:
                if node.node_id != self._local_node_id:
                    # 模拟远程查找
                    return DistributedOperationResult(
                        success=False,
                        node_id=node.node_id,
                        error="Key not found",
                        latency_ms=(time.perf_counter() - start_time) * 1000
                    )

            return DistributedOperationResult(
                success=False,
                error="Key not found",
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

        except Exception as e:
            return DistributedOperationResult(
                success=False,
                error=str(e),
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

    async def search(
        self,
        query: str,
        memory_types: Optional[List[str]] = None
    ) -> DistributedOperationResult:
        """
        搜索记忆(跨节点)

        Args:
            query: 查询字符串
            memory_types: 记忆类型过滤

        Returns:
            操作结果
        """
        start_time = time.perf_counter()

        try:
            results = []

            # 本地搜索
            for key, entry in self._local_memory.items():
                if query.lower() in str(entry["value"]).lower():
                    if not memory_types or entry["type"] in memory_types:
                        results.append({
                            "key": key,
                            "value": entry["value"],
                            "type": entry["type"],
                            "node_id": self._local_node_id
                        })

            # 跨节点聚合(模拟)
            # 实际应该并发查询所有节点

            return DistributedOperationResult(
                success=True,
                data=results,
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

        except Exception as e:
            return DistributedOperationResult(
                success=False,
                error=str(e),
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

    async def delete(self, key: str) -> DistributedOperationResult:
        """
        删除记忆

        Args:
            key: 记忆键

        Returns:
            操作结果
        """
        start_time = time.perf_counter()

        try:
            if key in self._local_memory:
                del self._local_memory[key]

            return DistributedOperationResult(
                success=True,
                node_id=self._local_node_id,
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

        except Exception as e:
            return DistributedOperationResult(
                success=False,
                error=str(e),
                latency_ms=(time.perf_counter() - start_time) * 1000
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "local_node_id": self._local_node_id,
            "local_memory_size": len(self._local_memory),
            "active_nodes": len(asyncio.all_tasks()),
            "total_operations": sum(1 for _ in self._operations)
        }


class ConsistentHashing:
    """
    一致性哈希(用于分布式记忆)

    优点:
    - 节点增减时最小化数据迁移
    - 支持虚拟节点提高负载均衡
    """

    def __init__(self, virtual_nodes: int = 100):
        self._virtual_nodes = virtual_nodes
        self._ring: Dict[int, str] = {}  # hash -> node_id
        self._sorted_keys: List[int] = []

    def add_node(self, node_id: str) -> None:
        """添加节点"""
        for i in range(self._virtual_nodes):
            key = self._hash(f"{node_id}:{i}")
            self._ring[key] = node_id
            self._sorted_keys.append(key)

        self._sorted_keys.sort()

    def remove_node(self, node_id: str) -> None:
        """移除节点"""
        keys_to_remove = []
        for key, nid in self._ring.items():
            if nid == node_id:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._ring[key]
            self._sorted_keys.remove(key)

    def get_node(self, key: str) -> Optional[str]:
        """获取key对应的节点"""
        if not self._ring:
            return None

        key_hash = self._hash(key)

        # 二分查找第一个 >= key_hash的位置
        for ring_key in self._sorted_keys:
            if ring_key >= key_hash:
                return self._ring[ring_key]

        # 回到第一个节点
        return self._ring[self._sorted_keys[0]]

    def _hash(self, key: str) -> int:
        """哈希函数"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
