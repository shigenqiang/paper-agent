# Storage 存储层详解

> 位置: `src/agents_v2/storage/`

## 一、架构概览

```
storage/
├── __init__.py
└── paper_db.py     # SQLite 单一存储（无向量存储）
```

> **注意**: 存储层 (storage/) 使用 SQLite 存储元数据。向量存储功能已移除至 `knowledge_graph/` 模块（使用 ChromaDB）。

## 二、Paper 数据结构

```python
@dataclass
class Paper:
    """论文数据结构"""
    paper_id: str
    title: str
    authors: List[str]
    year: int
    abstract: str = ""
    url: str = ""
    source: str = ""            # arxiv, pubmed, semantic_scholar
    paper_external_id: str = "" # 外部ID (arXiv ID, PMID, DOI等)
    doi: str = ""
    venue: str = ""             # 期刊/会议
    citations: int = 0
    keywords: List[str] = field(default_factory=list)
    methodology: str = ""
    key_contributions: List[str] = field(default_factory=list)
    results: str = ""
    raw_data: str = ""          # 原始JSON数据
    created_at: str = ""
    updated_at: str = ""
```

## 三、存储架构

```
┌────────────────────────────────────────────────────────────┐
│                    Storage Layer                            │
├────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐                                        │
│  │   SQLite        │                                        │
│  │   (元数据+向量)  │                                        │
│  │                 │                                        │
│  │  Paper表        │                                        │
│  │  Citations表    │                                        │
│  └────────┬────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────────────────────────────────┐          │
│  │  PaperDatabase (data/papers.db)              │          │
│  └─────────────────────────────────────────────┘          │
└────────────────────────────────────────────────────────────┘
```

> **变更记录**:
> - v2.0: 原storage层移除ChromaDB向量存储，统一使用SQLite
> - 知识图谱模块(knowledge_graph/)保留ChromaDB向量存储功能

## 四、存储路径

```
data/
└── papers.db         # SQLite数据库
    └── Paper表: id, title, authors, year, abstract, ...
```

## 五、核心功能 (PaperDatabase)

```python
class PaperDatabase:
    """论文数据库 - SQLite 存储"""

    def save_paper(self, paper: Paper) -> str:
        """保存论文，返回paper_id"""
        ...

    def save_papers_batch(self, papers: List[Paper]) -> int:
        """批量保存论文，返回成功数量"""
        ...

    def find_by_fingerprint(
        self,
        title: str,
        authors: List[str],
        year: int
    ) -> Optional[Paper]:
        """通过指纹查重（MD5(title+authors+year)）"""
        ...

    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """根据ID获取论文"""
        ...

    def search_papers(
        self,
        query: str = None,
        year: int = None,
        source: str = None,
        limit: int = 20
    ) -> List[Paper]:
        """搜索论文"""
        ...

    def delete_paper(self, paper_id: str) -> bool:
        """删除论文"""
        ...
```

## 六、查重机制 (指纹识别)

```python
def _compute_fingerprint(title: str, authors: str, year: int) -> str:
    """
    计算论文指纹用于去重

    使用 MD5(title + authors + year) 生成唯一指纹
    """
    content = f"{title.lower()}|{authors lower()}|{year}"
    return hashlib.md5(content.encode()).hexdigest()

def find_by_fingerprint(
    self,
    title: str,
    authors: List[str],
    year: int
) -> Optional[Paper]:
    """查重检测，返回已存在论文的ID"""
    # 1. 计算指纹
    authors_str = "|".join(authors)
    fingerprint = self._compute_fingerprint(title, authors_str, year)

    # 2. 查询指纹表
    existing = self.db.query(
        "SELECT * FROM papers WHERE fingerprint = ?",
        (fingerprint,)
    )

    if existing:
        return Paper(**existing[0])

    return None
```

## 七、在工作流中的集成

```python
# workflow_api.py
from ..storage.paper_db import PaperDatabase

class WorkflowAPI:
    def __init__(self):
        self.paper_db = PaperDatabase()

    async def save_papers(self, papers: List[dict]):
        """保存论文到存储"""
        for paper_data in papers:
            paper = Paper(**paper_data)
            self.paper_db.save_paper(paper)
```

---

**更新日期**: 2026-05-03
**基于代码**: `src/agents_v2/storage/paper_db.py`
**变更**: v2.0 移除 ChromaDB 向量存储，统一使用 SQLite