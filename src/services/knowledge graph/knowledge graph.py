from dataclasses import dataclass, field
from typing import Any

from neo4j import GraphDatabase


@dataclass
class PaperGraphRecord:
    """统计论文结构化记录（可由 LLM + 规则抽取生成）。"""

    title: str
    year: int
    doi: str | None = None
    venue: str | None = None
    abstract: str | None = None
    task_name: str | None = None
    methods: list[str] = field(default_factory=list)
    datasets: list[str] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    authors: list[dict[str, str]] = field(default_factory=list)



class Neo4jStatisticsKG:
    """统计论文知识图谱：创建约束、写入数据、执行典型查询。"""
    def __init__(self, uri: str) -> None:
        self.driver = GraphDatabase.driver(uri)

    def close(self) -> None:
        self.driver.close()

    def init_schema(self) -> None:#类节点创建 唯一性约束，适用Cyher语句去创建
        queries = [
            """
            CREATE CONSTRAINT paper_title_year IF NOT EXISTS
            FOR (p:Paper) REQUIRE (p.title, p.year) IS UNIQUE
            """,
            """
            CREATE CONSTRAINT author_name IF NOT EXISTS
            FOR (a:Author) REQUIRE a.name IS UNIQUE
            """,
            """
            CREATE CONSTRAINT method_name IF NOT EXISTS
            FOR (m:Method) REQUIRE m.name IS UNIQUE
            """,
            """
            CREATE INDEX task_name IF NOT EXISTS
            FOR (t:Task) ON (t.name)
            """,
        ]

        with self.driver.session() as session:
            for query in queries:
                session.run(query)

    def upsert_paper_record(self, record: PaperGraphRecord) -> None:#
        """
        核心目标：
        基于title+year唯一标识，向 Neo4j 批量写入 / 更新论文节点及关联的任务、方法、数据集、指标、作者 / 机构等图关系。
        2. 关键语法：MERGE实现 Upsert、FOREACH+CASE实现条件执行、coalesce处理空值、列表遍历实现批量关联。
        3. 图结构：最终形成Paper为核心，关联Task/Method/Dataset/Metric/Author/Institution等节点的图谱，关系带明确语义（STUDIES/USES_METHOD等）。
        :param record:
        :return:
        """


        query = """
        MERGE (p:Paper {title: $title, year: $year})
        SET p.doi = $doi,
            p.venue = $venue,
            p.abstract = $abstract

        FOREACH (_ IN CASE WHEN $task_name IS NULL THEN [] ELSE [1] END |
          MERGE (t:Task {name: $task_name})
          MERGE (p)-[:STUDIES]->(t)
        )

        FOREACH (method_name IN $methods |
          MERGE (m:Method {name: method_name})
          MERGE (p)-[:USES_METHOD]->(m)
        )

        FOREACH (dataset_name IN $datasets |
          MERGE (d:Dataset {name: dataset_name})
          MERGE (p)-[:USES_DATASET]->(d)
        )

        FOREACH (metric IN $metrics |
          MERGE (me:Metric {name: metric.name})
          MERGE (p)-[:EVALUATED_BY {
            value: coalesce(metric.value, ''),
            split: coalesce(metric.split, '')
          }]->(me)
        )

        FOREACH (author IN $authors |
          MERGE (a:Author {name: author.name})
          FOREACH (_ IN CASE WHEN author.institution IS NULL THEN [] ELSE [1] END |
            MERGE (i:Institution {name: author.institution})
            MERGE (a)-[:AFFILIATED_WITH]->(i)
          )
          MERGE (a)-[:AUTHORED]->(p)
        )
        """
        payload = {
            "title": record.title,
            "year": record.year,
            "doi": record.doi,
            "venue": record.venue,
            "abstract": record.abstract,
            "task_name": record.task_name,
            "methods": record.methods,
            "datasets": record.datasets,
            "metrics": record.metrics,
            "authors": record.authors,
        }
        with self.driver.session() as session:
            session.run(query, payload)


    def top_methods_for_task(self, task_name: str, limit: int = 10) -> list[dict[str, Any]]:
        query = """
        MATCH (:Task {name: $task_name})<-[:STUDIES]-(p:Paper)-[:USES_METHOD]->(m:Method)
        RETURN m.name AS method, count(*) AS freq
        ORDER BY freq DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(query, {"task_name": task_name, "limit": limit})
            return [dict(row) for row in result]


if __name__ == "__main__":
    # 示例：根据真实环境变量或配置替换连接信息
    kg = Neo4jStatisticsKG(uri="bolt://localhost:7687")#在docker中采用了 -e NEO4J_AUTH=none `
    kg.init_schema()

    sample = PaperGraphRecord(
        title="A Bayesian Approach for Time Series Forecasting",
        year=2024,
        doi="10.0000/example",
        venue="Journal of Statistical Learning",
        abstract="A short abstract about Bayesian forecasting.",
        task_name="时间序列预测",
        methods=["Bayesian Regression", "MCMC"],
        datasets=["M4", "Electricity Load"],
        metrics=[
            {"name": "MAE", "value": "0.123", "split": "test"},
            {"name": "RMSE", "value": "0.185", "split": "test"},
        ],
        authors=[
            {"name": "Alice Zhang", "institution": "Tsinghua University"},
            {"name": "Bob Li", "institution": "Peking University"},
        ],
    )

    kg.upsert_paper_record(sample)
    print(kg.top_methods_for_task("时间序列预测"))
    kg.close()

