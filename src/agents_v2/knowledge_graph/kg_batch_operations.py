"""
知识图谱批量操作模块

功能:
1. 批量导入优化 (Batch Import)
2. 事务管理 (Transaction Management)
3. 增量更新 (Incremental Update)
4. CDC支持 (Change Data Capture)
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from src.agents_v2.logging_config import get_logging_logger

import asyncio

logger = get_logging_logger(__name__)


class BatchMode(str, Enum):
    """批量模式"""
    AUTO = "auto"           # 自动选择最佳模式
    TRANSACTION = "transaction"  # 事务批量
    PERIODIC_COMMIT = "periodic_commit"  # 周期性提交
    PARALLEL = "parallel"  # 并行批量


@dataclass
class BatchResult:
    """批量操作结果"""
    total: int
    success: int
    failed: int
    duration_ms: float
    errors: List[Dict] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.success / self.total


@dataclass
class IncrementalUpdate:
    """增量更新"""
    entity_id: str
    entity_type: str
    operation: str  # "upsert", "delete", "touch"
    timestamp: float
    changes: Dict[str, Any] = None

    def __post_init__(self):
        if self.changes is None:
            self.changes = {}


class BatchImporter:
    """
    批量导入器

    优化策略:
    1. 单事务批量：适用于小批量（<1000）
    2. 周期性提交：适用于大批量，防止内存溢出
    3. 并行导入：多线程/多进程导入
    """

    def __init__(
        self,
        neo4j_driver,
        batch_size: int = 1000,
        commit_interval_ms: int = 10000,
        mode: BatchMode = BatchMode.AUTO
    ):
        """
        Args:
            neo4j_driver: Neo4j driver
            batch_size: 每批处理数量
            commit_interval_ms: 提交间隔（毫秒）
            mode: 批量模式
        """
        self.driver = neo4j_driver
        self.batch_size = batch_size
        self.commit_interval_ms = commit_interval_ms
        self.mode = mode

    async def import_entities(
        self,
        entities: List[Tuple[str, str, Dict]],
        use_merge: bool = True
    ) -> BatchResult:
        """
        批量导入实体

        Args:
            entities: [(entity_id, entity_type, properties), ...]
            use_merge: 是否使用MERGE（false则用CREATE）

        Returns:
            BatchResult
        """
        import time
        start = time.time()
        success = 0
        failed = 0
        errors = []

        if use_merge:
            query = """
                UNWIND $batch AS row
                MERGE (e:Entity {entity_id: row.entity_id})
                SET e.entity_type = row.entity_type,
                    e += row.properties,
                    e.created_at = coalesce(e.created_at, timestamp()),
                    e.updated_at = timestamp()
                RETURN count(e) AS count
            """
        else:
            query = """
                UNWIND $batch AS row
                CREATE (e:Entity {entity_id: row.entity_id, entity_type: row.entity_type})
                SET e += row.properties
                RETURN count(e) AS count
            """

        try:
            with self.driver.session() as session:
                # 分批处理
                for i in range(0, len(entities), self.batch_size):
                    batch = entities[i:i + self.batch_size]
                    batch_data = [
                        {
                            "entity_id": e[0],
                            "entity_type": e[1],
                            "properties": e[2]
                        }
                        for e in batch
                    ]

                    result = session.run(query, batch=batch_data)
                    count = result.single()[0]
                    success += count

        except Exception as e:
            logger.error(f"Batch import error: {e}")
            failed = len(entities) - success
            errors.append({"batch": i // self.batch_size, "error": str(e)})

        duration_ms = (time.time() - start) * 1000
        return BatchResult(
            total=len(entities),
            success=success,
            failed=failed,
            duration_ms=duration_ms,
            errors=errors
        )

    async def import_relations(
        self,
        relations: List[Tuple[str, str, str, Dict]],
        use_merge: bool = True
    ) -> BatchResult:
        """
        批量导入关系

        Args:
            relations: [(source_id, target_id, relation_type, properties), ...]

        Returns:
            BatchResult
        """
        import time
        start = time.time()
        success = 0
        failed = 0
        errors = []

        if use_merge:
            query = """
                UNWIND $batch AS row
                MATCH (source:Entity {entity_id: row.source_id})
                MATCH (target:Entity {entity_id: row.target_id})
                MERGE (source)-[r:RELATES_TO {type: row.relation_type}]->(target)
                SET r += row.properties,
                    r.created_at = coalesce(r.created_at, timestamp())
                RETURN count(r) AS count
            """
        else:
            query = """
                UNWIND $batch AS row
                MATCH (source:Entity {entity_id: row.source_id})
                MATCH (target:Entity {entity_id: row.target_id})
                CREATE (source)-[r:RELATES_TO {type: row.relation_type}]->(target)
                SET r += row.properties
                RETURN count(r) AS count
            """

        try:
            with self.driver.session() as session:
                for i in range(0, len(relations), self.batch_size):
                    batch = relations[i:i + self.batch_size]
                    batch_data = [
                        {
                            "source_id": r[0],
                            "target_id": r[1],
                            "relation_type": r[2],
                            "properties": r[3]
                        }
                        for r in batch
                    ]

                    result = session.run(query, batch=batch_data)
                    count = result.single()[0]
                    success += count

        except Exception as e:
            logger.error(f"Relation batch import error: {e}")
            failed = len(relations) - success
            errors.append({"batch": i // self.batch_size, "error": str(e)})

        duration_ms = (time.time() - start) * 1000
        return BatchResult(
            total=len(relations),
            success=success,
            failed=failed,
            duration_ms=duration_ms,
            errors=errors
        )

    async def import_graph_parallel(
        self,
        entities: List[Tuple[str, str, Dict]],
        relations: List[Tuple[str, str, str, Dict]],
        max_workers: int = 4
    ) -> Tuple[BatchResult, BatchResult]:
        """
        并行导入实体和关系

        Args:
            entities: 实体列表
            relations: 关系列表
            max_workers: 最大并行数

        Returns:
            (entity_result, relation_result)
        """
        import concurrent.futures

        async def run_import():
            entity_result = await self.import_entities(entities)
            relation_result = await self.import_relations(relations)
            return entity_result, relation_result

        # 使用线程池并行执行
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future = loop.run_in_executor(executor, asyncio.run, run_import())
            return await asyncio.wrap_future(future)


class IncrementalUpdater:
    """
    增量更新器

    支持:
    1. 基于时间戳的增量同步
    2. 变更检测 (CDC)
    3. 软删除
    """

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver

    async def detect_changes(
        self,
        since_timestamp: float,
        entity_ids: Optional[List[str]] = None
    ) -> List[IncrementalUpdate]:
        """
        检测自上次同步以来的变更

        Args:
            since_timestamp: 上次同步时间戳
            entity_ids: 可选，限定检查的实体ID

        Returns:
            变更列表
        """
        changes = []

        query = """
            MATCH (e:Entity)
            WHERE e.updated_at > $since
        """

        if entity_ids:
            query += " AND e.entity_id IN $entity_ids"

        query += " RETURN e.entity_id AS entity_id, e.entity_type AS entity_type, e.updated_at AS updated_at"

        params = {"since": since_timestamp}
        if entity_ids:
            params["entity_ids"] = entity_ids

        try:
            with self.driver.session() as session:
                result = session.run(query, **params)
                for record in result:
                    changes.append(IncrementalUpdate(
                        entity_id=record["entity_id"],
                        entity_type=record["entity_type"],
                        operation="upsert",
                        timestamp=record["updated_at"]
                    ))
        except Exception as e:
            logger.error(f"Change detection error: {e}")

        return changes

    async def apply_updates(
        self,
        updates: List[IncrementalUpdate]
    ) -> BatchResult:
        """
        应用增量更新

        Args:
            updates: 增量更新列表

        Returns:
            BatchResult
        """
        import time
        start = time.time()
        success = 0
        failed = 0
        errors = []

        for update in updates:
            try:
                if update.operation == "delete":
                    await self._soft_delete(update.entity_id)
                elif update.operation == "touch":
                    await self._touch_entity(update.entity_id)
                else:  # upsert
                    await self._update_properties(
                        update.entity_id,
                        update.changes
                    )
                success += 1
            except Exception as e:
                logger.error(f"Update error for {update.entity_id}: {e}")
                failed += 1
                errors.append({"entity_id": update.entity_id, "error": str(e)})

        duration_ms = (time.time() - start) * 1000
        return BatchResult(
            total=len(updates),
            success=success,
            failed=failed,
            duration_ms=duration_ms,
            errors=errors
        )

    async def _soft_delete(self, entity_id: str) -> None:
        """软删除：标记删除"""
        with self.driver.session() as session:
            session.run("""
                MATCH (e:Entity {entity_id: $entity_id})
                SET e.deleted = true,
                    e.deleted_at = timestamp()
            """, entity_id=entity_id)

    async def _touch_entity(self, entity_id: str) -> None:
        """更新实体的时间戳"""
        with self.driver.session() as session:
            session.run("""
                MATCH (e:Entity {entity_id: $entity_id})
                SET e.updated_at = timestamp()
            """, entity_id=entity_id)

    async def _update_properties(
        self,
        entity_id: str,
        properties: Dict[str, Any]
    ) -> None:
        """更新实体属性"""
        if not properties:
            return

        set_clause = ", ".join([f"e.{k} = ${k}" for k in properties.keys()])
        params = {"entity_id": entity_id, **properties}

        with self.driver.session() as session:
            session.run(f"""
                MATCH (e:Entity {{entity_id: $entity_id}})
                SET {set_clause},
                    e.updated_at = timestamp()
            """, **params)

    async def cleanup_deleted(
        self,
        retention_days: int = 30
    ) -> int:
        """
        清理已删除的实体

        Args:
            retention_days: 保留天数

        Returns:
            删除数量
        """
        cutoff = datetime.now().timestamp() - (retention_days * 86400)

        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Entity)
                WHERE e.deleted = true AND e.deleted_at < $cutoff
                DETACH DELETE e
                RETURN count(e) AS count
            """, cutoff=cutoff)

            return result.single()[0]


