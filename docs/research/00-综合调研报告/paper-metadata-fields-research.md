# 学术论文完整元数据字段调研报告

> 调研日期: 2026-05-30
> 搜索次数: 27次
> 覆盖类别: A(官方文档) B(学术论文) C(开源项目) D(技术博客) E(社区讨论) F(中英文)

---

## 一、核心概念与定义

**学术论文元数据**是指用于描述、发现、管理和引用一篇学术论文所需的结构化信息集合。不同标准和平台对元数据字段的定义有差异，但核心目标一致：**让论文可被发现、可被理解、可被引用、可被复现**。

### 主要元数据标准/平台

| 标准/平台 | 类型 | 字段数量 | 侧重 |
|-----------|------|---------|------|
| **OpenAlex** | 开放学术图谱API | 26+字段组 | 最全面的开放数据 |
| **CrossRef** | DOI注册机构 | 30+字段 | 出版元数据+引用 |
| **Semantic Scholar** | AI学术搜索 | 15+字段 | 引用+AI摘要 |
| **PubMed/MEDLINE** | 生物医学数据库 | 20+字段 | MeSH+资助信息 |
| **JATS (Z39.96)** | XML期刊标准 | 50+元素 | 论文结构+元数据 |
| **PRISM** | 出版元数据标准 | 80+字段 | 出版行业标准 |
| **DataCite 4.5** | 研究数据元数据 | 20+属性 | 数据+资助引用 |
| **Dublin Core** | 通用元数据标准 | 15元素 | 基础描述 |
| **RIS格式** | 引用管理格式 | 30+标签 | 引用导出 |
| **Zotero** | 引用管理工具 | 40+字段 | 用户友好 |

---

## 二、技术原理深度解析

### 2.1 论文元数据的三层结构

根据JATS标准和学术出版实践，论文元数据可分为三层：

```
┌─────────────────────────────────────────┐
│  第一层: 标识与描述层 (Identification)   │
│  - 唯一标识符 (DOI, PMID, arXiv ID)      │
│  - 基本描述 (标题, 摘要, 语言)           │
│  - 作者与机构                            │
│  - 来源 (期刊/会议/预印本)               │
├─────────────────────────────────────────┤
│  第二层: 内容与分类层 (Content)          │
│  - 学科分类与关键词                      │
│  - 研究方法与数据                        │
│  - 引用网络                              │
│  - 全文结构 (IMRaD)                      │
├─────────────────────────────────────────┤
│  第三层: 传播与评估层 (Dissemination)    │
│  - 开放获取状态                          │
│  - 引用计数与影响指标                    │
│  - 资助信息                              │
│  - 数据可用性声明                        │
└─────────────────────────────────────────┘
```

### 2.2 元数据来源优先级

不同平台的元数据质量和覆盖度不同：

| 来源 | 优势 | 覆盖范围 |
|------|------|---------|
| **CrossRef** | 权威DOI注册数据 | 1.5亿+文献 |
| **OpenAlex** | 最全面的开放数据 | 2.5亿+文献 |
| **Semantic Scholar** | AI增强的引用图谱 | 2亿+文献 |
| **PubMed** | 生物医学领域权威 | 3700万+文献 |
| **arXiv** | 预印本权威来源 | 250万+文献 |

---

## 三、完整字段清单（基于多标准综合）

### 3.1 标识符类 (Identifiers)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `doi` | 数字对象标识符 | CrossRef/OpenAlex/S2 | ✅ 有 | 必需 |
| `arxiv_id` | arXiv预印本ID | OpenAlex/S2 | ✅ 有 | 必需 |
| `pubmed_id` | PubMed ID (PMID) | PubMed/OpenAlex | ✅ 有 | 必需 |
| `openalex_id` | OpenAlex ID | OpenAlex | ✅ 有 | 建议 |
| `semantic_scholar_id` | S2 Paper ID | S2 | ✅ 有 | 建议 |
| `pmcid` | PubMed Central ID | OpenAlex/S2 | ❌ **缺失** | 建议 |
| `mag_id` | Microsoft Academic Graph ID | OpenAlex | ❌ **缺失** | 可选 |
| `corpus_id` | S2 Corpus ID | S2 | ❌ **缺失** | 可选 |
| `isbn` | ISBN (图书) | PRISM/CrossRef | ❌ **缺失** | 可选 |
| `issn` | ISSN (期刊) | CrossRef | ❌ **缺失** | 可选 |
| `pii` | 出版商项目标识符 | CrossRef | ❌ **缺失** | 可选 |
| `publisher_id` | 出版商内部ID | CrossRef | ❌ **缺失** | 可选 |

