# Paper Agent Skill 需求文档

> 创建时间: 2026-04-27
> 状态: 进行中
> 优先级说明: P0=立即实现, P1=下一迭代, P2=后续增强

---

## 一、需求概述

本文档定义 Paper Agent 项目所需的外部 Skill 集成需求，基于业界调研和代码分析确定优先级。

---

## 二、Skill 需求清单

### 2.1 论文搜索增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| SS-001 | **Semantic Scholar API** | P0 | ✅ 已实现 | 接入真实 GraphQL API | `search/semantic_scholar_searcher.py` |
| SS-002 | **OpenAlex API** | P1 | ✅ 已实现 | 新增数据源 | `search/openalex_searcher.py` |
| SS-003 | **CrossRef API** | P1 | 模拟实现 | 接入真实 API | `tools/extended_search.py` |
| SS-004 | **Connected Papers API** | P2 | 无 | 引文网络可视化 | `knowledge_graph/kg_service.py` |
| SS-005 | **DBLP API** | P2 | 模拟实现 | 计算机会议论文 | `search/dblp_searcher.py` |

### 2.2 论文写作增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| WR-001 | **Trinka AI API** | P0 | ✅ 已实现 | 集成专业语法检查 | `writing/smart_reviser.py` |
| WR-002 | **Grammarly API** | P1 | 无 | 语法检查增强 | `writing/smart_reviser.py` |
| WR-003 | **LaTeX 模板库** | P1 | 基础实现 | 扩展期刊模板 | `tools/paper_tools.py` |
| WR-004 | **Zotero API** | P2 | ✅ 已实现 | 引用管理集成 | `tools/zotero_client.py` |
| WR-005 | **Paperpal API** | P2 | 无 | 学术润色 | `writing/smart_reviser.py` |

### 2.3 论文审核增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| RV-001 | **iThenticate API** | P1 | 本地Jaccard | 学术查重 | `problem_oriented/plagiarism_checker.py` |
| RV-002 | **引用验证** | P1 | 格式检查 | 真实性核验 | `qa/citation_manager.py` |
| RV-003 | **Scite API** | P2 | 无 | 引用分析 | `qa/citation_manager.py` |
| RV-004 | **创新性评估模型** | P2 | 基础 | 增强评估维度 | `paper_agents/reviewer_agent.py` |

### 2.4 检索增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| RT-001 | **ColBERT Reranker** | P1 | CrossEncoder | 升级重排序 | `retrieval/cross_encoder_reranker.py` |
| RT-002 | **BGE Reranker** | P1 | 无 | 中文支持增强 | `retrieval/` |
| RT-003 | **BM25S** | P2 | 基础BM25 | 升级检索 | `retrieval/` |

### 2.5 PDF解析增强

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| PDF-001 | **Marker** | P1 | ✅ 已实现 | 公式转LaTeX，代码块保留 | `tools/marker_pdf_parser.py` |
| PDF-002 | **Nougat** | P2 | 无 | 学术公式识别，MathML输出 | `tools/` |
| PDF-003 | **PDF-Extract-Kit** | P2 | 无 | 中文文档，复杂布局 | `tools/` |

### 2.6 图表生成

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| CG-001 | **Matplotlib** | P1 | 无 | 论文级图表生成，PDF矢量输出 | `tools/chart_generator.py` |
| CG-002 | **Plotly** | P2 | 无 | 交互式图表，用于报告预览 | `tools/` |

### 2.7 引用管理

| 序号 | Skill | 优先级 | 现状 | 改进建议 | 集成位置 |
|------|-------|--------|------|----------|----------|
| CM-001 | **Zotero API** | P2 | 无 | 文献检索，引用生成，BibTeX导出 | `qa/citation_manager.py` |
| CM-002 | **Mendeley API** | P2 | 无 | 不推荐（API已降级） | - |

---

## 三、优先级实现计划

### 3.1 P0 - 立即实现

#### SS-001: Semantic Scholar API

**问题**: 当前 `semantic_scholar_searcher.py` 使用 `_mock_search()` 返回假数据