class TransactionManager:
    """
    事务管理器

    提供:
    1. 自动重试
    2. 死锁处理
    3. 超时控制
    """

    def __init__(
        self,
        neo4j_driver,
        max_retries: int = 3,
        retry_delay_ms: int = 100,
        timeout_seconds: int = 30
    ):
        self.driver = neo4j_driver
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms
        self.timeout_seconds = timeout_seconds

    async def execute_with_retry(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        带重试的事务执行

        Args:
            operation: 要执行的操作（异步函数）
            *args, **kwargs: 操作参数

        Returns:
            操作结果
        """
        import asyncio

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with self.driver.session() as session:
                    # 设置超时
                    result = await asyncio.wait_for(
                        operation(session, *args, **kwargs),
                        timeout=self.timeout_seconds
                    )
                    return result

            except Exception as e:
                last_error = e
                logger.warning(f"Transaction attempt {attempt + 1} failed: {e}")

                # 检查是否是可重试的错误
                if not self._is_retryable(e):
                    raise

                # 等待后重试
                await asyncio.sleep(self.retry_delay_ms / 1000)

        raise last_error

    def _is_retryable(self, error: Exception) -> bool:
        """判断错误是否可重试"""
        retryable_messages = [
            "deadlock",
            "lock",
            "timeout",
            "temporary failure"
        ]

        error_str = str(error).lower()
        return any(msg in error_str for msg in retryable_messages)

    async def execute_batch(
        self,
        operations: List[Tuple[str, Dict]]
    ) -> BatchResult:
        """
        批量执行操作

        Args:
            operations: [(cypher_query, params), ...]

        Returns:
            BatchResult
        """
        import time
        start = time.time()
        success = 0
        failed = 0
        errors = []

        try:
            with self.driver.session() as session:
                for i, (query, params) in enumerate(operations):
                    try:
                        session.run(query, **params)
                        success += 1
                    except Exception as e:
                        failed += 1
                        errors.append({
                            "operation": i,
                            "error": str(e)
                        })

        except Exception as e:
            logger.error(f"Batch execution error: {e}")
            errors.append({"batch": -1, "error": str(e)})

        duration_ms = (time.time() - start) * 1000
        return BatchResult(
            total=len(operations),
            success=success,
            failed=failed,
            duration_ms=duration_ms,
            errors=errors
        )
