# 学术论文统一数据结构设计

## 调研范围

| 平台 | API 格式 | 文档 |
|------|---------|------|
| arXiv | Atom/XML | https://info.arxiv.org/help/api/index.html |
| CrossRef | JSON | https://api.crossref.org/swagger-ui/index.html |
| OpenAlex | JSON | https://docs.openalex.org/api-entities/works |
| Semantic Scholar | JSON | https://api.semanticscholar.org/api-docs/ |
| PubMed | XML (E-utilities) | https://www.ncbi.nlm.nih.gov/books/NBK25500/ |

---

## 各平台返回字段对照

### 字段对照表

| 统一字段 | arXiv | CrossRef | OpenAlex | Semantic Scholar | PubMed |
|---------|-------|----------|----------|-----------------|--------|
| **标识符** | | | | | |
| doi | arxiv:doi | DOI | doi | externalIds.DOI | ArticleId[@IdType="doi"] |
| arxiv_id | id (提取) | — | — | externalIds.ArXiv | — |
| pubmed_id | — | — | — | externalIds.PubMed | PMID |
| openalex_id | — | — | id | — | — |
| semantic_scholar_id | — | — | — | paperId | — |
| **标题** | | | | | |
| title | title | title[0] | title | title | ArticleTitle |
| **作者** | | | | | |
| authors[].name | author.name | "{given} {family}" | authorships[].author.display_name | authors[].name | LastName+ForeName |
| authors[].orcid | — | author.ORCID | — | — | — |
| authors[].affiliation | arxiv:affiliation | author.affiliation | authorships[].institutions[].display_name | authors[].affiliations | AffiliationInfo |
| **日期** | | | | | |
| year | published (提取) | published-print.date-parts[0][0] | publication_year | year | PubDate.Year |
| published_date | published | published-online.date-parts | publication_date | — | PubDate (完整) |
| **来源** | | | | | |
| venue | primary_category | container-title[0] | primary_location.source.display_name | venue | Journal/Title |
| volume | — | volume | — | — | Volume |
| issue | — | issue | — | — | Issue |
| pages | — | page | — | — | MedlinePgn |
| **内容** | | | | | |
| abstract | summary | abstract | abstract_inverted_index | abstract | AbstractText |
| **分类** | | | | | |
| categories | category[] | subject[] | concepts[].display_name | — | — |
| keywords | — | — | keywords[].keyword | — | KeywordList |
| mesh_terms | — | — | — | — | MeshHeadingList |
| **引用** | | | | | |
| citation_count | — | is-referenced-by-count | cited_by_count | citationCount | — |
| references | — | reference[] | referenced_works | references[] | — |
| **链接** | | | | | |
| url | id | URL | id | url | — |
| pdf_url | link[pdf] | — | best_oa_location.pdf_url | openAccessPdf.url | — |
| **开放获取** | | | | | |
| is_open_access | (隐含) | — | open_access.is_oa | isOpenAccess | — |
| oa_status | — | — | open_access.oa_status | — | — |
| oa_url | — | — | open_access.oa_url | openAccessPdf.url | — |
| **资助** | | | | | |
| funders | — | funder[] | grants[] | — | — |
| **其他** | | | | | |
| language | — | — | language | — | Language |
| publication_type | — | type | type | — | PublicationType |
| issn | — | ISSN[] | — | — | — |
| journal_ref | arxiv:journal_ref | — | — | — | — |

---

## 各平台独有字段

### arXiv 独有
- `primary_category` — 主分类 (如 cs.AI)
- `comment` — 作者注释 (如 "15 pages, 5 figures")
- `journal_ref` — 期刊引用 (如已发表)
- `version` — 版本号 (v1, v2, ...)

### CrossRef 独有
- `reference` — 完整参考文献列表 (DOI + 作者 + 标题)
- `license` — 许可证信息
- `ISSN` — 期刊 ISSN
- `container-title` — 容器标题 (期刊/会议名)
- `published-print` / `published-online` — 分别跟踪印刷版和在线版日期

### OpenAlex 独有
- `abstract_inverted_index` — 倒排索引格式的摘要
- `concepts` — 关联概念 (带分数)
- `topics` — 关联主题 (新字段)
- `sustainable_development_goals` — SDG 分类
- `best_oa_location` — 最佳开放获取位置
- `locations` — 所有可用位置列表