**解决方案**:
```python
# 文件: src/agents_v2/search/semantic_scholar_searcher.py
import aiohttp

class SemanticScholarSearcher(BaseSearcher):
    API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,citationCount,venue,externalIds"
        }
        headers = {"x-api-key": self.API_KEY} if self.API_KEY else {}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                data = await resp.json()
                # 解析返回数据...
```

**API申请**: https://api.semanticscholar.org/

---

#### WR-001: Trinka AI API

**问题**: `LanguagePolisherAgent` 纯 LLM 实现，专业性不足

**解决方案**:
```python
# 文件: src/agents_v2/writing/smart_reviser.py

class LanguagePolisherAgent(WritingAgentBase):
    TRINKA_API_KEY = os.getenv("TRINKA_API_KEY")

    async def _check_grammar_with_api(self, text: str) -> List[Dict]:
        """使用 Trinka API 进行专业语法检查"""
        if not self.TRINKA_API_KEY:
            return await self._check_grammar(text)  # 回退到 LLM

        url = "https://api.trinka.ai/api/v1/document/check"
        headers = {"Authorization": f"Bearer {self.TRINKA_API_KEY}"}
        data = {"content": text, "language": "en"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                result = await resp.json()
                return self._parse_trinka_result(result)
```

**API申请**: https://www.trinka.ai/

---

### 3.2 P1 - 下一迭代

#### SS-002: OpenAlex API

**新增文件**: `src/agents_v2/search/openalex_searcher.py`

OpenAlex 是免费开源的学术论文 API，覆盖 2 亿+ 论文。

```python
# 核心实现
class OpenAlexSearcher(BaseSearcher):
    BASE_URL = "https://api.openalex.org"

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        url = f"{self.BASE_URL}/works"
        params = {
            "search": query,
            "per-page": max_results,
            "select": "id,title,authors,abstract_inverted_index,publication_year,cited_by_count"
        }
        # 实现...
```

**API文档**: https://docs.openalex.org/

---

#### SS-003: CrossRef API

**改进位置**: `src/agents_v2/tools/extended_search.py`

```python
# 增强 get_doi_metadata
async def get_doi_metadata(doi: str) -> Dict:
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()
```

**API文档**: https://www.crossref.org/documentation/retrieve-metadata/

---

#### WR-002: Grammarly API

**改进位置**: `src/agents_v2/writing/smart_reviser.py`

Grammarly 提供专业语法检查 API，可作为 Trinka 的替代或补充。

---

#### RV-001: iThenticate API

**改进位置**: `src/agents_v2/problem_oriented/plagiarism_checker.py`

iThenticate 是学术查重金标准，但需要机构授权。可考虑：
- 直接集成 API
- 或使用 Turnitin API
- 或对接学校机构的查重服务

---

#### RT-001: ColBERT Reranker

**改进位置**: `src/agents_v2/retrieval/cross_encoder_reranker.py`

```python
# 升级重排序模型
class CrossEncoderReranker:
    def __init__(self):
        self.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        # 可升级到: "colbert-ir/colbertv2.0"
```

---

### 3.3 P2 - 后续增强

| 序号 | Skill | 说明 | 集成位置 |
|------|-------|------|----------|
| SS-004 | Connected Papers API | 引文网络可视化 | `knowledge_graph/` |
| SS-005 | DBLP API | 计算机会议论文 | `search/dblp_searcher.py` |
| WR-003 | LaTeX 模板库 | IEEE/ACM/Nature 模板 | `tools/` |
| WR-004 | Zotero API | 引用管理 | `qa/citation_manager.py` |
| WR-005 | Paperpal API | 学术润色 | `writing/` |
| RV-003 | Scite API | 智能引用分析 | `qa/citation_manager.py` |
| RV-004 | 创新性评估模型 | 增强 ReviewerAgent | `paper_agents/` |
| RT-002 | BGE Reranker | 中文检索增强 | `retrieval/` |
| RT-003 | BM25S | 高性能 BM25 | `retrieval/` |

