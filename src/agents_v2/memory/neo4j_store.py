"""
Neo4j图数据库集成

提供实体关系图存储和遍历
"""
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


@dataclass
class GraphEntity:
    """图实体"""
    entity_id: str
    entity_type: str
    properties: Dict[str, Any]
    created_at: float


@dataclass
class GraphRelation:
    """图关系"""
    source_id: str
    target_id: str
    relation_type: str
    properties: Dict[str, Any]


class Neo4jGraphStore:
    """
    Neo4j图存储

    功能:
    - 实体管理
    - 关系管理
    - 路径查询
    - 子图遍历
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = None
    ):
        self.uri = uri
        self.user = user
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._driver = None

    def _get_driver(self):
        """获取驱动"""
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j not installed. Run: pip install neo4j")

        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
        return self._driver

    def close(self) -> None:
        """关闭驱动"""
        if self._driver:
            self._driver.close()
            self._driver = None

    async def initialize(self) -> None:
        """初始化约束和索引"""
        driver = self._get_driver()
        with driver.session() as session:
            # 创建约束
            session.run("""
                CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity)
                REQUIRE e.entity_id IS UNIQUE
            """)

            session.run("""
                CREATE INDEX IF NOT EXISTS FOR (e:Entity)
                ON (e.entity_type)
            """)

            session.run("""
                CREATE INDEX IF NOT EXISTS FOR (e:Entity)
                ON (e.entity_id)
            """)

    async def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加实体

        Args:
            entity_id: 实体ID
            entity_type: 实体类型 (agent/task/memory/concept)
            properties: 属性

        Returns:
            是否成功
        """
        driver = self._get_driver()
        properties = properties or {}

        try:
            with driver.session() as session:
                session.run("""
                    MERGE (e:Entity {entity_id: $entity_id})
                    SET e.entity_type = $entity_type,
                        e += $properties,
                        e.created_at = timestamp()
                    RETURN e
                """, entity_id=entity_id, entity_type=entity_type, properties=properties)
            return True
        except Exception as e:
            print(f"Error adding entity: {e}")
            return False

    async def add_entities_batch(
        self,
        entities: List[Tuple[str, str, Dict]]
    ) -> int:
        """
        批量添加实体

        Args:
            entities: [(entity_id, entity_type, properties), ...]

        Returns:
            成功数量
        """
        driver = self._get_driver()
        count = 0

        try:
            with driver.session() as session:
                for entity_id, entity_type, properties in entities:
                    session.run("""
                        MERGE (e:Entity {entity_id: $entity_id})
                        SET e.entity_type = $entity_type,
                            e += $properties,
                            e.created_at = timestamp()
                    """, entity_id=entity_id, entity_type=entity_type, properties=properties)
                    count += 1
            return count
        except Exception as e:
            print(f"Error adding entities batch: {e}")
            return count

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加关系

        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            relation_type: 关系类型
            properties: 属性

        Returns:
            是否成功
        """
        driver = self._get_driver()
        properties = properties or {}

        try:
            with driver.session() as session:
                session.run("""
                    MATCH (source:Entity {entity_id: $source_id})
                    MATCH (target:Entity {entity_id: $target_id})
                    MERGE (source)-[r:RELATES_TO {type: $relation_type}]->(target)
                    SET r += $properties
                    RETURN r
                """, source_id=source_id, target_id=target_id,
                   relation_type=relation_type, properties=properties)
            return True
        except Exception as e:
            print(f"Error adding relation: {e}")
            return False

    async def find_entity(self, entity_id: str) -> Optional[Dict]:
        """查找实体"""
        driver = self._get_driver()

        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})
                    RETURN e.entity_id AS entity_id,
                           e.entity_type AS entity_type,
                           e.properties AS properties,
                           e.created_at AS created_at
                """, entity_id=entity_id)

                record = result.single()
                if record:
                    return dict(record)
                return None
        except Exception as e:
            print(f"Error finding entity: {e}")
            return None

    async def find_related_entities(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        depth: int = 1
    ) -> List[Dict]:
        """
        查找相关实体

        Args:
            entity_id: 实体ID
            relation_type: 关系类型过滤
            depth: 深度

        Returns:
            相关实体列表
        """
        driver = self._get_driver()

        try:
            with driver.session() as session:
                if relation_type:
                    query = """
                        MATCH (e:Entity {entity_id: $entity_id})
                        MATCH (e)-[:RELATES_TO*1..%d {type: $relation_type}]-(related:Entity)
                        RETURN DISTINCT related.entity_id AS entity_id,
                               related.entity_type AS entity_type,
                               related.properties AS properties
                    """ % depth
                    result = session.run(query, entity_id=entity_id, relation_type=relation_type)
                else:
                    query = """
                        MATCH (e:Entity {entity_id: $entity_id})
                        MATCH (e)-[:RELATES_TO*1..%d]-(related:Entity)
                        RETURN DISTINCT related.entity_id AS entity_id,
                               related.entity_type AS entity_type,
                               related.properties AS properties
                    """ % depth
                    result = session.run(query, entity_id=entity_id)

                return [dict(record) for record in result]
        except Exception as e:
            print(f"Error finding related entities: {e}")
            return []

    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5
    ) -> List[Dict]:
        """
        查找路径

        Args:
            start_id: 起始实体ID
            end_id: 目标实体ID
            max_depth: 最大深度

        Returns:
            路径列表
        """
        driver = self._get_driver()

        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH path = shortestPath(
                        (start:Entity {entity_id: $start_id})
                        -[:RELATES_TO*1..%d]
                        -(end:Entity {entity_id: $end_id})
                    )
                    RETURN path
                """ % max_depth, start_id=start_id, end_id=end_id)

                record = result.single()
                if record:
                    path = record["path"]
                    nodes = [dict(n) for n in path.nodes]
                    relationships = [dict(r) for r in path.relationships]
                    return {
                        "nodes": nodes,
                        "relationships": relationships
                    }
                return None
        except Exception as e:
            print(f"Error finding path: {e}")
            return None

    async def execute_query(self, cypher: str, **params) -> List[Dict]:
        """
        执行Cypher查询

        Args:
            cypher: Cypher语句
            **params: 参数

        Returns:
            结果列表
        """
        driver = self._get_driver()

        try:
            with driver.session() as session:
                result = session.run(cypher, **params)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"Error executing query: {e}")
            return []

    async def delete_entity(self, entity_id: str) -> bool:
        """删除实体及其关系"""
        driver = self._get_driver()

        try:
            with driver.session() as session:
                session.run("""
                    MATCH (e:Entity {entity_id: $entity_id})
                    DETACH DELETE e
                """, entity_id=entity_id)
            return True
        except Exception as e:
            print(f"Error deleting entity: {e}")
            return False

    async def get_entity_stats(self) -> Dict[str, Any]:
        """获取实体统计"""
        driver = self._get_driver()

        try:
            with driver.session() as session:
                # 统计实体数量
                entity_count = session.run("""
                    MATCH (e:Entity)
                    RETURN count(e) as count
                """).single()["count"]

                # 按类型统计
                type_stats = session.run("""
                    MATCH (e:Entity)
                    RETURN e.entity_type AS type, count(e) AS count
                """)

                # 统计关系数量
                relation_count = session.run("""
                    MATCH ()-[r:RELATES_TO]->()
                    RETURN count(r) as count
                """).single()["count"]

                return {
                    "total_entities": entity_count,
                    "total_relations": relation_count,
                    "by_type": [dict(r) for r in type_stats]
                }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}

    async def find_agents_by_capability(self, capability: str) -> List[Dict]:
        """查找具有特定能力的Agent"""
        driver = self._get_driver()

        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (agent:Entity {entity_type: 'agent'})
                    WHERE agent.properties.capabilities CONTAINS $capability
                    RETURN agent.entity_id AS entity_id,
                           agent.properties AS properties
                """, capability=capability)

                return [dict(record) for record in result]
        except Exception as e:
            print(f"Error finding agents: {e}")
            return []

    async def find_task_dependencies(self, task_id: str) -> Dict[str, List]:
        """查找任务依赖关系"""
        driver = self._get_driver()

        try:
            with driver.session() as session:
                # 查找前置任务
                prerequisites = session.run("""
                    MATCH (task:Entity {entity_id: $task_id})
                    MATCH (prereq:Entity)-[:RELATES_TO {type: 'depends_on'}]->(task)
                    RETURN prereq.entity_id AS entity_id,
                           prereq.properties AS properties
                """, task_id=task_id)

                # 查找后置任务
                dependents = session.run("""
                    MATCH (task:Entity {entity_id: $task_id})
                    MATCH (task)-[:RELATES_TO {type: 'depends_on'}]->(dep:Entity)
                    RETURN dep.entity_id AS entity_id,
                           dep.properties AS properties
                """, task_id=task_id)

                return {
                    "prerequisites": [dict(r) for r in prerequisites],
                    "dependents": [dict(r) for r in dependents]
                }
        except Exception as e:
            print(f"Error finding dependencies: {e}")
            return {"prerequisites": [], "dependents": []}


# 单例
_neo4j_instance: Optional[Neo4jGraphStore] = None


def get_neo4j_graph_store() -> Neo4jGraphStore:
    """获取Neo4j图存储单例"""
    global _neo4j_instance
    if _neo4j_instance is None:
        _neo4j_instance = Neo4jGraphStore(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD")
        )
    return _neo4j_instance