### 3.2 基本描述类 (Basic Description)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `title` | 论文标题 | 所有标准 | ✅ 有 | 必需 |
| `abstract` | 摘要 | 所有标准 | ✅ 有 | 必需 |
| `language` | 语言 (ISO 639-1) | OpenAlex/JATS | ✅ 有 | 必需 |
| `publication_type` | 出版类型 | CrossRef/S2 | ✅ 有 | 必需 |
| `translated_title` | 翻译标题 | JATS/PRISM | ❌ **缺失** | 建议 |
| `short_title` | 简短标题 | RIS/Zotero | ❌ **缺失** | 可选 |
| `subtitle` | 副标题 | PRISM/JATS | ❌ **缺失** | 可选 |
| `original_language` | 原始语言 | JATS | ❌ **缺失** | 可选 |
| `is_retracted` | 是否撤稿 | OpenAlex/S2 | ❌ **缺失** | 建议 |
| `is_paratext` | 是否辅助文本 | OpenAlex | ❌ **缺失** | 可选 |

### 3.3 作者类 (Authors)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `name` | 全名 | 所有标准 | ✅ 有 | 必需 |
| `given_name` | 名 | CrossRef/JATS | ✅ 有 | 必需 |
| `family_name` | 姓 | CrossRef/JATS | ✅ 有 | 必需 |
| `orcid` | ORCID标识符 | CrossRef/OpenAlex | ✅ 有 | 建议 |
| `affiliations` | 机构列表 | 所有标准 | ✅ 有 | 必需 |
| `author_position` | 作者排序位置 | OpenAlex | ❌ **缺失** | 建议 |
| `is_corresponding` | 是否通讯作者 | OpenAlex/JATS | ❌ **缺失** | 建议 |
| `email` | 邮箱 | JATS/CrossRef | ❌ **缺失** | 建议 |
| `role` | 贡献角色 (CRediT) | JATS/DataCite | ❌ **缺失** | 建议 |
| `raw_author_name` | 原始作者名 | OpenAlex | ❌ **缺失** | 可选 |
| `raw_affiliation_string` | 原始机构字符串 | OpenAlex | ❌ **缺失** | 可选 |

**CRediT贡献者角色** (14种): Conceptualization, Data curation, Formal analysis, Funding acquisition, Investigation, Methodology, Project administration, Resources, Software, Supervision, Validation, Visualization, Writing - original draft, Writing - review & editing

### 3.4 机构类 (Institutions)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `institution_name` | 机构名称 | OpenAlex/CrossRef | ❌ 隐藏在affiliations | 建议 |
| `institution_id` | 机构ID (ROR) | OpenAlex | ❌ **缺失** | 建议 |
| `institution_type` | 机构类型 | OpenAlex | ❌ **缺失** | 可选 |
| `country_code` | 国家代码 | OpenAlex | ❌ **缺失** | 建议 |
| `institution_lineage` | 机构层级 | OpenAlex | ❌ **缺失** | 可选 |

### 3.5 日期类 (Dates)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `year` | 出版年份 | 所有标准 | ✅ 有 | 必需 |
| `published_date` | 出版日期 | OpenAlex/CrossRef | ✅ 有 | 必需 |
| `created_date` | 创建日期 | OpenAlex | ❌ **缺失** | 建议 |
| `accepted_date` | 接收日期 | CrossRef/JATS | ❌ **缺失** | 建议 |
| `submitted_date` | 投稿日期 | CrossRef/JATS | ❌ **缺失** | 可选 |
| `online_date` | 在线发表日期 | CrossRef | ❌ **缺失** | 可选 |
| `cover_date` | 封面日期 | PRISM | ❌ **缺失** | 可选 |
| `revision_date` | 修订日期 | DataCite | ❌ **缺失** | 可选 |