---

## 四、多数据源论文搜索需求

### 4.1 需求描述

Paper Agent 需要从多个学术数据库搜索论文，目前支持：
- arXiv (已完整实现)
- PubMed (已完整实现)
- Semantic Scholar (模拟，需真实API)

### 4.2 推荐新增数据源

| 数据源 | API | 覆盖范围 | 优先级 |
|--------|-----|---------|--------|
| **OpenAlex** | https://api.openalex.org | 2亿+论文，开源免费 | P1 |
| **CrossRef** | https://api.crossref.org | 期刊论文元数据 | P1 |
| **DBLP** | https://api.dblp.org | 计算机会议/期刊 | P2 |
| **Semantic Scholar** | https://api.semanticscholar.org | AI领域强 | P0 |
| **arXiv** | https://export.arxiv.org/api | 预印本 | 已实现 |
| **PubMed** | https://eutils.ncbi.nlm.nih.gov | 生物医学 | 已实现 |

### 4.3 多数据源搜索架构

```
用户查询
    │
    ▼
┌─────────────────┐
│  SearchFactory  │  ← 搜索工厂，统一入口
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ arXiv  │ │PubMed │
│Searcher│ │Searcher│
└────────┘ └────────┘
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│OpenAlex│ │  SS   │
│Searcher│ │Searcher│  ← 新增
└────────┘ └────────┘
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│ ResultMerger    │  ← 结果合并、去重
└────────┬────────┘
         │
         ▼
    统一结果格式
```

### 4.4 多数据源搜索API对比

| 数据库 | API端点 | 特点 | 速率限制 |
|--------|---------|------|----------|
| **arXiv** | `https://export.arxiv.org/api/query` | 免费，支持字段查询/布尔运算/日期范围 | 1 req/3s |
| **PubMed** | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | E-utilities API，需要API Key提高限额 | 3 req/s (无key) / 10 req/s (有key) |
| **Semantic Scholar** | `https://api.semanticscholar.org/graph/v1` | AI增强搜索，TLDR，引用图谱 | 100 req/5min (免费) |
| **OpenAlex** | `https://api.openalex.org` | 开源，跨学科，统一的Paper/Author/Institution数据 | 10 req/s |
| **CrossRef** | `https://api.crossref.org` | DOI元数据，期刊文章 | 50 req/s |
| **DBLP** | `https://api.dblp.org` | 计算机会议/期刊论文 | 公开访问 |

### 4.5 多数据源搜索实现代码

#### OpenAlex Searcher（建议新增）

```python
# 文件: src/agents_v2/search/openalex_searcher.py
import aiohttp

class OpenAlexSearcher(BaseSearcher):
    """OpenAlex学术搜索器 - 跨学科免费API"""

    BASE_URL = "https://api.openalex.org"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_filter: str = None
    ) -> SearchResponse:
        url = f"{self.BASE_URL}/works"
        params = {
            "search": query,
            "per-page": min(max_results, 200),
            "select": "id,title,authorships,abstract_inverted_index,publication_year,cited_by_count,concepts,open_access"
        }

        if year_filter:
            params["filter"] = f"publication_year:{year_filter}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                papers = [self._parse_work(w) for w in data.get("results", [])]
                return self._create_response(query, papers, self.name)

    def _parse_work(self, work: dict) -> SearchResult:
        """解析OpenAlex论文格式"""
        return SearchResult(
            paper_id=work["id"].split("/")[-1],
            title=work.get("title", ""),
            abstract=self._reconstruct_abstract(work.get("abstract_inverted_index")),
            authors=[a["author"]["display_name"] for a in work.get("authorships", [])[:5]],
            year=work.get("publication_year", 2024),
            venue=work.get("primary_location", {}).get("source", {}).get("display_name", ""),
            url=work.get("doi", ""),
            citations=work.get("cited_by_count", 0)
        )
```

#### Semantic Scholar Searcher 真实API（当前模拟）