### Semantic Scholar 独有
- `fieldsOfStudy` — 研究领域
- `influentialCitationCount` — 有影响力的引用数
- `tldr` — AI 生成的摘要简版
- `citationStyles` — 多格式引用样式
- `embedding.specter_v2` — 论文嵌入向量

### PubMed 独有
- `MeshHeadingList` — MeSH 主题词 (受控词表)
- `KeywordList` — 作者关键词
- `PublicationType` — 出版类型
- `GrantList` — 资助信息
- `SupplMeshList` — 补充 MeSH 词

---

## 统一数据结构设计

```python
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


# ── 作者 ──────────────────────────────────────────────


class Author(BaseModel):
    """论文作者"""
    name: str = ""                          # 全名 (如 "Yann LeCun")
    given_name: str = ""                    # 名 (CrossRef/S2)
    family_name: str = ""                   # 姓 (CrossRef/S2)
    orcid: str = ""                         # ORCID ID
    affiliations: list[str] = Field(default_factory=list)  # 机构列表
    author_id: str = ""                     # 平台内 ID (OpenAlex/S2)


# ── 标识符 ────────────────────────────────────────────


class PaperIdentifiers(BaseModel):
    """论文标识符集合"""
    doi: str = ""                           # 通用, CrossRef/OpenAlex/S2/PubMed
    arxiv_id: str = ""                      # arXiv 特有
    pubmed_id: str = ""                     # PubMed 特有
    pmc_id: str = ""                        # PubMed Central
    openalex_id: str = ""                   # OpenAlex 特有
    semantic_scholar_id: str = ""           # S2 特有
    mag_id: str = ""                        # Microsoft Academic Graph


# ── 日期 ──────────────────────────────────────────────


class PaperDates(BaseModel):
    """论文日期信息"""
    year: int | None = None                 # 出版年份 (所有平台)
    published_date: str = ""                # 完整出版日期 (YYYY-MM-DD)
    submitted_date: str = ""                # 提交日期 (arXiv)
    accepted_date: str = ""                 # 接收日期
    online_date: str = ""                   # 在线发表日期 (CrossRef)


# ── 来源 ──────────────────────────────────────────────


class PaperSource(BaseModel):
    """论文来源 (期刊/会议/预印本)"""
    venue: str = ""                         # 期刊/会议名
    venue_type: str = ""                    # journal / conference / preprint / book
    volume: str = ""                        # 卷号
    issue: str = ""                         # 期号
    pages: str = ""                         # 页码 (如 "1-15" 或 "1234-1245")
    issn: list[str] = Field(default_factory=list)  # ISSN 列表
    publisher: str = ""                     # 出版商


# ── 开放获取 ──────────────────────────────────────────


class OpenAccessInfo(BaseModel):
    """开放获取信息"""
    is_oa: bool = False                     # 是否开放获取
    oa_status: str = ""                     # gold / green / hybrid / bronze / closed
    oa_url: str = ""                        # OA 访问链接
    pdf_url: str = ""                       # PDF 直链
    license: str = ""                       # 许可证


# ── 分类 ──────────────────────────────────────────────


class PaperClassification(BaseModel):
    """论文分类信息"""
    categories: list[str] = Field(default_factory=list)     # arXiv 分类 / CrossRef subject
    concepts: list[str] = Field(default_factory=list)        # OpenAlex 概念
    topics: list[str] = Field(default_factory=list)          # OpenAlex 主题
    fields_of_study: list[str] = Field(default_factory=list) # S2 研究领域
    keywords: list[str] = Field(default_factory=list)        # 作者关键词
    mesh_terms: list[str] = Field(default_factory=list)      # PubMed MeSH 主题词


# ── 引用 ──────────────────────────────────────────────


class CitationInfo(BaseModel):
    """引用信息"""
    citation_count: int | None = None       # 总引用数 (所有平台)
    influential_citation_count: int | None = None  # 有影响力的引用 (S2)
    reference_count: int | None = None      # 参考文献数量
    references: list[str] = Field(default_factory=list)  # 参考文献 DOI 列表


# ── 资助 ──────────────────────────────────────────────


class FunderInfo(BaseModel):
    """资助信息"""
    funder_name: str = ""
    funder_doi: str = ""
    award_id: str = ""


# ── 统一论文模型 ──────────────────────────────────────


class UnifiedPaper(BaseModel):
    """
    统一学术论文数据结构

    设计原则:
    1. 所有平台都能填充的字段作为必填/默认字段
    2. 特定平台的独有数据放入 source_payload
    3. 使用空字符串/None 表示缺失，而非省略
    4. 标识符统一放在 identifiers 子模型中
    """

    # ── 唯一标识 ──
    paper_id: str = ""                      # 系统内部 ID

    # ── 标识符 ──
    identifiers: PaperIdentifiers = Field(default_factory=PaperIdentifiers)

    # ── 基本信息 ──
    title: str = ""                         # 标题 (所有平台)
    abstract: str = ""                      # 摘要 (所有平台, OpenAlex 需从倒排索引还原)
    language: str = ""                      # 语言代码 (OpenAlex/PubMed)
    publication_type: str = ""              # journal-article / conference-paper / review / preprint / book

    # ── 作者 ──
    authors: list[Author] = Field(default_factory=list)

    # ── 日期 ──
    dates: PaperDates = Field(default_factory=PaperDates)

    # ── 来源 ──
    source: PaperSource = Field(default_factory=PaperSource)

    # ── 开放获取 ──
    open_access: OpenAccessInfo = Field(default_factory=OpenAccessInfo)

    # ── 分类 ──
    classification: PaperClassification = Field(default_factory=PaperClassification)

    # ── 引用 ──
    citation: CitationInfo = Field(default_factory=CitationInfo)

    # ── 资助 ──
    funders: list[FunderInfo] = Field(default_factory=list)

    # ── URL ──
    url: str = ""                           # 论文主页 URL

    # ── 平台原始数据 ──
    source_platform: str = ""               # 来源平台: arxiv/crossref/openalex/s2/pubmed
    source_payload: dict[str, Any] = Field(default_factory=dict)  # 平台原始 JSON/XML

    # ── 系统内部字段 ──
    relevance_score: float = 0.0            # 搜索相关性分数
    quality_score: float = 0.0              # 质量评估分数
    included: bool = True                   # 是否纳入研究
    exclude_reason: str = ""                # 排除原因
```