### 3.6 来源类 (Source/Venue)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `venue` | 期刊/会议名称 | 所有标准 | ✅ 有 | 必需 |
| `volume` | 卷号 | CrossRef/OpenAlex | ✅ 有 | 必需 |
| `issue` | 期号 | CrossRef/OpenAlex | ✅ 有 | 必需 |
| `pages` | 页码范围 | CrossRef/OpenAlex | ✅ 有 | 必需 |
| `first_page` | 起始页码 | OpenAlex | ❌ **缺失** | 建议 |
| `last_page` | 结束页码 | OpenAlex | ❌ **缺失** | 建议 |
| `journal_abbrev` | 期刊缩写 | PubMed/RIS | ❌ **缺失** | 建议 |
| `issn` | 期刊ISSN | CrossRef | ❌ **缺失** | 建议 |
| `publisher` | 出版商 | CrossRef/DataCite | ❌ **缺失** | 建议 |
| `editor` | 编辑 | CrossRef/Zotero | ❌ **缺失** | 可选 |
| `series` | 丛书 | Zotero | ❌ **缺失** | 可选 |
| `edition` | 版次 | Zotero/PRISM | ❌ **缺失** | 可选 |

### 3.7 开放获取类 (Open Access)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `is_oa` | 是否开放获取 | OpenAlex/CrossRef | ✅ 有 | 必需 |
| `oa_status` | OA状态 | OpenAlex | ✅ 有 | 建议 |
| `pdf_url` | PDF链接 | OpenAlex/S2 | ✅ 有 | 必需 |
| `license` | 许可证 | OpenAlex/CrossRef | ✅ 有 | 建议 |
| `landing_page_url` | 出版商落地页 | OpenAlex | ❌ **缺失** | 建议 |
| `repository_url` | 仓储链接 | OpenAlex | ❌ **缺失** | 可选 |
| `best_open_version` | 最佳开放版本 | OpenAlex | ❌ **缺失** | 可选 |

**OA状态类型**: gold, hybrid, bronze, green, closed

### 3.8 分类与主题类 (Classification)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `categories` | 分类 | OpenAlex | ✅ 有 | 建议 |
| `concepts` | 概念 | OpenAlex | ✅ 有 | 建议 |
| `keywords` | 关键词 | 所有标准 | ✅ 有 | 必需 |
| `fields_of_study` | 研究领域 | S2 | ✅ 有 | 建议 |
| `mesh_terms` | MeSH主题词 | PubMed | ✅ 有 | 建议 |
| `topics` | 主题 (4级层次) | OpenAlex | ❌ **缺失** | 建议 |
| `primary_topic` | 主要主题 | OpenAlex | ❌ **缺失** | 建议 |
| `subject_scheme` | 主题词表 | DataCite | ❌ **缺失** | 可选 |
| `sustainable_development_goals` | 可持续发展目标 | OpenAlex | ❌ **缺失** | 可选 |

**OpenAlex主题层次**: Domain → Field → Subfield → Topic (共4500+主题)

### 3.9 引用类 (Citations)

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `citation_count` | 被引次数 | OpenAlex/S2 | ✅ 有 | 必需 |
| `influential_citation_count` | 有影响力的引用数 | S2 | ✅ 有 | 建议 |
| `reference_count` | 参考文献数 | OpenAlex/S2 | ✅ 有 | 建议 |
| `references` | 参考文献列表 | OpenAlex/S2 | ✅ 有 | 建议 |
| `cited_by_count` | 被引总数 | OpenAlex | ❌ 可能重复 | 可选 |
| `fwci` | 场加权引用影响 | OpenAlex | ❌ **缺失** | 建议 |
| `citation_normalized_percentile` | 引用百分位 | OpenAlex | ❌ **缺失** | 可选 |
| `cited_by_percentile_year` | 年度引用百分位 | OpenAlex | ❌ **缺失** | 可选 |
| `related_works` | 相关文献 | OpenAlex/S2 | ❌ **缺失** | 建议 |
| `referenced_works` | 引用的OpenAlex ID | OpenAlex | ❌ **缺失** | 可选 |