```python
# 文件: src/agents_v2/search/semantic_scholar_searcher.py

class SemanticScholarSearcher(BaseSearcher):
    """Semantic Scholar搜索器 - AI增强学术搜索"""

    API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search(self, query: str, max_results: int = 10) -> SearchResponse:
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,citationCount,venue,externalIds"
        }
        headers = {"x-api-key": self.API_KEY} if self.API_KEY else {}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                data = await resp.json()
                papers = [self._parse_paper(p) for p in data.get("data", [])]
                return self._create_response(query, papers, self.name)
```

### 4.6 项目已有搜索组件

| 文件路径 | 类/模块 | 功能 |
|---------|--------|------|
| `search/search_factory.py` | `SearchFactory` | 搜索器工厂，统一管理多个搜索器 |
| `search/arxiv_searcher.py` | `ArxivSearcher` | arXiv论文搜索 |
| `search/pubmed_searcher.py` | `PubmedSearcher` | PubMed生物医学文献搜索 |
| `search/semantic_scholar_searcher.py` | `SemanticScholarSearcher` | Semantic Scholar搜索 |
| `mcp/search/arxiv_mcp.py` | `ArxivMCPClient` | ArXiv MCP协议实现 |
| `mcp/search/pubmed_mcp.py` | `PubmedMCPClient` | PubMed MCP实现 |
| `qa/paper_search.py` | `PaperSearchAgent` | 综合论文搜索Agent |

### 4.7 实现计划

#### Phase 1: Semantic Scholar 真实 API (P0)
- 申请 API Key: https://api.semanticscholar.org/
- 修改 `semantic_scholar_searcher.py`
- 测试搜索功能

#### Phase 2: OpenAlex 新数据源 (P1)
- 新建 `openalex_searcher.py`
- 实现 SearchFactory 支持
- 实现结果合并

#### Phase 3: CrossRef DOI 解析 (P1)
- 增强 `extended_search.py`
- 实现 DOI 元数据获取

#### Phase 4: DBLP 计算机文献 (P2)
- 新建 `dblp_searcher.py`
- 覆盖计算机领域

---

### 4.8 PDF解析工具对比

| 工具 | GitHub | 公式支持 | 表格支持 | 速度 | 推荐度 |
|------|--------|----------|----------|------|--------|
| **Marker** | VikParuchuri/marker | ⭐⭐⭐⭐⭐ LaTeX输出 | ⭐⭐⭐⭐ | 快 | ⭐⭐⭐⭐⭐ |
| **Nougat** | facebookresearch/nougat | ⭐⭐⭐⭐⭐ MathML | ⭐⭐⭐ | 慢 | ⭐⭐⭐⭐ |
| **PDF-Extract-Kit** | UFAL/pdf-extract-kit | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中 | ⭐⭐⭐⭐ |

**推荐选择**:
- 通用学术论文: **Marker** (安装简单，速度快)
- 公式为主论文: **Nougat** (Meta出品，公式最准)
- 复杂布局中文: **PDF-Extract-Kit**

### 4.9 图表生成工具对比

| 工具 | 输出格式 | 论文适用性 | 学习曲线 | 推荐度 |
|------|----------|------------|----------|--------|
| **Matplotlib** | PDF/SVG/PNG | ⭐⭐⭐⭐⭐ | 陡 | ⭐⭐⭐⭐⭐ |
| **Plotly** | HTML/PNG | ⭐⭐⭐ (仅预览) | 缓 | ⭐⭐⭐ |
| **ECharts** | HTML | ⭐ (不推荐) | 中 | ⭐ |

**推荐方案**:
- 论文正式图表: **Matplotlib + PDF/EPS**
- 交互式报告: **Plotly (HTML导出)**
- 不推荐 ECharts 用于学术论文

### 4.10 引用管理API对比

| 工具 | API完整性 | 免费可用 | 推荐度 |
|------|-----------|----------|--------|
| **Zotero** | ⭐⭐⭐⭐⭐ 完整REST | ⭐⭐⭐⭐⭐ 完全免费 | ⭐⭐⭐⭐⭐ |
| **Mendeley** | ⭐⭐ 严重降级 | ⭐⭐ 受限 | ⭐ |
| **EndNote** | ⭐ 无公共API | - | - |

