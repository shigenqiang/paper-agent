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
            metadata JSONB DEFAULT '{}',
            added_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "papers": """
        CREATE TABLE IF NOT EXISTS papers (
            paper_id VARCHAR(64) PRIMARY KEY,
            project_id VARCHAR(64) REFERENCES projects(project_id) ON DELETE CASCADE,
            title TEXT,
            abstract TEXT,
            language VARCHAR(16),
            publication_type VARCHAR(32),
            identifiers JSONB DEFAULT '{}',
            authors JSONB DEFAULT '[]',
            dates JSONB DEFAULT '{}',
            source JSONB DEFAULT '{}',
            open_access JSONB DEFAULT '{}',
            classification JSONB DEFAULT '{}',
            citation JSONB DEFAULT '{}',
            url TEXT,
            source_platform VARCHAR(32),
            source_payload JSONB DEFAULT '{}',
            status VARCHAR(32) DEFAULT 'imported',
            pdf_path TEXT,
            error_message TEXT,
            included BOOLEAN DEFAULT TRUE,
            exclude_reason TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "paper_chunks": """
        CREATE TABLE IF NOT EXISTS paper_chunks (
            chunk_id VARCHAR(64) PRIMARY KEY,
            paper_id VARCHAR(64) REFERENCES papers(paper_id) ON DELETE CASCADE,
            project_id VARCHAR(64),
            chunk_index INTEGER DEFAULT 0,
            section_title TEXT,
            section_type VARCHAR(32),
            chunk_type VARCHAR(32) DEFAULT 'body',
            text TEXT,
            start_char INTEGER DEFAULT 0,
            end_char INTEGER DEFAULT 0,
            page_start INTEGER DEFAULT 0,
            page_end INTEGER DEFAULT 0,
            token_count INTEGER DEFAULT 0,
            parser_name VARCHAR(32),
            quality_flags JSONB DEFAULT '[]',
            metadata JSONB DEFAULT '{}'
        )
    """,
    "paper_cards": """
        CREATE TABLE IF NOT EXISTS paper_cards (
            card_id VARCHAR(64) PRIMARY KEY,
            paper_id VARCHAR(64) REFERENCES papers(paper_id) ON DELETE CASCADE,
            project_id VARCHAR(64),
            is_active BOOLEAN DEFAULT TRUE,
            extraction JSONB DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """,
    "evidence_records": """
        CREATE TABLE IF NOT EXISTS evidence_records (
            evidence_id VARCHAR(64) PRIMARY KEY,
            paper_id VARCHAR(64),
            card_id VARCHAR(64),
            project_id VARCHAR(64),
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
            paper_id VARCHAR(64) REFERENCES papers(paper_id) ON DELETE CASCADE,
            project_id VARCHAR(64),
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
    "search_sessions": """
        CREATE TABLE IF NOT EXISTS search_sessions (
            session_id VARCHAR(64) PRIMARY KEY,
            project_id VARCHAR(64),
            query JSONB DEFAULT '{}',
            results JSONB DEFAULT '[]',
            duplicate_groups JSONB DEFAULT '[]',
            selected_result_ids JSONB DEFAULT '[]',
            status VARCHAR(32) DEFAULT 'pending',
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
    "search_cache": """
        CREATE TABLE IF NOT EXISTS search_cache (
            cache_key VARCHAR(128) PRIMARY KEY,
            data JSONB DEFAULT '{}',
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
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
    "search_sessions": "session_id",
    "tasks": "task_id",
    "qa_history": "qa_id",
    "search_cache": "cache_key",
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
        """创建所有表"""
        with self.conn.cursor() as cur:
            for table_name, schema in TABLE_SCHEMAS.items():
                try:
                    cur.execute(schema)
                except Exception as e:
                    logger.error(f"Failed to create table {table_name}: {e}")
        logger.info("PostgreSQL tables ensured")

    def _get_id_field(self, table: str) -> str:
        """获取表的主键字段名"""
        return TABLE_ID_FIELDS.get(table, "id")

    def upsert(self, table: str, item_id: str, data: dict[str, Any]) -> None:
        """插入或更新一条记录"""
        id_field = self._get_id_field(table)
        # 将嵌套 dict 转为 JSON 字符串用于 JSONB 字段
        processed = self._process_data_for_db(data)

        columns = list(processed.keys())
        values = [processed[k] for k in columns]
        placeholders = ["%s"] * len(columns)

        # 构建 UPSERT 语句
        update_clause = ", ".join(
            f"{k} = EXCLUDED.{k}" for k in columns if k != id_field
        )

        sql = f"""
            INSERT INTO {table} ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
            ON CONFLICT ({id_field}) DO UPDATE SET {update_clause}
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