---

## 各平台适配器映射

### arXiv → UnifiedPaper

```python
def arxiv_to_unified(entry: dict) -> UnifiedPaper:
    return UnifiedPaper(
        identifiers=PaperIdentifiers(
            doi=entry["doi"],
            arxiv_id=extract_arxiv_id(entry["id"]),
        ),
        title=entry["title"],
        abstract=entry["summary"],
        authors=[Author(name=a["name"]) for a in entry["authors"]],
        dates=PaperDates(
            year=parse_year(entry["published"]),
            published_date=entry["published"],
            submitted_date=entry.get("submitted", ""),
        ),
        source=PaperSource(
            venue=entry["primary_category"],
            venue_type="preprint",
        ),
        classification=PaperClassification(
            categories=entry["categories"],
        ),
        url=entry["id"],
        source_platform="arxiv",
        source_payload=entry,
    )
```

### CrossRef → UnifiedPaper

```python
def crossref_to_unified(work: dict) -> UnifiedPaper:
    return UnifiedPaper(
        identifiers=PaperIdentifiers(doi=work["DOI"]),
        title=work["title"][0],
        abstract=work.get("abstract", ""),
        authors=[
            Author(
                name=f'{a.get("given","")} {a.get("family","")}'.strip(),
                given_name=a.get("given", ""),
                family_name=a.get("family", ""),
                orcid=a.get("ORCID", ""),
                affiliations=[af.get("name","") for af in a.get("affiliation", [])],
            )
            for a in work.get("author", [])
        ],
        dates=PaperDates(
            year=extract_year(work),
            published_date=extract_date(work),
        ),
        source=PaperSource(
            venue=work.get("container-title", [""])[0],
            volume=work.get("volume", ""),
            issue=work.get("issue", ""),
            pages=work.get("page", ""),
            issn=work.get("ISSN", []),
            publisher=work.get("publisher", ""),
        ),
        classification=PaperClassification(
            categories=work.get("subject", []),
        ),
        citation=CitationInfo(
            citation_count=work.get("is-referenced-by-count"),
            reference_count=len(work.get("reference", [])),
            references=[r.get("DOI","") for r in work.get("reference", []) if r.get("DOI")],
        ),
        funders=[
            FunderInfo(
                funder_name=f.get("name",""),
                funder_doi=f.get("DOI",""),
                award_id=f.get("award",[""])[0] if f.get("award") else "",
            )
            for f in work.get("funder", [])
        ],
        url=work.get("URL", ""),
        source_platform="crossref",
        source_payload=work,
    )
```