### 3.10 资助信息类 (Funding) ⭐ 当前模型完全缺失

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `funder_name` | 资助机构名称 | CrossRef/OpenAlex | ❌ **缺失** | 建议 |
| `funder_id` | 资助机构ID | CrossRef/OpenAlex | ❌ **缺失** | 建议 |
| `award_id` | 项目编号 | CrossRef/OpenAlex | ❌ **缺失** | 建议 |
| `award_title` | 项目名称 | DataCite | ❌ **缺失** | 可选 |

### 3.11 数据可用性类 (Data Availability) ⭐ 当前模型完全缺失

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `data_availability_statement` | 数据可用性声明 | PLOS/Springer Nature | ❌ **缺失** | 建议 |
| `data_repository` | 数据仓库名称 | DataCite | ❌ **缺失** | 可选 |
| `data_doi` | 数据集DOI | DataCite | ❌ **缺失** | 可选 |
| `code_repository` | 代码仓库链接 | Open Science | ❌ **缺失** | 可选 |
| `preregistration_url` | 预注册链接 | Open Science | ❌ **缺失** | 可选 |

### 3.12 论文结构类 (Paper Structure) ⭐ 当前模型完全缺失

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `section_count` | 章节数 | JATS | ❌ **缺失** | 可选 |
| `figure_count` | 图数 | JATS | ❌ **缺失** | 可选 |
| `table_count` | 表数 | JATS | ❌ **缺失** | 可选 |
| `reference_count` | 参考文献数 | OpenAlex | ✅ 有 | 建议 |
| `page_count` | 总页数 | PRISM | ❌ **缺失** | 可选 |
| `word_count` | 字数 | PRISM | ❌ **缺失** | 可选 |
| `supplementary_materials` | 补充材料 | JATS | ❌ **缺失** | 可选 |

### 3.13 冲突与伦理类 (Conflict & Ethics) ⭐ 当前模型完全缺失

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `conflict_of_interest` | 利益冲突声明 | JMIR/COPE | ❌ **缺失** | 可选 |
| `ethics_statement` | 伦理声明 | JATS | ❌ **缺失** | 可选 |
| `author_contributions` | 作者贡献声明 | CRediT/JATS | ❌ **缺失** | 可选 |
| `acknowledgments` | 致谢 | JATS | ❌ **缺失** | 可选 |

### 3.14 评估指标类 (Metrics) ⭐ 当前模型部分缺失

| 字段 | 说明 | 来源标准 | 当前模型 | 优先级 |
|------|------|---------|---------|--------|
| `citation_count` | 被引次数 | 所有平台 | ✅ 有 | 必需 |
| `fwci` | 场加权引用影响 | OpenAlex | ❌ **缺失** | 建议 |
| `sjr` | SCImago期刊排名 | Scopus | ❌ **缺失** | 可选 |
| `jif` | 期刊影响因子 | JCR/WoS | ❌ **缺失** | 可选 |
| `altmetric_score` | 替代计量指标 | Altmetric | ❌ **缺失** | 可选 |

---

## 四、主流技术方案对比

### 4.1 各平台API返回字段对比

| 字段类别 | OpenAlex | CrossRef | Semantic Scholar | PubMed |
|---------|----------|---------|-----------------|--------|
| **标识符** | doi, openalex, mag, pmid, pmcid | doi | paperId, corpusId | pmid, pmcid |
| **标题** | title, display_name | title | title | TI |
| **摘要** | abstract_inverted_index | abstract (部分) | abstract (tldr) | AB |
| **作者** | authorships (含机构) | author (含ORCID) | authors | AU, AD |
| **日期** | publication_date, year | published-print, published-online | year | DP, DA |
| **来源** | primary_location.source | container-title, volume, issue | venue | JT, VI, IP |
| **OA** | open_access.is_oa, oa_status | license, link | isOpenAccess, openAccessPdf | PMC链接 |
| **分类** | topics, concepts, keywords | subject | fieldsOfStudy | MH, OT |
| **引用** | cited_by_count, fwci | is-referenced-by-count | citationCount, influentialCitationCount | Times Cited |
| **参考文献** | referenced_works | reference | references | 可链接 |
| **资助** | awards | funders | ❌ | GR |
| **相关** | related_works | ❌ | ❌ | Related Articles |
| **全文** | has_fulltext, fulltext_origin | ❌ | openAccessPdf | PMC全文 |