**Zotero API核心endpoints**:
```
GET /users/{userID}/items          # 获取文献
POST /users/{userID}/items         # 创建条目
GET /users/{userID}/collections    # 获取收藏夹
```

---

## 五、Skill 优先级汇总

| 优先级 | Skill | 工作量 | 价值 |
|--------|-------|--------|------|
| **P0** | Semantic Scholar API | 中 | 高 |
| **P0** | Trinka AI 语法检查 | 中 | 高 |
| **P1** | OpenAlex API | 中 | 高 |
| **P1** | CrossRef API | 低 | 中 |
| **P1** | iThenticate 查重 | 高 | 高 |
| **P1** | ColBERT Reranker | 中 | 中 |
| **P1** | Marker PDF解析 | 中 | 高 |
| **P1** | Matplotlib 图表生成 | 中 | 高 |
| **P2** | DBLP API | 低 | 中 |
| **P2** | Zotero 集成 | 中 | 中 |
| **P2** | BGE Reranker | 中 | 中 |
| **P2** | Nougat PDF解析 | 中 | 中 |
| **P2** | 本地LLM部署 (Ollama) | 中 | 中 |
| **P2** | GraphRAG | 高 | 高 |

---

## 六、多Agent协作框架对比

### 6.1 框架对比

| 维度 | CrewAI | LangChain/LangGraph | AutoGen |
|------|--------|---------------------|---------|
| **抽象层次** | 高层 | 中低层 | 中层 |
| **学习曲线** | 平缓 | 陡峭 | 中等 |
| **多Agent原生** | 是 | 需LangGraph | 是 |
| **人机协作** | 一般 | 一般 | 强 |
| **代码执行** | 需自集成 | 需自集成 | 内置 |
| **社区生态** | 增长中 | 成熟 | 活跃 |
| **维护方** | CrewAI Inc. | LangChain AI | Microsoft |

### 6.2 框架选择建议

| 场景 | 推荐框架 |
|------|----------|
| 快速构建多角色工作流 | **CrewAI** |
| 深度定制复杂工作流 | **LangGraph** |
| 人机协作+代码执行 | **AutoGen** |

### 6.3 本地LLM部署对比

| 工具 | 特点 | 推荐度 |
|------|------|--------|
| **Ollama** | 命令行优先，API兼容OpenAI | ⭐⭐⭐⭐⭐ |
| **LM Studio** | 桌面GUI，快速原型 | ⭐⭐⭐⭐ |
| **LocalAI** | 企业级，Kubernetes友好 | ⭐⭐⭐⭐ |

---

## 七、知识图谱相关Skill

### 7.1 核心组件

| 组件 | 工具 | 说明 |
|------|------|------|
| **实体识别** | spaCy / LLM-based | 从文本提取实体 |
| **关系抽取** | Stanford NLP / LLM-based | 提取实体关系 |
| **图数据库** | Neo4j / JanusGraph | 存储知识图谱 |
| **GraphRAG** | Microsoft GraphRAG | 图增强检索 |

### 7.2 项目已有实现

| 组件 | 文件 | 状态 |
|------|------|------|
| 实体链接 | `knowledge_graph/kg_hybrid_retriever.py` | ✅ 已有 |
| 图嵌入 | `knowledge_graph/kg_embeddings.py` | ✅ 已有 (TransE/ComplEx) |
| 社区检测 | `knowledge_graph/kg_community.py` | ✅ 已有 (Louvain/Leiden) |
| GraphRAG | `knowledge_graph/kg_graphrag.py` | ✅ 已有 |

---

## 八、附录

### A. API 申请链接

| API | 申请地址 | 费用 |
|-----|----------|------|
| Semantic Scholar | https://api.semanticscholar.org/ | 免费/付费 |
| OpenAlex | https://docs.openalex.org/ | 免费 |
| CrossRef | https://www.crossref.org/ | 免费 |
| Trinka AI | https://www.trinka.ai/ | 付费 |
| iThenticate | https://www.ithenticate.com/ | 机构付费 |
| Grammarly | https://www.grammarly.com/ | 付费 |