### OpenAlex → UnifiedPaper

```python
def openalex_to_unified(work: dict) -> UnifiedPaper:
    return UnifiedPaper(
        identifiers=PaperIdentifiers(
            doi=work.get("doi","").replace("https://doi.org/",""),
            openalex_id=work.get("id","").replace("https://openalex.org/",""),
        ),
        title=work.get("title",""),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        language=work.get("language",""),
        publication_type=work.get("type",""),
        authors=[
            Author(
                name=a.get("author",{}).get("display_name",""),
                author_id=a.get("author",{}).get("id","").replace("https://openalex.org/",""),
                affiliations=[i.get("display_name","") for i in a.get("institutions",[])],
            )
            for a in work.get("authorships",[])
        ],
        dates=PaperDates(
            year=work.get("publication_year"),
            published_date=work.get("publication_date",""),
        ),
        source=PaperSource(
            venue=(work.get("primary_location") or {}).get("source",{}).get("display_name",""),
        ),
        open_access=OpenAccessInfo(
            is_oa=(work.get("open_access") or {}).get("is_oa",False),
            oa_status=(work.get("open_access") or {}).get("oa_status",""),
            oa_url=(work.get("open_access") or {}).get("oa_url",""),
            pdf_url=(work.get("best_oa_location") or {}).get("pdf_url",""),
        ),
        classification=PaperClassification(
            concepts=[c.get("display_name","") for c in work.get("concepts",[])],
            keywords=[k.get("keyword","") for k in work.get("keywords",[])],
        ),
        citation=CitationInfo(
            citation_count=work.get("cited_by_count"),
            references=work.get("referenced_works",[]),
        ),
        url=work.get("id",""),
        source_platform="openalex",
        source_payload=work,
    )
```

### Semantic Scholar → UnifiedPaper

```python
def s2_to_unified(paper: dict) -> UnifiedPaper:
    ext = paper.get("externalIds", {})
    return UnifiedPaper(
        identifiers=PaperIdentifiers(
            doi=ext.get("DOI",""),
            arxiv_id=ext.get("ArXiv",""),
            pubmed_id=ext.get("PubMed",""),
            semantic_scholar_id=paper.get("paperId",""),
            mag_id=ext.get("MAG",""),
        ),
        title=paper.get("title",""),
        abstract=paper.get("abstract",""),
        authors=[
            Author(
                name=a.get("name",""),
                author_id=a.get("authorId",""),
                affiliations=a.get("affiliations",[]),
            )
            for a in paper.get("authors",[])
        ],
        dates=PaperDates(year=paper.get("year")),
        source=PaperSource(
            venue=paper.get("venue",""),
        ),
        open_access=OpenAccessInfo(
            is_oa=paper.get("isOpenAccess",False),
            pdf_url=(paper.get("openAccessPdf") or {}).get("url",""),
        ),
        classification=PaperClassification(
            fields_of_study=paper.get("fieldsOfStudy",[]),
            keywords=[k for k in (paper.get("keywords") or []) if isinstance(k, str)],
        ),
        citation=CitationInfo(
            citation_count=paper.get("citationCount"),
            influential_citation_count=paper.get("influentialCitationCount"),
            reference_count=paper.get("referenceCount"),
        ),
        url=paper.get("url",""),
        source_platform="semantic_scholar",
        source_payload=paper,
    )
```

### PubMed → UnifiedPaper