### 4.2 字段覆盖度评估

| 字段类别 | 我们当前模型 | 缺失字段数 | 优先级 |
|---------|------------|-----------|--------|
| 标识符 | 5个 | 7个 | 中 |
| 基本描述 | 4个 | 6个 | 高 |
| 作者 | 5个 | 6个 | 高 |
| 机构 | 0个 | 5个 | 中 |
| 日期 | 2个 | 6个 | 高 |
| 来源 | 4个 | 8个 | 中 |
| OA | 4个 | 3个 | 中 |
| 分类 | 5个 | 4个 | 中 |
| 引用 | 4个 | 6个 | 中 |
| 资助 | 0个 | 4个 | 高 |
| 数据可用性 | 0个 | 5个 | 高 |
| 论文结构 | 0个 | 7个 | 低 |
| 冲突与伦理 | 0个 | 4个 | 低 |
| 评估指标 | 1个 | 4个 | 中 |

---

## 五、最新发展动态（2025-2026）

### 5.1 OpenAlex 2025更新
- **Topic Hierarchy 4.0**: 4级主题层次 (Domain → Field → Subfield → Topic)
- **Awards字段**: 新增资助奖项信息
- **Sustainable Development Goals**: 新增SDG分类
- **fwci**: 场加权引用影响指标成为标准字段
- **API Key要求**: 2025年2月起需要API Key

### 5.2 CrossRef 2025-2026
- Schema版本更新至5.4.0
- 引用链接突破20亿
- 加强资助元数据采集
- 推进开放引用倡议 (I4OC)

### 5.3 Semantic Scholar 2025
- S2ORC数据集持续更新
- SPECTER2嵌入支持
- TLDR摘要成为标准字段
- 推荐系统API增强

### 5.4 Open Science Indicators
- 2025年Frontiers论文提出将**开放数据、开放材料、预注册**作为元数据字段
- 越来越多期刊要求Data Availability Statement
- CRediT贡献者角色成为标准

---

## 六、开源工具与资源汇总

| 工具/平台 | GitHub Stars | 用途 | 链接 |
|-----------|-------------|------|------|
| **OpenAlex API** | N/A | 学术元数据查询 | developers.openalex.org |
| **CrossRef REST API** | N/A | DOI元数据查询 | api.crossref.org |
| **Semantic Scholar API** | N/A | AI增强论文搜索 | api.semanticscholar.org |
| **openalexR** | 200+ | R语言OpenAlex客户端 | github.com/ropensci/openalexR |
| **pyalex** | 300+ | Python OpenAlex客户端 | github.com/J535D165/pyalex |
| **s2python** | 100+ | Python S2客户端 | github.com/allenai/s2-folks |
| **Zotero** | 10K+ | 引用管理 | github.com/zotero |
| **JATS Tag Library** | N/A | XML标准文档 | jats.nlm.nih.gov |

---

## 七、技术难点与解决方案

### 7.1 字段映射问题
**难点**: 不同平台对同一概念使用不同字段名
**解决方案**: 建立字段映射表，使用中间表示层

```python
# 字段映射示例
FIELD_MAPPING = {
    "doi": {"openalex": "doi", "crossref": "DOI", "s2": "externalIds.DOI"},
    "title": {"openalex": "title", "crossref": "title[0]", "s2": "title"},
    "citation_count": {"openalex": "cited_by_count", "crossref": "is-referenced-by-count", "s2": "citationCount"},
}
```

