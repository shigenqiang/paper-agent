"""PostgreSQL 存储后端实现"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from loguru import logger

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    logger.warning("psycopg2 not installed, PostgreSQL storage unavailable")


# ── 表结构定义 ──────────────────────────────────────────

TABLE_SCHEMAS = {
    "projects": """
        CREATE TABLE IF NOT EXISTS projects (
            project_id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(255),
            dir_name VARCHAR(255),
            description TEXT,
            discipline VARCHAR(128),
            education_level VARCHAR(64),
            research_goal TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "papers_pool": """
        CREATE TABLE IF NOT EXISTS papers_pool (
            paper_id VARCHAR(128) PRIMARY KEY,
            title TEXT,
            abstract TEXT,
            authors JSONB DEFAULT '[]',
            year INTEGER,
            venue TEXT,
            doi VARCHAR(255),
            arxiv_id VARCHAR(64),
            pubmed_id VARCHAR(64),
            openalex_id VARCHAR(64),
            semantic_scholar_id VARCHAR(64),
            url TEXT,
            pdf_url TEXT,
            citations INTEGER,
            concepts JSONB DEFAULT '[]',
            keywords JSONB DEFAULT '[]',
            language VARCHAR(16),
            publication_type VARCHAR(32),
            source VARCHAR(32),
            source_payload JSONB DEFAULT '{}',
            is_pdf_downloaded BOOLEAN DEFAULT FALSE,
            is_parsed BOOLEAN DEFAULT FALSE,
            metadata JSONB DEFAULT '{}',
            added_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "papers": """
        CREATE TABLE IF NOT EXISTS papers (
            paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE CASCADE,
            project_id VARCHAR(64) REFERENCES projects(project_id) ON DELETE CASCADE,
            importance_score FLOAT DEFAULT 0.0,
            relevance_score FLOAT DEFAULT 0.0,
            quality_score FLOAT DEFAULT 0.0,
            included BOOLEAN DEFAULT TRUE,
            exclude_reason TEXT DEFAULT '',
            status VARCHAR(32) DEFAULT 'imported',
            pdf_path TEXT DEFAULT '',
            error_message TEXT DEFAULT '',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (paper_id, project_id)
        )
    """,
    "paper_chunks": """
        CREATE TABLE IF NOT EXISTS paper_chunks (
            chunk_id VARCHAR(64) PRIMARY KEY,
            paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE CASCADE,
            chunk_index INTEGER DEFAULT 0,
            section_title TEXT,
            section_type VARCHAR(32),
            chunk_type VARCHAR(32) DEFAULT 'body',
            parent_id VARCHAR(64) DEFAULT '',
            text TEXT,
            start_char INTEGER DEFAULT 0,
            end_char INTEGER DEFAULT 0,
            page_start INTEGER DEFAULT 0,
            page_end INTEGER DEFAULT 0,
            token_count INTEGER DEFAULT 0,
            parser_name VARCHAR(32),
            quality_flags JSONB DEFAULT '[]',
            quality_score FLOAT DEFAULT 0.0,
            quality_details JSONB DEFAULT '{}',
            metadata JSONB DEFAULT '{}'
        )
    """,
    "paper_cards": """
        CREATE TABLE IF NOT EXISTS paper_cards (
            card_id VARCHAR(64) PRIMARY KEY,
            paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE CASCADE,
            is_active BOOLEAN DEFAULT TRUE,
            extraction JSONB DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "evidence_records": """
        CREATE TABLE IF NOT EXISTS evidence_records (
            evidence_id VARCHAR(64) PRIMARY KEY,
            paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE CASCADE,
            card_id VARCHAR(64),
            topic VARCHAR(255),
            method TEXT,
            finding TEXT,
            limitation TEXT,
            future_work TEXT,
            source_quote TEXT,
            source_span JSONB DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "parse_results": """
        CREATE TABLE IF NOT EXISTS parse_results (
            parse_id VARCHAR(64) PRIMARY KEY,
            paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE CASCADE,
            parser_name VARCHAR(32),
            status VARCHAR(32) DEFAULT 'pending',
            page_count INTEGER DEFAULT 0,
            section_count INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0,
            body_chunk_count INTEGER DEFAULT 0,
            reference_count INTEGER DEFAULT 0,
            quality_flags JSONB DEFAULT '[]',
            error_message TEXT,
            started_at TIMESTAMP,
            finished_at TIMESTAMP
        )
    """,
    "graphs": """
        CREATE TABLE IF NOT EXISTS graphs (
            graph_id VARCHAR(64) PRIMARY KEY,
            project_id VARCHAR(64),
            nodes JSONB DEFAULT '[]',
            edges JSONB DEFAULT '[]',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "reports": """
        CREATE TABLE IF NOT EXISTS reports (
            report_id VARCHAR(64) PRIMARY KEY,
            project_id VARCHAR(64),
            report_type VARCHAR(32),
            title TEXT,
            content TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "report_versions": """
        CREATE TABLE IF NOT EXISTS report_versions (
            version_id VARCHAR(64) PRIMARY KEY,
            report_id VARCHAR(64) REFERENCES reports(report_id) ON DELETE CASCADE,
            version_number INTEGER,
            content TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "tasks": """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id VARCHAR(64) PRIMARY KEY,
            task_type VARCHAR(32),
            status VARCHAR(32) DEFAULT 'pending',
            data JSONB DEFAULT '{}',
            events JSONB DEFAULT '[]',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "qa_history": """
        CREATE TABLE IF NOT EXISTS qa_history (
            qa_id VARCHAR(64) PRIMARY KEY,
            project_id VARCHAR(64),
            question TEXT,
            answer TEXT,
            sources JSONB DEFAULT '[]',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "paper_references": """
        CREATE TABLE IF NOT EXISTS paper_references (
            ref_id VARCHAR(64) PRIMARY KEY,
            citing_paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE CASCADE,
            cited_paper_id VARCHAR(128) DEFAULT '',
            index INTEGER DEFAULT 0,
            raw_text TEXT,
            title TEXT,
            authors JSONB DEFAULT '[]',
            year INTEGER,
            venue TEXT,
            doi VARCHAR(255),
            url TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "kg_nodes": """
        CREATE TABLE IF NOT EXISTS kg_nodes (
            node_id VARCHAR(128) PRIMARY KEY,
            project_id VARCHAR(64),
            node_type VARCHAR(32),
            label TEXT,
            description TEXT,
            properties JSONB DEFAULT '{}',
            confidence FLOAT DEFAULT 1.0,
            source_paper_ids JSONB DEFAULT '[]',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "kg_edges": """
        CREATE TABLE IF NOT EXISTS kg_edges (
            edge_id VARCHAR(128) PRIMARY KEY,
            project_id VARCHAR(64),
            source_id VARCHAR(128),
            target_id VARCHAR(128),
            edge_type VARCHAR(32),
            confidence FLOAT DEFAULT 1.0,
            evidence TEXT,
            source_chunk_id VARCHAR(64),
            source_paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE SET NULL,
            properties JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "topic_scores": """
        CREATE TABLE IF NOT EXISTS topic_scores (
            paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE CASCADE,
            topic VARCHAR(255),
            importance_score FLOAT DEFAULT 0.0,
            relevance_score FLOAT DEFAULT 0.0,
            quality_score FLOAT DEFAULT 0.0,
            scored_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (paper_id, topic)
        )
    """,
    "queries": """
        CREATE TABLE IF NOT EXISTS queries (
            query_id VARCHAR(64) PRIMARY KEY,
            query_text TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(query_text)
        )
    """,
    "paper_queries": """
        CREATE TABLE IF NOT EXISTS paper_queries (
            paper_id VARCHAR(128) REFERENCES papers_pool(paper_id) ON DELETE CASCADE,
            query_id VARCHAR(64) REFERENCES queries(query_id) ON DELETE CASCADE,
            score FLOAT DEFAULT 0.0,
            source VARCHAR(32) DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (paper_id, query_id)
        )
    """,
}

# 表名到 ID 字段的映射
TABLE_ID_FIELDS = {
    "projects": "project_id",
    "papers_pool": "paper_id",
    "papers": "paper_id",
    "paper_chunks": "chunk_id",
    "paper_cards": "card_id",
    "evidence_records": "evidence_id",
    "parse_results": "parse_id",
    "graphs": "graph_id",
    "reports": "report_id",
    "report_versions": "version_id",
    "tasks": "task_id",
    "qa_history": "qa_id",
    "paper_references": "ref_id",
    "kg_nodes": "node_id",
    "kg_edges": "edge_id",
    "topic_scores": "paper_id",
    "queries": "query_id",
    "paper_queries": "paper_id",
}

# 复合唯一约束表（ON CONFLICT 需要列出所有列）
TABLE_UNIQUE_CONSTRAINTS = {
    "papers": ["paper_id", "project_id"],
    "topic_scores": ["paper_id", "topic"],
    "paper_queries": ["paper_id", "query_id"],
}


class PostgresStorage:
    """PostgreSQL 存储后端"""

    def __init__(self, dsn: str | None = None, **kwargs):
        if not HAS_PSYCOPG2:
            raise RuntimeError("psycopg2 is not installed. Run: pip install psycopg2-binary")

        if dsn:
            self.conn = psycopg2.connect(dsn)
        else:
            self.conn = psycopg2.connect(
                host=kwargs.get("host", "localhost"),
                port=kwargs.get("port", 5432),
                database=kwargs.get("database", "paper_agent"),
                user=kwargs.get("user", "postgres"),
                password=kwargs.get("password", ""),
            )
        self.conn.autocommit = True
        # 兼容 JSONStorage 的 data_dir 属性
        from pathlib import Path
        self.data_dir = Path("data/research_workspace")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """创建所有表并修补缺失列"""
        with self.conn.cursor() as cur:
            for table_name, schema in TABLE_SCHEMAS.items():
                try:
                    cur.execute(schema)
                except Exception as e:
                    logger.error(f"Failed to create table {table_name}: {e}")

            # 修补已有表的缺失列（CREATE TABLE IF NOT EXISTS 不会修改已有表）
            _migrations = [
                ("papers_pool", "is_pdf_downloaded", "BOOLEAN DEFAULT FALSE"),
                ("papers_pool", "is_parsed", "BOOLEAN DEFAULT FALSE"),
                ("papers", "relevance_score", "FLOAT DEFAULT 0.0"),
                ("papers", "quality_score", "FLOAT DEFAULT 0.0"),
                ("paper_chunks", "parent_id", "VARCHAR(64) DEFAULT ''"),
                ("paper_chunks", "quality_score", "FLOAT DEFAULT 0.0"),
                ("paper_chunks", "quality_details", "JSONB DEFAULT '{}'"),
                ("parse_results", "table_count", "INTEGER DEFAULT 0"),
                ("parse_results", "figure_count", "INTEGER DEFAULT 0"),
                ("parse_results", "diagnostics", "JSONB DEFAULT '{}'"),
            ]
            for table, col, col_def in _migrations:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}")
                except Exception:
                    pass  # 列已存在

            # 创建索引
            _indexes = [
                "CREATE INDEX IF NOT EXISTS idx_paper_refs_citing ON paper_references(citing_paper_id)",
                "CREATE INDEX IF NOT EXISTS idx_paper_refs_cited ON paper_references(cited_paper_id)",
                "CREATE INDEX IF NOT EXISTS idx_paper_queries_query ON paper_queries(query_id)",
            ]
            for idx_sql in _indexes:
                try:
                    cur.execute(idx_sql)
                except Exception:
                    pass

        logger.info("PostgreSQL tables ensured")

    def _get_id_field(self, table: str) -> str:
        """获取表的主键字段名"""
        return TABLE_ID_FIELDS.get(table, "id")

    def upsert(self, table: str, item_id: str, data: dict[str, Any]) -> None:
        """插入或更新一条记录"""
        id_field = self._get_id_field(table)
        # 将嵌套 dict 转为 JSON 字符串用于 JSONB 字段
        processed = self._process_data_for_db(data)

        # 复合主键表：确保 data 中包含所有主键字段
        conflict_cols = TABLE_UNIQUE_CONSTRAINTS.get(table, [id_field])
        if len(conflict_cols) > 1:
            for col in conflict_cols:
                if col not in processed:
                    raise ValueError(f"Composite key table '{table}' requires '{col}' in data")

        columns = list(processed.keys())
        values = [processed[k] for k in columns]
        placeholders = ["%s"] * len(columns)

        # 确定冲突目标：复合唯一约束 or 单字段主键
        conflict_cols = TABLE_UNIQUE_CONSTRAINTS.get(table, [id_field])
        conflict_target = ", ".join(conflict_cols)

        # 构建 UPDATE 子句（排除冲突目标列）
        exclude_set = set(conflict_cols)
        update_clause = ", ".join(
            f"{k} = EXCLUDED.{k}" for k in columns if k not in exclude_set
        )

        sql = f"""
            INSERT INTO {table} ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
            ON CONFLICT ({conflict_target}) DO UPDATE SET {update_clause}
        """

        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, values)
        except Exception as e:
            logger.error(f"Upsert failed for {table}/{item_id}: {e}")
            raise

    def get(self, table: str, item_id: str) -> dict[str, Any] | None:
        """获取单条记录"""
        id_field = self._get_id_field(table)
        sql = f"SELECT * FROM {table} WHERE {id_field} = %s"

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (item_id,))
                row = cur.fetchone()
                return self._process_row_from_db(dict(row)) if row else None
        except Exception as e:
            logger.error(f"Get failed for {table}/{item_id}: {e}")
            return None

    def query(self, table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """按条件查询"""
        if not filters:
            return self.list_all(table)

        conditions = []
        values = []
        for key, value in filters.items():
            if isinstance(value, dict):
                # JSONB 查询支持
                for op, v in value.items():
                    if op == "$contains":
                        conditions.append(f"{key} @> %s")
                        values.append(Json(v))
                    elif op == "$eq":
                        conditions.append(f"{key} = %s")
                        values.append(v)
            elif isinstance(value, list):
                if value:
                    placeholders = ", ".join(["%s"] * len(value))
                    conditions.append(f"{key} IN ({placeholders})")
                    values.extend(value)
                else:
                    conditions.append("FALSE")
            else:
                conditions.append(f"{key} = %s")
                values.append(value)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM {table} WHERE {where_clause}"

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, values)
                rows = cur.fetchall()
                return [self._process_row_from_db(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Query failed for {table}: {e}")
            return []

    def delete(self, table: str, item_id: str) -> bool:
        """删除一条记录"""
        id_field = self._get_id_field(table)
        sql = f"DELETE FROM {table} WHERE {id_field} = %s"

        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (item_id,))
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Delete failed for {table}/{item_id}: {e}")
            return False

    def delete_project_data(self, project_id: str) -> dict[str, int]:
        """删除项目相关的所有数据库记录

        删除顺序：
        1. 根级实体（有 project_id 无 paper_id 的表）
        2. papers_pool（CASCADE 自动删 paper_chunks/cards/evidence/parse_results/topic_scores/references）
        3. projects（CASCADE 自动删 papers）
        """
        deleted = {}

        # 根级实体：直接属于项目，有 project_id 列
        root_tables = [
            "graphs",
            "reports",          # CASCADE: report_versions
            "qa_history",
            "kg_nodes",
            "kg_edges",
        ]

        with self.conn.cursor() as cur:
            # 1. 删根级实体
            for table in root_tables:
                if table not in TABLE_SCHEMAS:
                    continue
                try:
                    cur.execute(f"DELETE FROM {table} WHERE project_id = %s", (project_id,))
                    deleted[table] = cur.rowcount
                except Exception as e:
                    logger.warning(f"Failed to delete {table} for project {project_id}: {e}")
                    deleted[table] = 0

            # 2. 删 papers_pool（CASCADE: paper_chunks, paper_cards, evidence_records,
            #    parse_results, topic_scores, paper_references）
            try:
                cur.execute(
                    "DELETE FROM papers_pool WHERE paper_id IN "
                    "(SELECT paper_id FROM papers WHERE project_id = %s)",
                    (project_id,),
                )
                deleted["papers_pool"] = cur.rowcount
            except Exception as e:
                logger.warning(f"Failed to delete papers_pool for project {project_id}: {e}")
                deleted["papers_pool"] = 0

            # 3. 删 projects（CASCADE: papers）
            try:
                cur.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))
                deleted["projects"] = cur.rowcount
            except Exception as e:
                logger.warning(f"Failed to delete project {project_id}: {e}")
                deleted["projects"] = 0

        self.conn.commit()
        total = sum(deleted.values())
        logger.info(f"Deleted {total} rows for project {project_id}: {deleted}")
        return deleted

    def list_all(self, table: str) -> list[dict[str, Any]]:
        """列出表中所有记录"""
        sql = f"SELECT * FROM {table}"

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                return [self._process_row_from_db(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"List all failed for {table}: {e}")
            return []

    def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        """统计记录数"""
        if filters:
            conditions = []
            values = []
            for key, value in filters.items():
                conditions.append(f"{key} = %s")
                values.append(value)
            where_clause = " AND ".join(conditions)
            sql = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
        else:
            sql = f"SELECT COUNT(*) FROM {table}"
            values = []

        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, values)
                return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Count failed for {table}: {e}")
            return 0

    def close(self) -> None:
        """关闭连接"""
        if self.conn:
            self.conn.close()

    # ── 兼容 JSONStorage 接口 ──

    def upsert_item(self, name: str, item_id: str, item: dict[str, Any]) -> None:
        """兼容 JSONStorage 的 upsert_item 方法"""
        self.upsert(name, item_id, item)

    def get_item(self, name: str, item_id: str) -> dict[str, Any] | None:
        """兼容 JSONStorage 的 get_item 方法"""
        return self.get(name, item_id)

    def get_paper(self, paper_id: str, project_id: str) -> dict[str, Any] | None:
        """按复合键查询 papers 表"""
        rows = self.query("papers", {"paper_id": paper_id, "project_id": project_id})
        return rows[0] if rows else None

    def delete_item(self, name: str, item_id: str) -> bool:
        """兼容 JSONStorage 的 delete_item 方法"""
        return self.delete(name, item_id)

    def load_collection(self, name: str) -> list[dict[str, Any]]:
        """兼容 JSONStorage 的 load_collection 方法"""
        return self.list_all(name)

    def save_collection(self, name: str, items: list[dict[str, Any]]) -> None:
        """兼容 JSONStorage 的 save_collection 方法"""
        id_field = self._get_id_field(name)
        for item in items:
            item_id = item.get(id_field)
            if item_id:
                self.upsert(name, item_id, item)

    def load_project_metadata(self) -> dict[str, Any] | None:
        """兼容 JSONStorage 的 load_project_metadata 方法"""
        # PostgreSQL 不需要这个方法，项目元数据存在 projects 表中
        return None

    def save_project_metadata(self, project_data: dict[str, Any]) -> None:
        """兼容 JSONStorage 的 save_project_metadata 方法"""
        project_id = project_data.get("project_id")
        if project_id:
            self.upsert("projects", project_id, project_data)

    # ── 文件夹存储兼容（papers_pool） ──

    def save_to_folder(self, folder: str, item_id: str, item: dict[str, Any]) -> None:
        """兼容 JSONStorage 的 save_to_folder 方法"""
        if folder == "papers_pool":
            self.upsert("papers_pool", item_id, item)

    def load_from_folder(self, folder: str, item_id: str) -> dict[str, Any] | None:
        """兼容 JSONStorage 的 load_from_folder 方法"""
        if folder == "papers_pool":
            return self.get("papers_pool", item_id)
        return None

    def list_folder(self, folder: str) -> list[dict[str, Any]]:
        """兼容 JSONStorage 的 list_folder 方法"""
        if folder == "papers_pool":
            return self.list_all("papers_pool")
        return []

    def delete_from_folder(self, folder: str, item_id: str) -> bool:
        """兼容 JSONStorage 的 delete_from_folder 方法"""
        if folder == "papers_pool":
            return self.delete("papers_pool", item_id)
        return False

    def ensure_dirs(self) -> None:
        """兼容 JSONStorage 的 ensure_dirs 方法"""
        pass  # PostgreSQL 不需要创建目录

    def _process_data_for_db(self, data: dict[str, Any]) -> dict[str, Any]:
        """将 Python 数据转换为 PostgreSQL 兼容格式"""
        result = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                result[key] = Json(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, float) and key in ("expires_at", "created_at", "updated_at", "added_at", "started_at", "finished_at"):
                # 将 unix 时间戳转换为 ISO 格式
                from datetime import datetime as dt
                result[key] = dt.fromtimestamp(value).isoformat()
            else:
                result[key] = value
        return result

    def _process_row_from_db(self, row: dict[str, Any]) -> dict[str, Any]:
        """将 PostgreSQL 行数据转换为 Python 格式"""
        result = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                # psycopg2 RealDictCursor 已经自动解析 JSONB
                result[key] = value
            else:
                result[key] = value
        return result


def get_postgres_storage(**kwargs) -> PostgresStorage:
    """获取 PostgreSQL 存储实例"""
    return PostgresStorage(**kwargs)