```python
def pubmed_to_unified(article: dict) -> UnifiedPaper:
    medline = article.get("MedlineCitation", {})
    art = medline.get("Article", {})
    return UnifiedPaper(
        identifiers=PaperIdentifiers(
            doi=extract_doi(art),
            pubmed_id=str(medline.get("PMID","")),
        ),
        title=art.get("ArticleTitle",""),
        abstract=extract_abstract(art),
        language=art.get("Language",""),
        authors=[
            Author(
                name=f'{a.get("ForeName","")} {a.get("LastName","")}'.strip(),
                given_name=a.get("ForeName",""),
                family_name=a.get("LastName",""),
                affiliations=[af.get("Affiliation","") for af in
                    a.get("AffiliationInfo",[])],
            )
            for a in extract_authors(art)
        ],
        dates=PaperDates(
            year=extract_pub_year(art),
            published_date=extract_pub_date(art),
        ),
        source=PaperSource(
            venue=art.get("Journal",{}).get("Title",""),
            volume=art.get("Journal",{}).get("JournalIssue",{}).get("Volume",""),
            issue=art.get("Journal",{}).get("JournalIssue",{}).get("Issue",""),
            pages=art.get("Pagination",{}).get("MedlinePgn",""),
            issn=[art.get("Journal",{}).get("ISSN","")],
        ),
        classification=PaperClassification(
            mesh_terms=extract_mesh(medline),
            keywords=extract_keywords(medline),
        ),
        url=f'https://pubmed.ncbi.nlm.nih.gov/{medline.get("PMID","")}/',
        source_platform="pubmed",
        source_payload=article,
    )
```

---

## 数据结构设计决策

| 决策 | 原因 |
|------|------|
| 标识符独立子模型 | 各平台 ID 格式不同，集中管理便于跨平台关联 |
| 作者使用子模型 | 需要支持 name/given/family/orcid/affiliations |
| 日期独立子模型 | arXiv 有 submitted，CrossRef 分 print/online，需要区分 |
| 来源独立子模型 | volume/issue/pages 只有部分平台有 |
| OA 信息独立子模型 | OpenAlex 提供最丰富的 OA 数据，其他平台有限 |
| 分类独立子模型 | arXiv 用 categories，PubMed 用 MeSH，S2 用 fieldsOfStudy |
| source_payload 保留原始数据 | 避免信息丢失，特殊需求可从原始数据提取 |
| 无嵌套引用列表 | CrossRef 引用数据量大，只存 DOI 列表 |

---

## 与现有代码的对比

现有 `SearchResult` 模型：

```python
class SearchResult(BaseModel):
    title: str
    authors: list[str]           # ← 只有名字字符串
    year: int | None
    venue: str
    abstract: str
    doi: str
    arxiv_id: str
    pubmed_id: str
    semantic_scholar_id: str
    openalex_id: str
    url: str
    pdf_url: str
    citations: int | None
    concepts: list[str]
    keywords: list[str]
    source_payload: dict
```

**UnifiedPaper 改进点：**

| 方面 | SearchResult | UnifiedPaper |
|------|-------------|--------------|
| 作者 | `list[str]` | `list[Author]` (含 ORCID/机构) |
| 标识符 | 扁平字段 | `PaperIdentifiers` 子模型 |
| 日期 | 只有 year | `PaperDates` (含 submitted/accepted/online) |
| 来源 | 只有 venue | `PaperSource` (含 volume/issue/pages/ISSN) |
| OA | pdf_url | `OpenAccessInfo` (含 status/license) |
| 分类 | concepts + keywords | `PaperClassification` (含 MeSH/fields_of_study) |
| 引用 | citations | `CitationInfo` (含 influential/references) |
| 资助 | 无 | `FunderInfo` |
| 语言 | 无 | language 字段 |
| 出版类型 | 无 | publication_type 字段 |

---

## 使用建议

1. **搜索阶段**：继续使用 `SearchResult`（轻量，搜索够用）
2. **入库阶段**：转换为 `UnifiedPaper`（丰富元数据）
3. **分析阶段**：基于 `UnifiedPaper` 构建卡片/证据/图谱
4. **原始数据**：始终保留 `source_payload`，需要时可回溯

```python
# 搜索 → 统一 → 入库
results = orchestrator.search(query)           # list[SearchResult]
papers = [to_unified(r) for r in results]      # list[UnifiedPaper]
for p in papers:
    paper_library.add(p)                       # 存储
```
