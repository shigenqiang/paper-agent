"""
论文数据库模块 - SQLite 存储

功能:
1. SQLite 存储论文元数据（标题、作者、年份、摘要等）
2. 查重机制：按标题/DOI/作者+年份检测已存在的论文
3. 批量保存和查询
"""

import sqlite3
import uuid
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)

# 存储目录
STORAGE_DIR = Path(__file__).parent.parent.parent.parent / "data"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = STORAGE_DIR / "papers.db"


@dataclass
class Paper:
    """论文数据结构"""
    paper_id: str
    title: str
    authors: List[str]
    year: int
    abstract: str = ""
    url: str = ""
    source: str = ""  # arxiv, pubmed, semantic_scholar
    paper_external_id: str = ""  # 外部ID (arXiv ID, PMID, DOI等)
    doi: str = ""
    venue: str = ""  # 期刊/会议
    citations: int = 0
    keywords: List[str] = field(default_factory=list)
    methodology: str = ""
    key_contributions: List[str] = field(default_factory=list)
    results: str = ""
    raw_data: str = ""  # 原始JSON数据
    embedding: List[float] = field(default_factory=list)  # 192维嵌入向量
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "url": self.url,
            "source": self.source,
            "paper_external_id": self.paper_external_id,
            "doi": self.doi,
            "venue": self.venue,
            "citations": self.citations,
            "keywords": self.keywords,
            "methodology": self.methodology,
            "key_contributions": self.key_contributions,
            "results": self.results,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_db_tuple(self) -> Tuple:
        return (
            self.paper_id,
            self.title,
            json.dumps(self.authors, ensure_ascii=False),
            self.year,
            self.abstract,
            self.url,
            self.source,
            self.paper_external_id,
            self.doi,
            self.venue,
            self.citations,
            json.dumps(self.keywords, ensure_ascii=False),
            self.methodology,
            json.dumps(self.key_contributions, ensure_ascii=False),
            self.results,
            self.raw_data,
            json.dumps(self.embedding, ensure_ascii=False) if self.embedding else "[]",
            self.created_at,
            self.updated_at,
        )

    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> "Paper":
        data = dict(row)
        return cls(
            paper_id=data["paper_id"],
            title=data["title"],
            authors=json.loads(data["authors"]) if data["authors"] else [],
            year=data["year"],
            abstract=data["abstract"] or "",
            url=data["url"] or "",
            source=data["source"] or "",
            paper_external_id=data["paper_external_id"] or "",
            doi=data["doi"] or "",
            venue=data["venue"] or "",
            citations=data["citations"] or 0,
            keywords=json.loads(data["keywords"]) if data["keywords"] else [],
            methodology=data["methodology"] or "",
            key_contributions=json.loads(data["key_contributions"]) if data["key_contributions"] else [],
            results=data["results"] or "",
            raw_data=data["raw_data"] or "",
            embedding=json.loads(data["embedding"]) if data.get("embedding") else [],
            created_at=data["created_at"] or "",
            updated_at=data["updated_at"] or "",
        )

    @classmethod
    def from_search_result(cls, paper_dict: Dict[str, Any], source: str = "") -> "Paper":
        """从搜索结果字典创建 Paper 对象"""
        now = datetime.now().isoformat()
        authors = paper_dict.get("authors", [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(",")]

        return cls(
            paper_id=str(uuid.uuid4()),
            title=paper_dict.get("title", "Unknown Title"),
            authors=authors,
            year=int(paper_dict.get("year", 2024)),
            abstract=paper_dict.get("abstract", ""),
            url=paper_dict.get("url", ""),
            source=source or paper_dict.get("source", ""),
            paper_external_id=paper_dict.get("paper_id", ""),
            doi=paper_dict.get("doi", ""),
            venue=paper_dict.get("venue", ""),
            citations=int(paper_dict.get("citations", 0) or 0),
            keywords=paper_dict.get("keywords", []),
            methodology=paper_dict.get("methodology", ""),
            key_contributions=paper_dict.get("key_contributions", []),
            results=paper_dict.get("results", ""),
            raw_data=json.dumps(paper_dict, ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )

    def compute_fingerprint(self) -> str:
        """计算论文指纹，用于去重"""
        content = f"{self.title.lower().strip()}|{self.year}|{','.join(sorted(a.lower().strip() for a in self.authors))}"
        return hashlib.md5(content.encode()).hexdigest()


class PaperDatabase:
    """
    论文数据库 - SQLite 存储

    功能:
    - SQLite 存储论文元数据
    - 关键词搜索
    - 自动去重（标题+年份+作者指纹）
    """

    _instance: Optional["PaperDatabase"] = None

    def __init__(self, db_path: str = str(DATABASE_PATH)):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_sqlite()

    def _init_sqlite(self):
        """初始化 SQLite 数据库"""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                abstract TEXT,
                url TEXT,
                source TEXT,
                paper_external_id TEXT,
                doi TEXT,
                venue TEXT,
                citations INTEGER DEFAULT 0,
                keywords TEXT,
                methodology TEXT,
                key_contributions TEXT,
                results TEXT,
                raw_data TEXT,
                fingerprint TEXT UNIQUE,
                embedding TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_fingerprint ON papers(fingerprint)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source)
        """)
        self._conn.commit()
        logger.info(f"SQLite数据库初始化完成: {self.db_path}")

    def save_paper(self, paper: Paper) -> Tuple[bool, str]:
        """
        保存单篇论文

        Returns:
            (success, message) - 成功返回(True, paper_id)，已存在返回(False, existing_paper_id)
        """
        try:
            fingerprint = paper.compute_fingerprint()

            # 检查是否已存在
            existing = self.find_by_fingerprint(fingerprint)
            if existing:
                return False, existing.paper_id

            # 保存到 SQLite
            cursor = self._conn.cursor()
            db_tuple = paper.to_db_tuple()
            cursor.execute("""
                INSERT INTO papers (
                    paper_id, title, authors, year, abstract, url, source,
                    paper_external_id, doi, venue, citations, keywords,
                    methodology, key_contributions, results, raw_data,
                    fingerprint, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, db_tuple + (fingerprint,))
            self._conn.commit()

            logger.debug(f"论文已保存: {paper.title[:50]}...")
            return True, paper.paper_id

        except Exception as e:
            logger.error(f"保存论文失败: {e}")
            return False, str(e)

    def save_papers_batch(self, papers: List[Paper]) -> Dict[str, Any]:
        """
        批量保存论文

        Returns:
            {
                "saved": 10,      # 新增数量
                "skipped": 5,     # 跳过数量（已存在）
                "failed": 0,      # 失败数量
                "saved_ids": [...],
                "skipped_ids": [...]
            }
        """
        result = {
            "saved": 0,
            "skipped": 0,
            "failed": 0,
            "saved_ids": [],
            "skipped_ids": []
        }

        for paper in papers:
            success, msg = self.save_paper(paper)
            if success:
                result["saved"] += 1
                result["saved_ids"].append(msg)
            elif "已存在" in str(msg) or self.find_by_fingerprint(paper.compute_fingerprint()):
                result["skipped"] += 1
                result["skipped_ids"].append(msg if len(msg) > 50 else self._get_paper_id_by_fingerprint(paper.compute_fingerprint()))
            else:
                result["failed"] += 1
                logger.error(f"保存论文失败: {paper.title[:30]} - {msg}")

        logger.info(f"批量保存完成: 新增{result['saved']}，跳过{result['skipped']}，失败{result['failed']}")
        return result

    def find_by_fingerprint(self, fingerprint: str) -> Optional[Paper]:
        """通过指纹查找论文"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE fingerprint = ?", (fingerprint,))
        row = cursor.fetchone()
        return Paper.from_db_row(row) if row else None

    def _get_paper_id_by_fingerprint(self, fingerprint: str) -> str:
        """通过指纹获取 paper_id"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT paper_id FROM papers WHERE fingerprint = ?", (fingerprint,))
        row = cursor.fetchone()
        return row["paper_id"] if row else ""

    def find_by_title(self, title: str) -> Optional[Paper]:
        """通过标题查找论文（模糊匹配）"""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM papers WHERE title LIKE ? LIMIT 1",
            (f"%{title}%",)
        )
        row = cursor.fetchone()
        return Paper.from_db_row(row) if row else None

    def find_by_external_id(self, external_id: str, source: str) -> Optional[Paper]:
        """通过外部ID查找论文"""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM papers WHERE paper_external_id = ? AND source = ? LIMIT 1",
            (external_id, source)
        )
        row = cursor.fetchone()
        return Paper.from_db_row(row) if row else None

    def search_papers(
        self,
        query: str,
        top_k: int = 10,
        source: str = None,
        year: int = None
    ) -> List[Dict]:
        """
        搜索论文

        Args:
            query: 搜索查询（标题/摘要关键词）
            top_k: 返回数量
            source: 可选，限定数据源
            year: 可选，限定年份

        Returns:
            论文列表
        """
        cursor = self._conn.cursor()
        sql = "SELECT * FROM papers WHERE (title LIKE ? OR abstract LIKE ?)"
        params = [f"%{query}%", f"%{query}%"]

        if source:
            sql += " AND source = ?"
            params.append(source)

        if year:
            sql += " AND year = ?"
            params.append(year)

        sql += " ORDER BY citations DESC LIMIT ?"
        params.append(top_k)

        cursor.execute(sql, params)

        papers = []
        for row in cursor.fetchall():
            paper = Paper.from_db_row(row)
            papers.append(paper.to_dict())

        return papers

    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """通过 ID 获取论文"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
        row = cursor.fetchone()
        return Paper.from_db_row(row) if row else None

    def get_all_papers(self, limit: int = 100, offset: int = 0, source: str = None) -> List[Paper]:
        """获取所有论文"""
        cursor = self._conn.cursor()
        sql = "SELECT * FROM papers"
        params = []

        if source:
            sql += " WHERE source = ?"
            params.append(source)

        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return [Paper.from_db_row(row) for row in cursor.fetchall()]

    def count_papers(self, source: str = None) -> int:
        """统计论文数量"""
        cursor = self._conn.cursor()
        if source:
            cursor.execute("SELECT COUNT(*) FROM papers WHERE source = ?", (source,))
        else:
            cursor.execute("SELECT COUNT(*) FROM papers")
        return cursor.fetchone()[0]

    def delete_paper(self, paper_id: str) -> bool:
        """删除论文"""
        try:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM papers WHERE paper_id = ?", (paper_id,))
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除论文失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局单例
_paper_db_instance: Optional[PaperDatabase] = None


def get_paper_db() -> PaperDatabase:
    """获取论文数据库单例"""
    global _paper_db_instance
    if _paper_db_instance is None:
        _paper_db_instance = PaperDatabase()
    return _paper_db_instance