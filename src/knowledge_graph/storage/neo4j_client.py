"""
Neo4j图数据库客户端
Neo4j Graph Database Client
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

from ..schema.academic_kg_schema import Entity, Relation, AcademicKGSchema


@dataclass
class SubgraphResult:
    """子图查询结果"""
    nodes: List[Dict]
    edges: List[Dict]
    center_id: str


class Neo4jClient:
    """Neo4j图数据库客户端"""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        database: str = "neo4j"
    ):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None

        # 检查是否安装了neo4j
        self._available = self._check_neo4j()

    def _check_neo4j(self) -> bool:
        """检查neo4j驱动是否可用"""
        try:
            from neo4j import GraphDatabase
            return True
        except ImportError:
            print("Warning: neo4j driver not installed. Using mock mode.")
            return False

    def connect(self):
        """建立连接"""
        if not self._available:
            return

        from neo4j import GraphDatabase

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password)
        )

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.driver = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @contextmanager
    def session(self):
        """获取会话上下文管理器"""
        if not self.driver:
            raise RuntimeError("Not connected. Call connect() first.")

        sess = self.driver.session(database=self.database)
        try:
            yield sess
        finally:
            sess.close()

    def create_schema(self):
        """创建图谱Schema"""
        if not self._available:
            print("Mock: create schema")
            return

        with self.session() as session:
            # 创建约束
            for stmt in AcademicKGSchema.get_cypher_constraint_statements():
                try:
                    session.run(stmt)
                except Exception as e:
                    print(f"Constraint creation warning: {e}")

            # 创建索引
            for stmt in AcademicKGSchema.get_cypher_index_statements():
                try:
                    session.run(stmt)
                except Exception as e:
                    print(f"Index creation warning: {e}")

    def insert_entity(self, entity: Entity) -> bool:
        """插入实体"""
        if not self._available:
            print(f"Mock: insert entity {entity.id}")
            return True

        with self.session() as session:
            query = f"""
            MERGE (e:{entity.type.value} {{id: $id}})
            SET e.name = $name,
                e.properties = $properties
            """

            session.run(query, id=entity.id, name=entity.name, properties=entity.properties)

        return True

    def insert_entities(self, entities: List[Entity]) -> int:
        """批量插入实体"""
        count = 0
        for entity in entities:
            if self.insert_entity(entity):
                count += 1
        return count

    def insert_relation(self, relation: Relation) -> bool:
        """插入关系"""
        if not self._available:
            print(f"Mock: insert relation {relation.type.value}")
            return True

        with self.session() as session:
            query = """
            MATCH (s {id: $source_id})
            MATCH (t {id: $target_id})
            MERGE (s)-[r {type: $type}]->(t)
            SET r.properties = $properties
            """

            session.run(
                query,
                source_id=relation.source,
                target_id=relation.target,
                type=relation.type.value,
                properties=relation.properties
            )

        return True

    def insert_relations(self, relations: List[Relation]) -> int:
        """批量插入关系"""
        count = 0
        for relation in relations:
            if self.insert_relation(relation):
                count += 1
        return count

    def find_entity(self, entity_id: str) -> Optional[Dict]:
        """查找实体"""
        if not self._available:
            return None

        with self.session() as session:
            query = """
            MATCH (e {id: $id})
            RETURN e
            """

            result = session.run(query, id=entity_id)
            record = result.single()

            if record:
                return dict(record["e"])
            return None

    def find_entities_by_type(
        self,
        entity_type: str,
        limit: int = 100
    ) -> List[Dict]:
        """按类型查找实体"""
        if not self._available:
            return []

        with self.session() as session:
            query = f"""
            MATCH (e:{entity_type})
            RETURN e
            LIMIT $limit
            """

            result = session.run(query, limit=limit)
            return [dict(record["e"]) for record in result]

    def find_relations_by_type(
        self,
        relation_type: str,
        limit: int = 100
    ) -> List[Dict]:
        """按类型查找关系"""
        if not self._available:
            return []

        with self.session() as session:
            query = f"""
            MATCH ()-[r:{relation_type}]->()
            RETURN r
            LIMIT $limit
            """

            result = session.run(query, limit=limit)
            return [dict(record["r"]) for record in result]

    def query_subgraph(
        self,
        center_id: str,
        depth: int = 2,
        relation_types: Optional[List[str]] = None
    ) -> SubgraphResult:
        """查询局部子图"""
        if not self._available:
            return SubgraphResult(nodes=[], edges=[], center_id=center_id)

        rel_type_filter = ""
        if relation_types:
            rel_types = "|".join(relation_types)
            rel_type_filter = f":{rel_types}"

        with self.session() as session:
            # 查询从中心节点出发的路径
            query = f"""
            MATCH path = (center {{id: $center_id}})
                -[{rel_type_filter}*1..{depth}]-
                (connected)
            RETURN nodes(path) as nodes, relationships(path) as rels
            """

            result = session.run(query, center_id=center_id)

            nodes = []
            edges = []
            seen_nodes = set()
            seen_edges = set()

            for record in result:
                for node in record["nodes"]:
                    node_dict = dict(node)
                    node_id = node_dict.get("id")
                    if node_id and node_id not in seen_nodes:
                        nodes.append(node_dict)
                        seen_nodes.add(node_id)

                for rel in record["rels"]:
                    rel_dict = dict(rel)
                    rel_key = f"{rel.start_node.get('id')}_{rel.type}_{rel.end_node.get('id')}"
                    if rel_key not in seen_edges:
                        edges.append({
                            "source": rel.start_node.get("id"),
                            "target": rel.end_node.get("id"),
                            "type": rel.type,
                            "properties": dict(rel)
                        })
                        seen_edges.add(rel_key)

        return SubgraphResult(nodes=nodes, edges=edges, center_id=center_id)

    def find_neighbors(
        self,
        entity_id: str,
        depth: int = 1,
        relation_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """查找邻居节点"""
        if not self._available:
            return []

        rel_type_filter = ""
        if relation_types:
            rel_types = "|".join(relation_types)
            rel_type_filter = f":{rel_types}"

        with self.session() as session:
            query = f"""
            MATCH (e {{id: $entity_id}})-[{rel_type_filter}*1..{depth}]-(neighbor)
            RETURN DISTINCT neighbor
            """

            result = session.run(query, entity_id=entity_id)
            return [dict(record["neighbor"]) for record in result]

    def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5
    ) -> List[Dict]:
        """查找最短路径"""
        if not self._available:
            return []

        with self.session() as session:
            query = f"""
            MATCH path = shortestPath(
                (source {{id: $source_id}})-[*1..{max_length}]-(target {{id: $target_id}})
            )
            RETURN path
            """

            result = session.run(query, source_id=source_id, target_id=target_id)
            records = list(result)

            if not records:
                return []

            path = records[0]["path"]
            nodes = [dict(n) for n in path.nodes]
            edges = []
            for i, rel in enumerate(path.relationships):
                edges.append({
                    "source": rel.start_node.get("id"),
                    "target": rel.end_node.get("id"),
                    "type": rel.type
                })

            return {"nodes": nodes, "edges": edges}

    def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict] = None
    ) -> List[Dict]:
        """执行Cypher查询"""
        if not self._available:
            return []

        with self.session() as session:
            result = session.run(query, **(parameters or {}))
            return [dict(record) for record in result]

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        if not self._available:
            return {
                "total_entities": 0,
                "total_relations": 0,
                "entity_types": {},
                "relation_types": {}
            }

        stats = {}

        # 统计各类型实体数量
        with self.session() as session:
            for entity_type in AcademicKGSchema.ENTITY_TYPES.keys():
                query = f"MATCH (e:{entity_type}) RETURN count(e) as count"
                result = session.run(query)
                count = result.single()["count"]
                stats[entity_type] = count

        # 统计各类型关系数量
        with self.session() as session:
            for rel_type in AcademicKGSchema.RELATION_TYPES.keys():
                query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
                result = session.run(query)
                count = result.single()["count"]
                stats[rel_type] = count

        return stats

    def delete_all(self):
        """删除所有数据"""
        if not self._available:
            print("Mock: delete all")
            return

        with self.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def clear_graph(self):
        """清空图谱"""
        self.delete_all()