### B. GitHub 开源参考项目

#### 多源学术搜索开源项目

| 项目 | GitHub | Stars | 功能 | 技术栈 |
|------|--------|-------|------|--------|
| **GPT-Researcher** | assafelovic/gpt-researcher | 26,739+ | 多Agent研究助手，自动搜索/比较/总结 | Python, LangChain, Tavily |
| **PaperQA** | fairybio/paperqa | 8,422+ | 科学文献RAG，支持PubMed/arxiv/其他 | Python, LangChain, Anthropic |
| **Haystack** | deepset-ai/haystack | 14,800+ | 多源RAG框架，支持40+数据源 | Python, Elasticsearch, FAISS |
| **cite/seek** | atw1028/cite-seek | 1,500+ | 学术搜索聚合器 | Python |
| **Multi-Searcher** | - | - | 多数据源学术搜索原型 | Python |

#### 核心项目分析

**GPT-Researcher** (推荐参考)
```python
# 架构特点:
# - 多Agent协作：规划Agent + 搜索Agent + 写作Agent
# - 自动选择最佳数据源
# - 并行搜索 + 结果去重
# - 支持 Tavily, SerpAPI, Google Scholar 等搜索API

# 关键代码模式:
async def research(self, query):
    # 1. 规划阶段 - 确定搜索策略
    plan = await self.planner.create_plan(query)

    # 2. 并行搜索多个数据源
    results = await asyncio.gather(
        self.search_arxiv(query),
        self.search_pubmed(query),
        self.search_semantic_scholar(query),
        ...
    )

    # 3. 结果合并与去重
    unified = self.deduplicate(results)

    # 4. 生成报告
    return await self.writer.write(unified)
```

**PaperQA** (推荐参考)
```python
# 架构特点:
# - 专为科学论文设计的RAG
# - 内置PDF解析 + 引用提取
# - 支持"获取论文并提问"端到端流程

# 关键功能:
qa = PaperQA("papers/*.pdf")
answer = qa.query("What methods were used?")
```

**Haystack** (框架参考)
```python
# 架构特点:
# - 模块化设计：DocumentStore / Retriever / Reader
# - 支持 Elasticsearch, FAISS, Pinecone 等向量存储
# - 支持 DeepSet, HuggingFace, OpenAI 等LLM

from haystack import Pipeline
p = Pipeline()
p.add_node(component=retriever, name="Retriever", inputs=["Query"])
p.add_node(component=reader, name="Reader", inputs=["Retriever"])
```

#### 多源搜索技术方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **GPT-Researcher 模式** | Agent自主决策，易扩展 | 成本较高 | 深度研究任务 |
| **Haystack 模式** | 成熟稳定，组件丰富 | 学习曲线较陡 | 生产级RAG系统 |
| **PaperQA 模式** | 专为论文设计 | 定制化程度低 | 快速问答场景 |
| **自研多源搜索** | 完全可控，可定制 | 开发工作量大 | 深度定制需求 |

#### 建议集成方式

```python
# 在 PaperAgent 中集成多源搜索能力
# 文件: src/agents_v2/qa/paper_search.py

class MultiSourcePaperSearcher:
    """多源论文搜索器"""

    def __init__(self):
        self.searchers = {
            "arxiv": ArxivSearcher(),
            "pubmed": PubmedSearcher(),
            "semantic_scholar": SemanticScholarSearcher(),
            "openalex": OpenAlexSearcher(),  # 新增
        }

    async def search(self, query: str, sources: List[str] = None) -> SearchResponse:
        sources = sources or list(self.searchers.keys())

        # 并行搜索多个数据源
        tasks = [
            self.searchers[source].search(query)
            for source in sources
            if source in self.searchers
        ]
        results = await asyncio.gather(*tasks)

        # 合并结果
        return self._merge_results(results)
```

---

**最后更新**: 2026-04-27
