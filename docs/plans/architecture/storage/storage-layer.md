# Storage 存储层详解

> 位置: `src/agents_v2/storage/`

## 一、架构概览

```
storage/
├── __init__.py
└── paper_db.py     # SQLite + ChromaDB 双存储
```

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
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   SQLite        │  │   ChromaDB      │                  │
│  │   (元数据)       │  │   (向量)        │                  │
│  │                 │  │                 │                  │
│  │  Paper表        │  │  paper_embeddings│                 │
│  │  Citations表    │  │                 │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                           │
│           ▼                    ▼                           │
│  ┌─────────────────────────────────────────────┐          │
│  │  Paper DB (data/papers.db)                   │          │
│  └─────────────────────────────────────────────┘          │
│                                                        │
│  ┌─────────────────────────────────────────────┐          │
│  │  ChromaDB (data/chroma_db/)                   │          │
│  └─────────────────────────────────────────────┘          │
└────────────────────────────────────────────────────────────┘
```

## 四、存储路径

```
data/
├── papers.db         # SQLite数据库
│   └── Paper表: id, title, authors, year, abstract, ...
└── chroma_db/       # ChromaDB向量存储
    └── paper_embeddings/
```

## 五、核心功能

### 5.1 论文CRUD

```python
class PaperDB:
    """论文数据库"""

    def insert_paper(self, paper: Paper) -> str:
        """插入论文，返回paper_id"""
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

### 5.2 向量搜索

```python
class ChromaStore:
    """ChromaDB向量存储"""

    def add_embeddings(
        self,
        texts: List[str],
        ids: List[str],
        metadata: List[dict] = None
    ):
        """添加向量嵌入"""
        ...

    def similarity_search(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[dict]:
        """语义相似度搜索"""
        ...
```

### 5.3 查重机制

```python
def check_duplicate(self, paper: Paper) -> Optional[str]:
    """查重检测，返回已存在论文的ID"""
    # 1. DOI精确匹配
    if paper.doi:
        existing = self.db.query(
            "SELECT paper_id FROM papers WHERE doi = ?",
            (paper.doi,)
        )
        if existing:
            return existing[0]

    # 2. 标题+作者+年份 模糊匹配
    title_hash = hashlib.md5(paper.title.lower().encode()).hexdigest()
    ...
```

## 六、在工作流中的集成

```python
# workflow_api.py
from ..storage.paper_db import PaperDB

class WorkflowAPI:
    def __init__(self):
        self.paper_db = PaperDB()

    async def save_papers(self, papers: List[dict]):
        """保存论文到存储"""
        for paper_data in papers:
            paper = Paper(**paper_data)
            self.paper_db.insert_paper(paper)
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/storage/`