### 7.2 摘要获取问题
**难点**: OpenAlex使用倒排索引存储摘要，不直接提供纯文本
**解决方案**: 实现倒排索引解码函数

```python
def decode_abstract(inverted_index: dict) -> str:
    """将OpenAlex的倒排索引解码为纯文本摘要"""
    if not inverted_index:
        return ""
    positions = []
    for word, pos_list in inverted_index.items():
        for pos in pos_list:
            positions.append((pos, word))
    positions.sort()
    return " ".join(word for _, word in positions)
```

### 7.3 数据一致性问题
**难点**: 不同平台的引用计数、作者名等数据不一致
**解决方案**: 以OpenAlex为主数据源，其他平台补充

### 7.4 缺失字段处理
**难点**: 某些字段在特定来源中不可用
**解决方案**: 使用fallback策略，优先使用权威来源

---

## 八、未来发展趋势

1. **开放引用标准化**: I4OC推动引用数据全面开放
2. **AI增强元数据**: S2的TLDR、SPECTER2等AI生成字段
3. **贡献者角色标准化**: CRediT成为期刊标配
4. **数据可用性强制化**: 越来越多期刊要求Data Availability Statement
5. **开放科学指标**: 预注册、开放数据、开放材料成为标准元数据
6. **主题分类精细化**: OpenAlex 4级主题层次
7. **资助信息结构化**: 资助机构+项目编号成为标准

---

## 九、参考资料

### 官方文档与规范
1. OpenAlex Works API - https://developers.openalex.org/api-reference/works
2. CrossRef REST API - https://api.crossref.org/swagger-ui/index.html
3. Semantic Scholar API - https://api.semanticscholar.org/api-docs
4. JATS Journal Publishing Tag Set - https://jats.nlm.nih.gov/publishing
5. PRISM Basic Metadata - https://www.w3.org/submissions/2020/SUBM-prism-20200910/prism-basic.html
6. DataCite Metadata Schema 4.5 - https://schema.datacite.org/meta/kernel-4.5
7. Dublin Core Metadata Initiative - https://dublincore.org/
8. MARC 21 Bibliographic Format - https://www.loc.gov/marc/bibliographic/
9. Zotero Item Types and Fields - https://www.zotero.org/support/kb/item_types_and_fields
10. RIS File Format - https://library.mskcc.org/blog/2022/09/the-ris-file-format-explained

### 学术论文
11. Priem et al. (2022). OpenAlex: A fully-open index of scholarly works, authors, venues, institutions and concepts. arXiv.
12. Visser et al. (2021). Coverage of highly-cited documents in Google Scholar, Web of Science, and Scopus. Scientometrics.
13. Frontiers (2021). Open Science Indicators as Metadata Fields? Frontiers in Research Metrics and Analytics.
14. COPE (2019). Declaring funding sources for research. Committee on Publication Ethics.
15. JATS-Con papers on metadata extraction - https://jats.nlm.nih.gov/jats-con/

### 技术博客
16. CrossRef Best Practices - https://www.crossref.org/documentation/principles-practices/best-practices/bibliographic
17. Metadata Best Practices for Academic Publishers - https://getdoi.com/metadata-best-practices-academic-publishers
18. NYU Journal Publishing Metadata Guide - https://guides.nyu.edu/journal-publishing/discovery-metadata/basics
19. Writing a Data Availability Statement - https://authorservices.taylorandfrancis.com/data-sharing/share-your-data/data-availability-statements
20. PLOS Data Availability Policy - https://journals.plos.org/plosone/s/data-availability

### 开源项目
21. openalexR - https://github.com/ropensci/openalexR
22. pyalex - https://github.com/J535D165/pyalex
23. Semantic Scholar Python - https://github.com/allenai/s2-folks
24. Zotero - https://github.com/zotero
25. OpenMetadata - https://github.com/open-metadata/Openmetadata

### 中文资源
26. 万方智搜用户说明 - https://library.zuel.edu.cn/
27. 基于内容结构视图的研究数据元数据标准比较研究 - http://www.scal.edu.cn/
