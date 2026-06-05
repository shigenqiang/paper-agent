# 学术论文 PDF 解析后的文本清洗、分块过滤操作 — 调研报告

> 调研日期: 2026-05-30
> 调研主题: 学术论文 PDF 解析后的文本清洗、分块过滤操作
> 搜索次数: 65+ (3 轮搜索: 35 次 API/工具 + 15 次技术博客 + 15 次开源项目深度调研)
> 覆盖类别: 官方文档≥5、学术论文≥10、开源项目≥10、技术博客≥12、社区讨论≥8、中英文≥4
> 报告结构: 11 章，79+ 参考文献

---

## 搜索日志

### 第一轮: API/工具搜索 (35 次)

```
[搜索 1/35] 关键词: Docling document parsing chunking pipeline | 结果来源: GitHub API | 关键发现: IBM Research 开源文档解析框架，支持 HybridChunker、HierarchicalChunker
[搜索 2/35] 关键词: Unstructured.io chunking strategies | 结果来源: GitHub API | 关键发现: ★14808，ETL框架，支持 By Title/By Page/By Similarity 等分块策略
[搜索 3/35] 关键词: MinerU PDF parser academic | 结果来源: GitHub API | 关键发现: ★65626，opendatalab 出品，PDF→Markdown/JSON，支持版面分析
[搜索 4/35] 关键词: Nougat Meta academic PDF OCR | 结果来源: GitHub API | 关键发现: ★9993，Meta 出品，神经网络光学理解，PDF→Markdown
[搜索 5/35] 关键词: GROBID academic paper parsing | 结果来源: GitHub API | 关键发现: 学术论文结构化解析标准工具，识别标题/摘要/正文/参考文献
[搜索 6/35] 关键词: RAPTOR recursive tree retrieval | 结果来源: GitHub API | 关键发现: ★1680，递归抽象处理树状检索，层次化分块
[搜索 7/35] 关键词: text chunking RAG best practices | 结果来源: Web Search | 关键发现: 固定/递归/语义/结构感知四种分块策略
[搜索 8/35] 关键词: academic paper text cleaning post-processing | 结果来源: Web Search | 关键发现: 去噪→去重→格式统一→特殊字符处理 四步流程
[搜索 9/35] 关键词: MinHash SimHash deduplication document | 结果来源: GitHub API | 关键发现: datasketch ★2900，MinHash/LSH 近似去重
[搜索 10/35] 关键词: RapidFuzz string matching dedup | 结果来源: GitHub API | 关键发现: ★3900，快速模糊字符串匹配
[搜索 11/35] 关键词: langdetect language detection Python | 结果来源: GitHub API | 关键发现: ★1888，Google 语言检测库 Python 移植
[搜索 12/35] 关键词: lingua-py language detection | 结果来源: GitHub API | 关键发现: ★1727，最准确的语言检测库，适合短文本
[搜索 13/35] 关键词: jusText boilerplate removal | 结果来源: GitHub API | 关键发现: ★818，基于启发式的网页样板文本去除
[搜索 14/35] 关键词: trafilatura web scraping text extraction | 结果来源: GitHub API | 关键发现: ★6000，网页正文提取+样板去除
[搜索 15/35] 关键词: spaCy NLP text processing pipeline | 结果来源: GitHub API | 关键发现: ★33600，工业级 NLP 管道
[搜索 16/35] 关键词: NLTK text processing academic | 结果来源: GitHub API | 关键发现: ★14600，经典 NLP 工具包
[搜索 17/35] 关键词: pypdf pdfplumber PyMuPDF comparison | 结果来源: Web Search | 关键发现: pypdf ★10K, pdfplumber ★10K, PyMuPDF ★9.8K
[搜索 18/35] 关键词: semantic chunking embedding-based splitting | 结果来源: GitHub API | 关键发现: LangChain SemanticChunker, LlamaIndex SentenceWindowNodeParser
[搜索 19/35] 关键词: late chunking Jina AI 2024 | 结果来源: Web Search | 关键发现: ★516，先 embedding 再分块，保留跨段语义
[搜索 20/35] 关键词: dolma data curation LLM training | 结果来源: GitHub API | 关键发现: ★1500，AI2 数据整理框架
[搜索 21/35] 关键词: NeMo Curator NVIDIA text pipeline | 结果来源: Web Search | 关键发现: NVIDIA 出品，大规模文本数据清洗管道
[搜索 22/35] 关键词: FineWeb HuggingFace data curation | 结果来源: Web Search | 关键发现: HuggingFace 15T token 数据集，质量过滤标杆
[搜索 23/35] 关键词: RedPajama data pipeline dedup filter | 结果来源: Web Search | 关键发现: Together AI 开源 LLM 数据管道
[搜索 24/35] 关键词: Layout-Parser document layout analysis | 结果来源: GitHub API | 关键发现: ★5700，文档版面分析框架
[搜索 25/35] 关键词: chonkie chunking library RAG | 结果来源: GitHub API | 关键发现: ★409+，轻量级 RAG 分块库
[搜索 26/35] 关键词: 学术论文PDF解析 文本清洗 分块过滤 | 结果来源: Web Search | 关键发现: 中文技术社区对 GROBID/MinerU/Marker 的实践总结
[搜索 27/35] 关键词: academic paper chunking filtering RAG pipeline | 结果来源: Web Search | 关键发现: 学术论文特殊处理：公式/图表/引用/多栏
[搜索 28/35] 关键词: document quality scoring perplexity filtering | 结果来源: Web Search | 关键发现: FineWeb 用 fastText 分类器做质量评分
[搜索 29/35] 关键词: anystyle citation reference parsing | 结果来源: GitHub API | 关键发现: ★1200，参考文献解析工具
[搜索 30/35] 关键词: dedupe record linkage deduplication | 结果来源: GitHub API | 关键发现: ★4500，记录链接和去重库
[搜索 31/35] 关键词: text normalization unicode academic papers | 结果来源: Web Search | 关键发现: Unicode NFKC 规范化、连字修复、编码修复
[搜索 32/35] 关键词: RAG chunking overlap strategies 2025 | 结果来源: Web Search | 关键发现: 10-20% overlap 是主流实践
[搜索 33/35] 关键词: Marker PDF to markdown conversion | 结果来源: GitHub API | 关键发现: VikParuchuri 出品，深度学习 PDF→Markdown
[搜索 34/35] 关键词: science-parse academic paper parsing | 结果来源: GitHub API | 关键发现: ★700，Allen AI 学术论文解析
[搜索 35/35] 关键词: Lost in the Middle long context LLM | 结果来源: Web Search | 关键发现: Liu et al. 2023，LLM 位置偏差研究
```

### 第二轮: 技术博客与实践指南搜索 (15 次)

```
[搜索 36/50] 关键词: RAG chunking best practices 2025 2026 practical recommendations | 结果来源: Firecrawl Blog, AI Agents Buzz | 关键发现: RecursiveCharacterTextSplitter 400-512 token 是默认推荐；Chroma 上下文退化研究发现 2500 token 处存在"上下文悬崖"
[搜索 37/50] 关键词: text cleaning pipeline RAG 2025 blog tutorial | 结果来源: Weaviate Blog, KDnuggets, Nimbleway | 关键发现: PDF 先转 Markdown 再分块是最可靠方法；clean_text() 用正则去多余空白和非 ASCII 字符
[搜索 38/50] 关键词: academic paper PDF parsing pipeline 2025 | 结果来源: Firecrawl, Medium, Applied AI | 关键发现: 学术论文解析准确率仅 40-60%；领域决定一切，法律合同 95% vs 论文 40-60%
[搜索 39/50] 关键词: chunk size optimization RAG empirical 2025 | 结果来源: Ailog, arXiv, GPT-trainer, LinkedIn | 关键发现: 512-1024 token 平衡上下文与精度；NVIDIA 测试不同数据集最优大小差异大；embedding 维度应与 chunk 大小对齐
[搜索 40/50] 关键词: text deduplication techniques RAG practical 2025 | 结果来源: Brenndoerfer, NAACL, arXiv, Daft | 关键发现: MinHash+LSH 是 GPT-3/Llama3 等模型的标准去重方案；100K 网页 MinHash 去重 <4 分钟
[搜索 41/50] 关键词: PDF text extraction post-processing cleaning 2025 | 结果来源: V7 Labs, Datalogics, NVIDIA Blog, Artifex | 关键发现: 水印干扰 OCR 识别；PyMuPDF 混合策略（原生+OCR）效果最佳
[搜索 42/50] 关键词: semantic chunking vs fixed chunking RAG 2025 benchmark | 结果来源: Firecrawl, NAACL 2025, PMC, BuildMVPFast | 关键发现: NAACL 2025 论文结论: 固定 200 词分块匹配或超越语义分块；语义分块慢 14 倍；临床研究显示自适应分块 87% vs 固定 13%
[搜索 43/50] 关键词: document quality filtering RAG 2025 scoring methods | 结果来源: ACL 2025, Medium, RAGFlow | 关键发现: MAIN-RAG 自适应过滤提升 2-11% 准确率；Reranking 提升检索质量 +48%
[搜索 44/50] 关键词: RAG overlap strategies 2025 optimal overlap percentage | 结果来源: Ailog, Firecrawl, DEV.to, Puppyone | 关键发现: 10-20% overlap 是主流；2026 分析发现 SPLADE 检索下 overlap 无显著收益；Microsoft 推荐 25%，NVIDIA 用 15%
[搜索 45/50] 关键词: PDF parsing challenges academic papers 2025 formulas tables multi-column | 结果来源: OneUptime, TurboLens, Diva Portal, arXiv | 关键发现: 多栏布局是 OCR 噩梦；公式识别需专用模型；表格解析准确率是关键瓶颈
[搜索 46/50] 关键词: header footer detection PDF extraction boilerplate removal 2025 | 结果来源: UiPath Forum, Stack Overflow, Docling GitHub | 关键发现: Docling 有未解决的 header/footer issue (#1272)；pdfplumber 字体大小分析可区分脚注
[搜索 47/50] 关键词: chunk cleaning filtering RAG pipeline 2025 2026 end-to-end | 结果来源: Digital Applied, Kapa.ai, DecodeTheFuture, Firecrawl | 关键发现: 错误分块策略导致 9% recall 差距；PII 脱敏必须在分块前完成
[搜索 48/50] 关键词: academic paper reference citation removal text cleaning RAG | 结果来源: Substack (RAG Playbook), Brenndoerfer | 关键发现: 脚注/参考文献默认移除；pdfplumber 字体分析区分正文与脚注；页眉页脚污染 embedding 案例
[搜索 49/50] 关键词: chunk quality scoring filtering low quality chunks RAG | 结果来源: arXiv, Ailog, RAGFlow, ChunkRAG | 关键发现: ChunkRAG 用 TF-IDF+余弦相似度过滤，>0.9 冗余度剔除；parent-child 架构 +10-13 点提升
[搜索 50/50] 关键词: NVIDIA PDF extraction RAG 2025 page-level chunking benchmark | 结果来源: Firecrawl, LinkedIn, arXiv, ACL | 关键发现: NVIDIA 基准: page-level 分块 0.648 准确率；SPLADE+pdfplumber 是金融 PDF 最佳组合
```

### 第三轮: 开源项目深度调研 (15 次, Tavily Advanced Search)

```
[搜索 51/65] 关键词: datasketch MinHash LSH deduplication 2025 implementation Python GitHub | 结果来源: GitHub, Milvus Blog, arXiv | 关键发现: GPU 模式新增 (CuPy/CUDA)；LSHBloom 新索引类型；异步批量插入支持
[搜索 52/65] 关键词: RapidFuzz text deduplication 2025 fuzzy matching | 结果来源: GitHub, LinkedIn, Medium, Let's Data Science | 关键发现: v3.14.x (2026年3月)；比 FuzzyWuzzy 快 10-100x；cdist 矩阵计算
[搜索 53/65] 关键词: Dolma AI2 data curation 2025 text filtering perplexity OLMo | 结果来源: GitHub, AI2 Blog, Substack, arXiv | 关键发现: Dolma 3 新增万亿级去重；Gopher+C4 规则组合；fastText 质量分类器
[搜索 54/65] 关键词: NeMo Curator NVIDIA text cleaning deduplication 2025 | 结果来源: NVIDIA Docs, GitHub, Spheron Blog | 关键发现: 16x 快速模糊去重；30+ 启发式过滤器；GPU 加速 MinHash
[搜索 55/65] 关键词: RedPajama v2 data pipeline quality filtering Together AI | 结果来源: HuggingFace, OpenReview, Together AI Blog, GitHub | 关键发现: 30T+ token；质量信号元数据；Bloom filter + MinHash 去重
[搜索 56/65] 关键词: Chonkie RAG chunking library 2025 2026 lightweight Python | 结果来源: GitHub, Deeplearning.fr, DEV.to, docs.chonkie.ai | 关键发现: 9 种分块器；33x 速度优势；Pipeline 端到端模式
[搜索 57/65] 关键词: spaCy NER text cleaning pipeline 2025 | 结果来源: spaCy Docs, GeeksforGeeks, NewsCatcher, CodeSignal | 关键发现: 75+ 语言；EntityRuler 自定义规则；NER 用于 PII 检测和术语提取
[搜索 58/65] 关键词: trafilatura boilerplate removal text extraction 2025 Python | 结果来源: Contextractor, GitHub, trafilatura.readthedocs.io | 关键发现: v2.0.0 (2024年12月)；5,400+ stars；HuggingFace/IBM/Stanford 生产使用
[搜索 59/65] 关键词: FineWeb HuggingFace quality filtering 2025 fastText classifier | 结果来源: HuggingFace, GitHub, arXiv, EmergentMind | 关键发现: 15T token；8 步管道；FineWeb-Edu fastText 分类器；5-7% 通过率
[搜索 60/65] 关键词: Semantic Scholar S2ORC paper parsing 2025 academic PDF processing | 结果来源: ACL Anthology, arXiv, IntuitionLabs, Scribd | 关键发现: 81.1M 论文；ScienceParse + GROBID；380.5M 引用链接
[搜索 61/65] 关键词: datasketch GitHub stars MinHashLSH num_perm threshold parameters | 结果来源: GitHub, ekzhu.com docs | 关键发现: 参数调优网格搜索；Redis/Cassandra 后端；异步 API
[搜索 62/65] 关键词: Dolma toolkit GitHub stars text filters gopher rules quality heuristics | 结果来源: ACL 2024, AI2 Blog, Substack, ICLR 2025 | 关键发现: Gopher All + C4 NoPunc 最佳组合；代码过滤用 RedPajama+StarCoder 规则
[搜索 63/65] 关键词: NeMo Curator GitHub stars text cleaning heuristics quality filtering GPU | 结果来源: NVIDIA Docs, GitHub, Spheron Blog, Hermes Agent | 关键发现: Nemotron-CC 端到端管道；顺序 vs 流水线 13x 加速
[搜索 64/65] 关键词: FineWeb datatrove pipeline text deduplication MinHash filtering steps | 结果来源: DatologyAI, Spheron, NeurIPS 2024, arXiv | 关键发现: 5-gram + 112 hash functions；跨 dump 去重无效；Ultra-FineWeb 改进
[搜索 65/65] 关键词: Chonkie chunking GitHub stars semantic chunker recursive token sentence | 结果来源: GitHub, LinkedIn, docs.chonkie.ai | 关键发现: NeuralChunker (BERT)；SlumberChunker (LLM)；JS 版本 @chonkiejs/core
```

---

## 1. 核心概念与定义

### 1.1 文本清洗 (Text Cleaning / Post-processing)

PDF 解析后的文本清洗是指对从 PDF 中提取的原始文本进行**系统性修复和去噪**的过程。PDF 格式本身不存储文本流，而是通过字符定位指令渲染页面，因此提取的文本不可避免地包含各类噪声。

**核心问题来源**：
- **CID 伪影**：pdfplumber 等工具遇到未映射字符时输出 `(cid:48)` 格式
- **连字 (Ligatures)**：`fi`, `fl`, `ff` 等在字体中编码为单字形，提取后丢失或乱码
- **断词 (Hyphenation)**：`computa-\ntion` 跨行断词需拼接
- **词间距丢失**：`Alzheimer'sdisease` 缺少空格
- **页眉页脚**：重复出现的标题、页码、版权信息
- **引用标记错位**：`word [1]` 与正文粘连

### 1.2 分块 (Chunking)

将长文档切分为适合向量化和检索的文本片段。学术论文的分块需考虑：

- **结构感知**：按 Section (Abstract/Introduction/Methods/Results/Discussion) 切分
- **语义完整**：不在句子中间切断
- **长度控制**：典型 200-1000 token，兼顾上下文窗口和检索精度
- **重叠 (Overlap)**：相邻 chunk 共享 50-100 token 防止语义断裂

### 1.3 过滤 (Filtering)

对分块后的文本片段进行质量筛选，移除低信息量或噪声内容：

- **公式行过滤**：数学符号占比 >20% 的行
- **坐标轴标签块**：连续 5+ 行短数字/单字符
- **参考文献列表**：纯引用内容（除非专门分析引用）
- **目录页**：章节索引页
- **过短片段**：<50 字符的 chunk
- **重复内容**：跨页重复的页眉/水印

---

## 2. 技术原理深度解析

### 2.1 PDF 文本提取的固有问题

PDF 文件不存储"段落"或"文本流"概念。每页包含一系列字符绘制指令 `(x, y, font, size, char)`。文本提取工具通过以下策略重建文本：

1. **字符聚类**：按 y 坐标聚类为"行"，按 x 坐标排序为"阅读顺序"
2. **词间距推断**：当两个字符间距 > 阈值时插入空格
3. **字体分析**：通过字体信息判断粗体/斜体/上标/下标
4. **版面分析**：检测多栏布局、表格区域、图片区域

**固有噪声来源**：

| 噪声类型 | 原因 | 典型表现 |
|---------|------|---------|
| CID 伪影 | 字体未嵌入 Unicode 映射 | `(cid:48)` `(cid:70)` |
| 连字丢失 | 字体使用 OpenType ligature | `fi` → `ﬁ` → 乱码 |
| 断词残留 | PDF 按行渲染，软连字符被保留 | `computa-\ntion` |
| 词间距错误 | 字体 metrics 不准确 | `word1word2` 合并 |
| 版面顺序错乱 | 多栏文本被错误拼接 | 左栏右栏交替 |

### 2.2 分块策略的技术原理

#### 2.2.1 固定长度分块 (Fixed-size Chunking)

```
[text....................overlap....................]
                        [text....................overlap....................]
```

- 按 token 数切分，典型 500-1000 token
- 优点：实现简单，chunk 大小均匀
- 缺点：可能在句子/段落中间切断

#### 2.2.2 递归分块 (Recursive Splitting)

LangChain 的 `RecursiveCharacterTextSplitter` 采用递归策略：
1. 先尝试按 `\n\n` (段落) 切分
2. 如果 chunk 仍过大，按 `\n` (行) 切分
3. 如果仍过大，按 `. ` (句子) 切分
4. 最后按空格切分

#### 2.2.3 语义分块 (Semantic Chunking)

基于 embedding 的分块：
1. 将文档按句子切分
2. 计算相邻句子的 embedding 余弦相似度
3. 在相似度骤降处（主题转换点）切分
4. 合并相邻相似句子为 chunk

#### 2.2.4 结构感知分块 (Structure-aware Chunking)

学术论文专用：
1. 识别 Section 标题 (Abstract, Introduction, Methods, ...)
2. 在 Section 边界切分
3. Section 内按段落/长度二次切分
4. 保留 Section 元数据到 chunk

#### 2.2.5 层次化分块 (Hierarchical Chunking)

RAPTOR 的递归抽象策略：
1. 叶子节点：原始文本 chunk
2. 第一层：对叶子节点做摘要，合并为父节点
3. 递归：对父节点继续摘要，形成树结构
4. 检索时可在不同抽象层级搜索

#### 2.2.6 Late Chunking (Jina AI, 2024)

颠覆传统流程：
1. 将整篇文档（或长段落）输入 embedding 模型
2. 获得 token-level 的上下文感知 embedding
3. 在 embedding 空间中按位置切分
4. 每个 chunk 的 embedding 已包含全局上下文

### 2.3 过滤策略的技术原理

#### 2.3.1 启发式规则过滤

基于文本特征的规则：
- **公式行检测**：数学符号（∑, ∫, α, β, ∈, ∉, ≤, ≥）占比 > 20%
- **坐标轴标签**：连续 5+ 行，每行 ≤ 5 字符，多为数字
- **参考文献检测**：以 `[数字]` 或 `(Author, Year)` 开头的连续行
- **目录检测**：包含 `...` 或 `........` 的行

#### 2.3.2 统计质量过滤

- **困惑度 (Perplexity)**：用语言模型计算文本困惑度，过高表示噪声
- **信息密度**：停用词占比、实体密度、词汇多样性
- **长度分布**：过短（<50字符）或过长（>5000字符）的 chunk

#### 2.3.3 去重 (Deduplication)

- **精确去重**：SHA256 哈希完全匹配
- **近似去重 (MinHash/LSH)**：将文本转为 n-gram 集合，用 MinHash 签名 + LSH 桶分组，O(1) 时间判断近似重复
- **SimHash**：将文本映射为固定长度二进制指纹，汉明距离 < 阈值判为重复

---

## 3. 主流技术方案对比

### 3.1 文本提取工具对比

| 工具 | GitHub Stars | 语言 | 特点 | 学术论文适配 | 输出格式 |
|------|-------------|------|------|-------------|---------|
| **MinerU** | ★65,626 | Python | 版面分析+表格+公式 | ★★★★★ | Markdown/JSON |
| **GROBID** | ★3,500+ | Java | 学术论文专用结构化 | ★★★★★ | TEI-XML |
| **Nougat (Meta)** | ★9,993 | Python | 神经网络 OCR | ★★★★☆ | Markdown |
| **Unstructured** | ★14,808 | Python | ETL 全流程 | ★★★★☆ | JSON/Markdown |
| **Docling (IBM)** | ★15,000+ | Python | 模块化管道 | ★★★★☆ | JSON/Markdown |
| **Marker** | ★20,000+ | Python | 深度学习 PDF→MD | ★★★★☆ | Markdown |
| **PyMuPDF** | ★9,800 | Python | 速度快，C 底层 | ★★★☆☆ | Text/HTML |
| **pdfplumber** | ★10,000 | Python | 表格提取强 | ★★★☆☆ | Text/DataFrame |
| **pypdf** | ★10,000 | Python | 纯 Python，轻量 | ★★☆☆☆ | Text |

### 3.2 分块策略对比 (含 2025-2026 基准数据)

| 策略 | 优点 | 缺点 | 适用场景 | 代表实现 | 基准数据 |
|------|------|------|---------|---------|---------|
| **固定长度** | 简单、大小均匀 | 可能切断语义 | 通用文档 | LangChain `CharacterTextSplitter` | NAACL 2025: 200 词匹配语义分块 |
| **递归分割** | 尊重文本结构 | 依赖分隔符选择 | 通用文档 (默认推荐) | LangChain `RecursiveCharacterTextSplitter` | Vecta 2026: 512-token 第一 (69%) |
| **语义分块** | 主题边界准确 | 计算成本高 (14x 慢) | 长文档检索 | LangChain `SemanticChunker` | Vecta 2026: 54%，碎片平均 43 token |
| **结构感知** | 尊重文档结构 | 需要结构解析 | 学术论文 | Docling `HybridChunker` | 临床研究: 87% vs 固定 13% |
| **层次化** | 多粒度检索 | 实现复杂 | 深度分析 | RAPTOR | 递归+parent-child: +10-13 点 |
| **Late Chunking** | 全局上下文 | 需要长上下文模型 | 高精度检索 | Jina AI | +6.5 nDCG 点 |
| **页面级** | 尊重物理结构 | 页面大小不一致 | 金融/报告 PDF | Unstructured `chunk_by_title` | NVIDIA: 0.648 准确率 |

### 3.3 过滤技术对比

| 技术 | 原理 | 优点 | 缺点 | 代表工具 |
|------|------|------|------|---------|
| **启发式规则** | 正则/特征比对 | 快速、无依赖 | 规则需手工维护 | 自研 |
| **困惑度过滤** | LM 评分 | 自动化 | 需要 LM | Dolma |
| **MinHash 去重** | LSH 近似匹配 | O(1) 判断 | 有误判率 | datasketch |
| **SimHash** | 二进制指纹 | 内存效率高 | 短文本不准 | 自研 |
| **分类器过滤** | 训练质量分类器 | 准确率高 | 需标注数据 | FineWeb |
| **长度/格式过滤** | 阈值判断 | 简单快速 | 粗糙 | 通用 |

---

## 4. 最新发展动态 (2025-2026)

### 4.1 视觉语言模型 (VLM) 直接解析 PDF

2025 年最大趋势：不再依赖传统文本提取管道，而是用 VLM 直接"看"PDF 页面：
- **Nougat (Meta)**：基于 Donut 架构，端到端 PDF→Markdown
- **Marker**：结合布局检测 + OCR + 后处理
- **MinerU**：版面分析 + 多引擎融合

### 4.2 LLM 辅助结构化提取

用 LLM 将非结构化文本转为结构化 JSON：
- 提取 title, abstract, methods, results, discussion 等结构
- 识别图表标题、公式、参考文献
- 2025 年多篇论文验证了 GPT-4o/Claude 在此任务上的有效性

### 4.3 Late Chunking (Jina AI, 2024-2025)

颠覆传统"先分块再 embedding"的流程：
- 先对整篇文档做 token-level embedding
- 再在 embedding 空间中分块
- 每个 chunk 的 embedding 包含全局上下文
- 解决了传统分块丢失跨段语义的问题

### 4.4 数据质量过滤的工业化

2025 年 LLM 训练数据管道的成熟：
- **FineWeb (HuggingFace)**：15T token，用 fastText 分类器做质量过滤
- **Dolma (AI2)**：开源数据整理框架，支持 MinHash 去重 + 质量过滤
- **NeMo Curator (NVIDIA)**：企业级文本数据清洗管道
- **RedPajama v2 (Together AI)**：开源 LLM 数据管道

### 4.5 学术论文专用解析的进展

- **GROBID**：持续维护，2025 年改进了表格和公式识别
- **Science Parse v2 (Allen AI)**：基于 SciBERT 的论文结构化解析
- **PaperMage**：Allen AI 出品，论文多模态分析

### 4.6 2025-2026 技术博客与实践指南关键发现

> 以下内容来自第二轮 Web 搜索，覆盖 Firecrawl、Weaviate、NVIDIA、NAACL 2025、PMC 等技术博客和学术论文。

#### 4.6.1 Chunk Size: 实证数据

| 来源 | 推荐 Chunk Size | 备注 |
|------|----------------|------|
| Firecrawl (2026) | 400-512 token | "90% 用例的默认选择" |
| Digital Applied (2026) | 512-1024 token | "覆盖大多数工作负载" |
| NVIDIA 基准 (2025) | 因数据集而异 | KG-RAG: 1024, SQuAD: 64, Earnings: 512 |
| GPT-trainer | 200-500 token | "常见落点，15% overlap" |
| Ailog (2025) | 512 token + 50 overlap | "提升检索 25%+" |
| LinkedIn (Naman Goyal) | 与 embedding 维度对齐 | dim<512: 200-300, dim~768-1024: 300-700, dim>1536: 700-1200 |

**关键洞察**:
- **没有万能大小** -- 最佳 chunk size 取决于数据集和查询类型
- **NVIDIA 基准显示**: 不同数据集最优大小差异巨大 (64 vs 1024 token)
- **Embedding 维度对齐**: chunk 大小应与 embedding 维度匹配，这比切换 LLM 更有效
- **查询类型决定大小**: 事实查询 256-512 token; 分析查询 1024+ token

#### 4.6.2 Overlap: 争议性发现

| 来源 | 推荐 Overlap | 关键发现 |
|------|-------------|---------|
| 行业默认 (2026) | 10-20% | 多数指南推荐 |
| Microsoft Azure | 25% | 较保守 |
| NVIDIA 基准 | 15% (128/512) | 实测选择 |
| **2026 系统分析** | **0%** | SPLADE 检索下 overlap 无显著收益，仅增加索引成本 |
| Firecrawl (2026) | "测试决定" | Dense 向量检索比稀疏检索更受益于 overlap |

**关键洞察**:
- **Overlap 不是万能的**: 2026 年系统分析发现 SPLADE 检索下 overlap 无显著收益
- **Dense vs Sparse**: Dense 向量检索更受益于 overlap，稀疏检索受益较少
- **如果有 reranker**: overlap 重要性降低，reranker 在查询时重新读取上下文
- **Parent-child 架构**: parent chunk 已包含完整上下文，overlap 更不重要

#### 4.6.3 Semantic vs Fixed Chunking: 学术级对比

| 来源 | 结论 | 数据 |
|------|------|------|
| **NAACL 2025 Findings 论文** | 固定 200 词分块匹配或超越语义分块 | "计算成本不被一致收益所证明" |
| Vecta 基准 (2026.02) | 递归 512-token 第一 (69%) | 语义分块仅 54%，碎片平均 43 token |
| PMC 临床研究 (2025.11) | 自适应分块远超固定 (87% vs 13%) | p=0.001，统计显著 |
| Chonkie 基准 | 语义分块慢 14x | 0.33 MB/s vs 4.82 MB/s |
| Chroma 上下文退化 (2025.07) | 上下文越长性能越差 | 测试 18 个模型 |
| 2026 系统分析 | 句子分块匹配语义分块 | 上下文 <5000 token 时 |

**关键洞察**:
- **语义分块不是银弹**: NAACL 2025 论文明确指出固定分块在非合成数据集上表现更好
- **速度差异巨大**: 语义分块比 token 分块慢 14 倍
- **阈值敏感**: 0.7 余弦相似度阈值是任意的，换 embedding 模型需重新调参
- **结构化文档例外**: 当文档有强内在结构时（如临床文档），结构感知分块显著优于固定分块
- **递归分块是最佳起点**: Vecta 基准在学术论文上将递归 512-token 列为第一

#### 4.6.4 PDF 解析: 学术论文的困境

| 来源 | 关键发现 |
|------|---------|
| Applied AI 基准 (2025) | 学术论文解析准确率仅 40-60%，法律合同 95% |
| Firecrawl (2026) | "布局错误级联: 微小布局检测误差导致后续 OCR 和元素解析严重失败" |
| NVIDIA Blog (2025.07) | PDF 是 RAG 系统中最常见的输入格式，但解析仍是主要挑战 |
| OmniDocBench (CVPR 2025) | Pipeline 工具在学术论文上表现尚可，VLM 在幻灯片和手写笔记上泛化更好 |
| arXiv 表格基准 (2026) | 表格解析是非结构化到结构化转换中最困难的部分 |
| Infinity-Parser (2025) | 多专家策略: 布局模型+公式识别模型+表格解析器分工处理 |

**关键洞察**:
- **领域决定一切**: 同一个解析器在不同文档类型上准确率差异 55+ 个百分点
- **错误级联**: 布局检测的小误差会在后续步骤中放大
- **学术论文特别困难**: 多栏、公式、表格、脚注混合，是 PDF 解析的"硬骨头"
- **混合方法胜出**: PyMuPDF 的"智能策略" -- 检测是否需要 OCR，原生提取 + OCR 结合

#### 4.6.5 页眉页脚与样板内容移除

| 来源 | 方法 | 关键发现 |
|------|------|---------|
| Docling GitHub Issue #1272 | 请求功能 | Docling 目前将页眉页脚误识别为章节标题 |
| RAG Playbook (Substack) | 正则 + 字体分析 | "默认移除脚注和参考文献"；pdfplumber 字体分析区分正文与脚注 |
| UiPath Forum (2025) | 正则替换 | 静态内容用正则，动态内容无可靠方案 |
| Stack Overflow | pdfminer 布局分析 | 按文本块位置和大小分类 |
| RefinedDoc | 自动检测 | `rd.headers`, `rd.footers`, `rd.body` 自动分离 |

**实践建议**:
- **静态页眉页脚**: 正则匹配已知字符串，替换为空
- **动态页眉页脚**: 统计跨页面重复率 >80% 的短行
- **脚注检测**: pdfplumber 字体大小分析 -- 脚注通常比正文字体小
- **Running heads**: `^Page \d+ of \d+` 等模式移除
- **本项目方案**: `remove_headers_footers` 检测 >80% 页面重复的短行，效果良好

#### 4.6.6 Chunk 质量过滤: 最新方法

| 来源 | 方法 | 效果 |
|------|------|------|
| ChunkRAG (arXiv 2025) | TF-IDF + 余弦相似度过滤 | 冗余度 >0.9 剔除，动态阈值 |
| MAIN-RAG (ACL 2025) | 多 Agent 自适应过滤 | 4 个 QA 基准提升 2-11% |
| Pinecone/Superlinked | Reranking | 添加 reranking 提升检索质量 +48% |
| Dev.to (2026) | Parent-child 架构 | 递归单独 69% → 递归+parent-child ~78-82%，+10-13 点 |
| ZeroEntropy (2025-2026) | Reranking 50→top-5 | 最佳质量/速度平衡 |

**实践建议**:
- **冗余度过滤**: 相似度 >0.9 的 chunk 对剔除
- **动态阈值**: 基于分数分布自适应调整过滤阈值
- **Reranking 是免费升级**: 添加 cross-encoder reranker 提升 +48%，无架构变更
- **Parent-child 架构**: parent = 4-5x child 大小，+10-13 点提升，2x 存储成本

#### 4.6.7 学术论文文本清洗: 实践 Gotchas

来自 "The RAG Playbook: Advanced Parsing for PDFs That Hate You" (Substack):

1. **脚注污染**: "每个提取的文本 chunk 末尾都包含 'Confidential Draft – [Page X]'，严重污染 embedding"
2. **参考文献泄漏**: "AI 开始输出文档脚注部分的参考文献引用，显然不是用户需要的答案"
3. **字体检测技巧**: "用 pdfplumber 的字符分析，按字体大小分类为'正文 vs 可能的脚注'，只保留正文用于 embedding"
4. **默认移除策略**: "在大多数 QA 场景中，脚注和参考文献不需要 -- 所以我默认移除它们以避免混淆"
5. **Running heads**: "移除 'Page X of Y' 和已知页眉字符串"

---

## 5. 开源工具与资源汇总

### 5.1 PDF 解析工具

| 工具 | GitHub | Stars | 用途 |
|------|--------|-------|------|
| MinerU | github.com/opendatalab/MinerU | ★65,626 | PDF→Markdown/JSON，版面分析 |
| Nougat | github.com/facebookresearch/nougat | ★9,993 | 神经网络 PDF→Markdown |
| Unstructured | github.com/Unstructured-IO/unstructured | ★14,808 | 文档 ETL 全流程 |
| GROBID | github.com/kermitt2/grobid | ★3,500+ | 学术论文结构化解析 |
| Layout-Parser | github.com/Layout-Parser/layout-parser | ★5,700 | 文档版面分析 |
| science-parse | github.com/allenai/science-parse | ★700 | 学术论文解析 |

### 5.2 文本提取库

| 库 | GitHub | Stars | 特点 |
|---|--------|-------|------|
| pypdf | github.com/py-pdf/pypdf | ★10,000 | 纯 Python PDF 读写 |
| pdfplumber | github.com/jsvine/pdfplumber | ★10,000 | PDF 文本+表格提取 |
| PyMuPDF | github.com/pymupdf/PyMuPDF | ★9,800 | C 底层，速度快 |

### 5.3 分块工具

| 工具 | GitHub | Stars | 特点 |
|---|--------|-------|------|
| RAPTOR | github.com/parthsarthi03/raptor | ★1,680 | 递归抽象树状检索 |
| Chonkie | github.com/chonkie-inc/chonkie | ★409 | 轻量级 RAG 分块 |
| LangChain TextSplitters | 内置模块 | - | 递归/语义/字符分块 |
| LlamaIndex NodeParser | 内置模块 | - | 句子窗口/层次分块 |

### 5.4 去重与质量过滤

| 工具 | GitHub | Stars | 用途 |
|---|--------|-------|------|
| datasketch | github.com/ekzhu/datasketch | ★2,900 | MinHash/LSH 近似去重 |
| RapidFuzz | github.com/maxbachmann/RapidFuzz | ★3,900 | 快速模糊字符串匹配 |
| dedupe | github.com/dedupeio/dedupe | ★4,500 | 记录链接和去重 |
| Dolma | github.com/allenai/dolma | ★1,500 | AI2 数据整理工具包 |

### 5.5 NLP 与语言检测

| 工具 | GitHub | Stars | 用途 |
|---|--------|-------|------|
| spaCy | github.com/explosion/spaCy | ★33,600 | 工业级 NLP 管道 |
| NLTK | github.com/nltk/nltk | ★14,600 | 经典 NLP 工具包 |
| langdetect | github.com/Mimino666/langdetect | ★1,888 | 语言检测 |
| lingua-py | github.com/pemistahl/lingua-py | ★1,727 | 高精度语言检测 |

### 5.6 样板文本去除

| 工具 | GitHub | Stars | 用途 |
|---|--------|-------|------|
| trafilatura | github.com/adbar/trafilatura | ★6,000 | 网页正文提取 |
| jusText | github.com/miso-belica/jusText | ★818 | 启发式样板去除 |

---

## 6. 实际应用案例

### 6.1 案例一：FineWeb 数据集构建 (HuggingFace, 2024-2025)

**背景**：HuggingFace 构建 15T token 的高质量训练数据集。

**清洗管道**：
1. URL 过滤：移除成人/垃圾站点
2. 文本提取：trafilatura 提取正文
3. 语言检测：fastText lid.176 模型
4. 质量过滤：训练 fastText 分类器，用 Wikipedia 为正例，随机网页为负例
5. 去重：MinHash + LSH，跨文档去重
6. 个人信息过滤：正则匹配邮箱/电话/身份证号

**关键发现**：
- 质量过滤移除了 ~60% 的数据
- 去重移除了 ~15% 的数据
- 最终数据质量显著优于未过滤版本

### 6.2 案例二：Dolma 数据管道 (AI2, 2024-2025)

**背景**：AI2 为 OLMo 模型构建开源数据管道。

**管道步骤**：
1. 文档级过滤：语言、长度、重复率
2. 段落级过滤：困惑度过滤（用 KenLM）
3. 行级过滤：移除样板行（版权声明、Cookie 提示等）
4. 去重：CCNet 风格的 MinHash 去重
5. 内容过滤：移除有害/低质量内容

**技术亮点**：
- 完全开源，可复现
- 支持流式处理，内存效率高
- 提供数据质量报告

### 6.3 案例三：RAG 学术论文问答系统

**背景**：构建基于 RAG 的学术论文问答系统。

**典型管道**：
```
PDF → GROBID/MinerU 解析
  → TextPostProcessor 清洗（CID/连字/断词/页眉页脚）
  → 结构感知分块（按 Section 切分，500-900 token）
  → ChunkCleaner 过滤（公式行/坐标轴/过短 chunk）
  → MinHash 去重（跨论文去重）
  → Embedding → ChromaDB/Qdrant
  → 检索 → LLM 生成答案
```

**关键指标**：
- 分块大小：500-900 token（兼顾上下文和精度）
- 重叠：80-100 token（防止语义断裂）
- 过滤率：约 10-20% 的 chunk 被过滤
- 去重率：约 5% 的 chunk 被去重

### 6.4 案例四：NVIDIA PDF 解析基准 (2025)

**背景**：NVIDIA 测试不同 PDF 解析器和分块策略在金融文档 RAG 中的表现。

**关键发现**：
- **SPLADE + pdfplumber** 是金融 PDF 的最佳组合
- **页面级分块** 在金融报告中达到 0.648 准确率
- **不同 chunk size 在不同数据集上表现差异巨大**:

| 数据集 | 最优 Chunk Size | 分数 |
|--------|----------------|------|
| KG-RAG | 1024 tokens | 0.804 |
| FinanceBench | 1024 tokens | 0.579 |
| Earnings | 512 tokens | 0.681 |
| SQuAD (实体答案) | 64 tokens | 64.1% recall@1 |
| TechQA (技术答案) | 512 tokens | 61.3% recall@1 |

- **Overlap 测试** (0%, 25%, 50%): 25% overlap 在多数场景下表现最佳
- **6 种 chunker 对比**: token, sentence, semantic, recursive, SDPM, neural

**启示**: 没有万能的 chunk size，必须根据数据集和查询类型实测。

### 6.5 案例五：临床决策支持系统 (PMC, 2025.11)

**背景**：对比 4 种分块策略在临床 QA 中的效果。

**结果**:

| 策略 | 医学准确率 | 完全准确占比 | F1 分数 |
|------|-----------|-------------|---------|
| 自适应分块 | 2.37 ± 0.72 | 50% (15/30) | 0.64 |
| 命题分块 | 2.07 ± 0.78 | 33% (10/30) | 0.50 |
| 语义分块 | 2.03 ± 0.76 | 30% (9/30) | 0.46 |
| 固定分块 | 1.40 ± 0.81 | 13% (4/30) | 0.24 |

**关键发现**:
- 自适应分块 (按主题边界) 显著优于所有其他策略 (p=0.001)
- 固定分块在结构化临床文档上表现最差
- 语义分块略优于命题分块，但差距不大

**启示**: 当文档有强内在结构时，尊重结构的分块策略远超固定分块。

### 6.6 案例六：本项目 (PaperAgent) 的实现

本项目 `parser_service.py` 已实现的管道：

1. **多解析器回退链**：PyMuPDF → pdfplumber → pypdf → OCR
2. **TextPostProcessor**：
   - CID 伪影修复 (`fix_cid_artifacts`)
   - 连字修复 (`fix_ligatures`)
   - 词间距修复 (`fix_word_spacing`)
   - 断词拼接 (`fix_hyphenation`)
   - 引用标记修复 (`fix_citation_markers`)
   - 页码移除 (`remove_page_numbers`)
   - 页眉页脚检测 (`remove_headers_footers`，>80% 页面重复的短行)
3. **结构感知分块**：按 Section 切分，500-900 token，80 token overlap
4. **ChunkCleaner**：
   - 公式行过滤（数学符号占比 >20%）
   - 坐标轴标签块检测（连续 5+ 短行）
   - 碎片合并（<200 token 的 chunk 合并到相邻 chunk，上限 1000 token）

---

## 7. 技术难点与解决方案

### 7.1 多栏布局识别

**难点**：学术论文通常双栏排版，文本提取工具可能错误地将左栏右栏交替拼接。

**2025-2026 新发现**：
- **Applied AI 基准**: 学术论文解析准确率仅 40-60%，远低于法律合同的 95%
- **错误级联**: 布局检测的小误差在后续 OCR 和元素解析中被放大为严重失败
- **传统 OCR 噩梦**: 多栏布局导致 OCR 引擎跨栏读取而非逐栏读取，产生不连贯段落
- **VLM 泛化更好**: OmniDocBench (CVPR 2025) 发现通用 VLM 在幻灯片和手写笔记上比 pipeline 工具泛化更强

**解决方案**：
- **版面分析模型**：Layout-Parser, Detectron2 检测栏区域
- **坐标聚类**：按 x 坐标将字符分为左栏/右栏，然后按 y 坐标排序
- **MinerU**：内置双栏检测，自动处理阅读顺序
- **Google Document AI**: Layout Parser 自动检测列边界并建立正确阅读顺序
- **混合策略**: 先用原生提取检测页面类型，需要 OCR 时自动切换

### 7.2 公式与特殊符号

**难点**：数学公式提取后通常为乱码或无意义字符。

**解决方案**：
- **启发式过滤**：检测数学符号占比 >20% 的行（本项目方案）
- **公式识别模型**：Pix2Tex, MathOCR 将公式图片转为 LaTeX
- **Nougat**：内置公式识别，输出 LaTeX 格式

### 7.3 表格提取

**难点**：PDF 中表格是图形元素，不包含结构信息。

**解决方案**：
- **pdfplumber**：基于线条检测的表格提取
- **Camelot**：专门的 PDF 表格提取库
- **表格识别模型**：TableTransformer (Microsoft)

### 7.4 跨页段落拼接与页眉页脚移除

**难点**：段落可能跨页断裂，中间插入页眉/页脚/页码。页眉页脚被误识别为正文内容。

**2025-2026 新发现**：
- **Docling Issue #1272**: Docling 目前将页眉页脚误识别为章节标题，社区请求自动检测功能
- **页脚污染 embedding 案例**: "每个 chunk 末尾都包含 'Confidential Draft – [Page X]'，严重污染 embedding"
- **参考文献泄漏**: "AI 开始输出脚注部分的参考文献引用，不是用户需要的答案"
- **字体大小检测**: pdfplumber 字符分析可按字体大小区分正文与脚注 -- 脚注通常更小
- **Running heads**: 正则 `^Page \d+ of \d+` 和已知页眉字符串移除

**解决方案**：
- **页眉页脚检测**：统计重复行（>80% 页面出现）
- **段落拼接**：移除页眉页脚后，将首尾段落连接
- **字体分析**: pdfplumber 按字体大小分类文本块，只保留主字体大小的文本用于 embedding
- **正则清理**: 静态页眉页脚用正则匹配替换为空
- **默认移除脚注/参考文献**: 在 QA 场景中默认移除，避免污染答案
- **本项目方案**：`remove_headers_footers` 检测重复短行，分块时 buffer 机制跨页拼接

### 7.5 语言混杂

**难点**：中英文混杂的论文，或参考文献中的多语言内容。

**解决方案**：
- **语言检测**：langdetect/lingua-py 逐 chunk 检测
- **分语言处理**：中文按字符切分，英文按词切分
- **本项目方案**：token 估算区分 CJK 和 ASCII（CJK/2 + ASCII/4）

### 7.6 去重的精度与效率平衡

**难点**：精确去重 O(n²) 不可行，近似去重有误判。

**解决方案**：
- **MinHash + LSH**：O(1) 近似判断，误判率可调
- **SimHash**：内存效率更高，适合大规模
- **分层去重**：先精确哈希，再 MinHash 近似

---

## 8. 未来发展趋势

### 8.1 端到端 VLM 解析

传统管道 (提取→清洗→分块) 将被 VLM 端到端方案取代：
- 直接输入 PDF 页面图片，输出结构化文本
- 无需手工规则清洗，模型自动处理噪声
- 2025-2026 年将有更多专用模型发布

### 8.2 自适应分块

根据文档内容自动选择最佳分块策略：
- 学术论文用结构感知分块
- 法律文档用条款感知分块
- 代码文档用函数/类感知分块
- LLM 驱动的分块策略选择

### 8.3 质量感知检索

检索时不仅考虑语义相似度，还考虑 chunk 质量：
- 质量分数作为检索排序因子
- 低质量 chunk 在索引时标记，检索时降权
- 用户可设置质量阈值

### 8.4 多模态 chunk

将文本、图表、公式、代码统一为多模态 chunk：
- 图表 chunk 包含图片 + 标题 + 描述
- 公式 chunk 包含 LaTeX + 语义解释
- 代码 chunk 包含代码 + 注释 + 文档

### 8.5 实时增量处理

支持论文增量入库时的实时清洗和分块：
- 流式处理管道
- 增量去重（不需全量重建）
- 增量索引更新

---

## 9. 学术论文专项调研 (2023-2026)

> 以下内容来自 2026-05-30 的 15 次学术论文专项搜索，覆盖 10 个指定搜索主题。

### 9.1 "Lost in the Middle" — LLM 位置偏差与 Chunk 排序

**核心论文**:
- **Liu et al.** "Lost in the Middle: How Language Models Use Long Contexts." TACL 2024, Stanford. arXiv:2307.03172
  - **核心发现**: LLM 对上下文中信息的位置敏感，呈 U 型曲线 — 开头和结尾性能最高，中间下降
  - **方法**: 控制实验，将答案文档放在不同位置，测量 QA 准确率
  - **实践启示**: 将最相关证据放在上下文开头或结尾

- **Yu et al.** "Lost but not only in the Middle." 2024.
  - **扩展**: 退化不仅限于正中间，可能在多个位置出现，取决于提示方式和文档布局

- **"Lost in the Evidence? Reproducing Document Position and Context Size Effects in RAG."** arXiv:2605.27105, 2025.
  - **发现**: 位置效应与 passages 的组合方式有关，包括 chunks 是否保持文档内顺序 vs 纯按相关性拼接
  - 报告了添加更多 chunks 时的非单调行为

- **"Do RAG Systems Suffer From Positional Bias?"** HuggingFace Papers, 2025.
  - **关键发现**: 在真实 RAG 场景中，位置偏差影响被高估
  - 检索管道系统性地将高度干扰的 passages 带到 top ranks
  - 超过 60% 的查询在 top-10 中包含至少一个高度干扰 passage
  - **结论**: 精心设计的重排策略并不优于随机打乱

- **"Inference Scaling for Bridging Retrieval and Augmented Generation."** arXiv:2412.10684, 2024.
  - 提出 MoI (Marginal over Importance) 方法，同时确定位置偏差和去偏效用

**实践建议**:
- 将最相关证据放在上下文开头
- 考虑在末尾重复关键信息
- 使用层次化或多步阅读而非单一长上下文
- 在真实场景中，位置偏差影响可能不如控制实验中那么显著

### 9.2 Late Chunking — Jina AI 先编码后分块

**核心论文**:
- **Günther, Mohr, Williams, Wang, Xiao.** "Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models." arXiv:2409.04701, 2024.
  - **核心创新**: 先对整个文档（最多 8192 tokens）做 transformer 编码得到 token 级向量，再对每个 chunk 的 token 向量做 mean pooling
  - **优势**: 每个 chunk 的 embedding 包含全文上下文信息，解决传统分块的 i.i.d. 假设问题
  - **限制**: 需要长上下文嵌入模型（如 jina-embeddings-v2/v3），文档必须在模型上下文窗口内
  - **API 支持**: jina-embeddings-v3 通过 `late_chunking=True` 参数启用
  - **评估**: BeIR 多个数据集上 nDCG@10 提升

**技术原理**:
```
传统分块: [chunk1] → embed → vec1, [chunk2] → embed → vec2  (独立编码)
Late Chunking: [全文] → transformer → [token_vecs] → 按chunk边界 mean_pool → [vec1, vec2]  (全局感知)
```

**关键特性**:
1. 双向上下文感知: 每个 token embedding 受全文所有 token 影响
2. 一致表示: 同一文档的所有 chunks 共享相同的上下文基础
3. 长程依赖保持: 文档开头的信息可以影响结尾的表示

**实践数据**:
- BeIR 基准上 nDCG@10 提升约 6.5 点
- 需要支持 mean pooling 的模型（CLS-token 模型不适用）
- 弱 embedding 模型 + Late Chunking 仍不如强模型不使用 Late Chunking

### 9.3 RAPTOR — 递归层次化检索

**核心论文**:
- **Sarthi et al.** "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval." ICML 2024.
  - **原理**: 递归聚类 chunks → LLM 生成摘要 → 再聚类 → 构建层次树
  - **检索**: 跨所有层级搜索（叶子节点 + 中间摘要 + 根摘要）
  - **性能**: QuALITY 阅读理解基准 +20% 绝对准确率（GPT-4），SQuAD 上约 99% 检索准确率
  - **基准数据**: QuALITY 62.4% vs DPR 60.4% vs BM25 57.3%

**树构建过程**:
1. 文档分块 → 叶子节点
2. 基于 embedding 相似度聚类
3. LLM 对每个聚类生成摘要 → 父节点
4. 递归: 对父节点继续聚类 + 摘要
5. 直到达到根节点

**变体与扩展**:
- **SiReRAG** (2024 年末): 在 RAPTOR 基础上增加实体关系维度
  - 相似度: 向量/全文搜索计算语义距离
  - 相关性: LLM 提取命名实体，基于实体关系构建层次树
  - 混合召回: 实体、实体组、原始文本多粒度

**集成案例**:
- RAGFlow 在 2024 年中期集成 RAPTOR
- 预聚类 → LLM 摘要 → 摘要与原文一起送入搜索
- 对模糊查询和多跳问题效果显著

### 9.4 DPR Chunk Size — 最优检索单元大小

**核心参考**:
- **Karpukhin et al.** "Dense Passage Retrieval for Open-Domain Question Answering." EMNLP 2020.
  - 双编码器架构，使用批内负样本训练
  - 在 NQ 测试集上 top-1 准确率 52.47%（改进版）

**Chroma 实证研究** (trychroma.com/research/evaluating-chunking):

| Chunking | Size | Overlap | Recall | Precision | Precision_Omega | IoU |
|----------|------|---------|--------|-----------|-----------------|-----|
| Recursive | 200 | 0 | 86.7% | 23.5% | 25.7% | 23.4% |
| Recursive | 400 | 0 | 76.5% | 13.2% | 16.1% | 13.2% |
| Recursive | 400 | 200 | 94.3% | 8.0% | 11.4% | 8.0% |
| Recursive | 800 | 400 | 80.8% | 4.8% | 7.2% | 4.8% |
| TokenText | 200 | 0 | 77.3% | 19.5% | 24.7% | 19.2% |
| TokenText | 400 | 0 | 67.1% | 10.2% | 14.1% | 10.2% |
| TokenText | 400 | 200 | 82.2% | 5.8% | 10.0% | 5.8% |
| TokenText | 800 | 400 | 89.5% | 3.5% | 5.4% | 3.5% |

**关键洞察**:
- 小 chunks (200) 无重叠时 precision 最高 (23.5%)
- 大 chunks (400) 有重叠时 recall 最高 (94.3%)
- Recursive 优于 TokenText 在大多数配置下
- 存在 precision-recall 权衡，需根据应用场景选择

### 9.5 Semantic Chunking 评估 — 语义 vs 固定分块

**核心论文**:
- **Qu & Bao (Vectara).** "Is Semantic Chunking Worth the Computational Cost?" Findings of NAACL 2025. arXiv:2410.13070. aclanthology.org/2025.findings-naacl.114

**实验设计**:
- 3 个 RAG 任务: 文档检索、证据检索、答案生成
- 对比: 语义分块 vs 固定大小分块
- 数据集: 包括合成数据集和真实数据集

**核心结论**:
> "语义分块偶尔能提升性能，特别是在主题多样性高的拼接数据集上。但这些收益高度依赖上下文，并不能一致地证明额外的计算成本是合理的。在非合成数据集上，固定大小分块通常表现更好。"

**具体发现**:
1. 在真实文档上，固定 200 词 chunks 匹配或超过语义分块
2. 语义分块比固定分块慢 2-3 倍（Chonkie 基准: 14 倍，0.33 MB/s vs 4.82 MB/s）
3. 语义分块阈值（余弦相似度 0.7）是任意的，换 embedding 模型需重新调参
4. embedding 模型质量的影响往往超过分块策略的影响

**其他相关研究**:
- **PMC Bioengineering (2025.11)**: 临床决策支持研究，自适应分块 87% vs 固定 13% (p=0.001)
  - 但这是结构化临床文档，不代表所有场景
- **Vecta 2026 基准**: 递归 512-token 第一 (69%)，语义分块仅 54%

### 9.6 Document Quality Filtering — FineWeb 与困惑度过滤

**核心论文**:
- **Penedo et al.** "The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale." NeurIPS 2024.
  - 从 96 个 Common Crawl 快照构建 15 万亿 token 数据集
  - 详细文档化并消融了去重和过滤策略的所有设计选择
  - FineWeb-Edu: 1.3 万亿 token 教育文本，使用 fastText 分类器过滤
  - 在 MMLU 和 ARC 等知识推理基准上显著提升 LLM 性能

- **Ultra-FineWeb.** "Efficient Data Filtering and Verification for High-Quality LLM Training Data." arXiv:2505.05427, 2025.
  - 进一步优化 FineWeb
  - 在 MMLU 上 +3.46pp，ARC-C 上 +10.50pp
  - 提出高效的数据过滤验证方法

- **Seo et al.** "Prior-based Noisy Text Data Filtering: Fast and Strong Alternative For Perplexity." ICLR 2026.
  - **创新**: 使用语料库级词频统计估计 token 先验，作为困惑度的快速替代
  - **速度**: 比困惑度方法快 1000 倍，效果相当
  - 无需模型推理
  - 基于语言学洞察: 词角色和词汇密度

**质量过滤方法对比**:

| 方法 | 原理 | 速度 | 效果 | 代表工作 |
|------|------|------|------|---------|
| 困惑度过滤 | LM 计算 PPL | 慢 | 好 | CCNet, FineWeb |
| 分类器过滤 | fastText 训练 | 快 | 好 | FineWeb-Edu, DCLM |
| 先验过滤 | 词频统计 | 极快 | 相当 | ICLR 2026 |
| LLM 评估 | 多维度 prompt | 极慢 | 最好 | Sachdeva et al., 2024 |

### 9.7 Text Deduplication — MinHash 与 SimHash

**基准数据** (text-dedup 库):

| 算法 | Precision (Dup) | Recall (Dup) | Macro F1 | Accuracy | Time |
|------|----------------|--------------|----------|----------|------|
| MinHash | 0.9587 | 0.9416 | 0.9518 | 0.9277 | 11.09s |
| SimHash | 0.9038 | 0.7323 | 0.8515 | 0.8375 | 626.11s |

**NEWS-COPY 数据集 ARI**:

| 算法 | ARI | Time |
|------|-----|------|
| MinHash | 0.7293 | 3.01s |
| SimHash | 0.6463 | 140.03s |
| MinHash + LSH | 0.783 | - |
| RETSim Partial-Dup | 0.831 | - |

**语义去重** (semhash, 2025):
- 基于 embedding 的近似去重
- 解决 MinHash 只能检测字符级相似的问题
- 使用 potion-base-8m 等小模型实现快速语义匹配
- 支持精确去重和近似去重的混合模式

**MinHash + LSH 工作原理**:
1. 文档 → n-gram 集合 (shingling)
2. MinHash 签名: 100-200 个哈希值，签名相似度 = Jaccard 相似度
3. LSH 分桶: 将签名分为 b bands × r rows，同一桶内为候选对
4. 将 O(n²) 比较降为近似线性

**FineWeb 实践**:
- MinHash + LSH 跨文档去重
- 质量过滤移除约 60% 数据
- 去重移除约 15% 数据

### 9.8 Academic Paper Section Detection — 学术论文章节识别

**核心工具**:
- **GROBID** (kermitt2/grobid): 学术论文解析黄金标准
  - 使用级联模型处理不同文档区域
  - 分割模型检测文档主要区域（基于布局特征）
  - 级联模型允许独立调优每个模型
  - 2025 年改进了表格和公式识别

- **Science Parse v2** (Allen AI): 基于 SciBERT 的论文结构化解析
- **CERMINE**: 学术论文元数据和结构提取
- **PP-DocLayout** (2025): 统一布局检测框架
  - 支持 23 种布局类别
  - 推理速度超过 120 页/秒
  - 支持学术论文、书籍、杂志、试卷等多种文档类型

**文档解析综述** (arXiv:2410.21169, 2024-2025):
- 从宏到微的训练策略显著提升小布局组件检测性能
- 单阶段检测器在效率上优于两阶段检测器，但在密集布局上鲁棒性可能降低
- 表格结构识别: 行列分割 → 单元格内容提取 → 结构化输出（LaTeX/HTML）

**READOC-Zenodo 基准** (ACL Findings 2025):

| 系统 | 语义单元评估 | 阅读顺序 | 文本 | 标题 | 表格 |
|------|-------------|---------|------|------|------|
| MinerU | 57.28 | 59.95 | 30.73 | 22.83 | 38.75 |
| Marker | 59.34 | 61.68 | 30.28 | 18.29 | 40.68 |
| Nougat-base | 57.54 | 66.87 | 35.99 | 26.98 | 13.99 |
| GPT-4o-mini | 64.16 | 71.76 | 25.07 | 15.4 | 45.75 |

**OmniDocBench** (CVPR 2025):
- 1651 页 PDF, 10 种文档类型, 5 种布局类型, 5 种语言
- 28 种块级标注, 4 种 span 级标注
- 评估公式: Overall = (1-Text Edit Distance) × 100 + Table TEDS + Formula CDM) / 3

### 9.9 RAG Chunking Strategies Comparison — 分块策略基准对比

**NVIDIA 2024 基准测试**:
- 7 种策略 × 5 个数据集（FinanceBench, Earnings, KG-RAG, RAGBattlePacket, RAGChallenge）
- Page-level 分块: 0.648 准确率, 0.107 标准差（最一致）
- 查询类型影响最优 chunk size:
  - 事实型查询: 256-512 tokens 最优
  - 分析型查询: 1024+ tokens 最优
- 金融文档: 1024-token 最优 (57.9% 准确率)

**IEEE COINS 2025**:
- 90 种 chunker-model 配置跨 7 个 arXiv 领域（2520 次检索运行）
- 7 种开源 embedding 模型 × 语义/固定分块策略
- **结果**:
  - 句子分块（512-token 窗口, 200-token 重叠）达到最高 IoU (~0.099)
  - 较小 embedding 模型的跨域性能更稳定
  - 金融文本受益最多，天体物理学最差

**Mix-of-Granularity (MoG)** (COLING 2025, arXiv:2406.00456):
- 动态确定最优粒度的路由器
- MoGG 扩展到图结构
- 多个医学 QA 数据集上一致提升 RAG 性能
- 软标签训练路由器

**ChunkRAG** (arXiv 2025):
- 可学习语义边界的分块框架
- TF-IDF + 余弦相似度过滤冗余 chunks (>0.9 剔除)
- 层次分割 + 哈希索引

**HiChunk** (2025):
- 微调语言模型预测全局分块点
- Auto-Merge 检索时动态合并相关 chunks
- 解决细粒度检索与语义完整性的张力

**FreeChunker** (HuggingFace Papers):
- 跨粒度编码框架
- 句子作为原子单元
- 从静态分块切分转向灵活的任意句子组合检索

### 9.10 PDF Text Extraction Quality Evaluation — PDF 文本提取质量评估

**OmniDocBench** (CVPR 2025, github.com/opendatalab/OmniDocBench):
- 1651 页 PDF, 10 种文档类型
- 28 种块级标注（文本段落、标题、表格等）
- 4 种 span 级标注（文本行、行内公式、下标等）
- 阅读顺序标注
- 5 种页面属性标签, 3 种文本属性标签, 6 种表格属性标签

**READOC-Zenodo** (ACL Findings 2025):
- 统一基准评估文档结构化提取
- 评估: 语义单元、阅读顺序、文本、标题、表格
- GPT-4o-mini 在阅读顺序上领先 (71.76)，但成本高

**PDF Data Extraction Benchmark 2025** (Procycons):
- 对比 Docling, Unstructured, LlamaParse
- 评估维度: 文本提取准确率、表格检测、结构保留、ToC 准确率、处理速度
- Docling: 核心内容 100% 准确率
- 针对 ESG 报告的复杂多级表格

**DeltOCR Bench** (AIMultiple, 2025):
- 比较多种 OCR 服务和本地解决方案
- 包括 GPT-4o, Claude, Llama 3.2 等多模态 LLM
- 覆盖 API 服务和本地基础设施

---

## 10. 开源项目实现细节深度调研 (2025-2026)

> 以下为 10 个核心开源项目的深度调研结果，覆盖 GitHub Stars、算法原理、关键参数、代码模式。
> 搜索来源: Tavily Advanced Search (15 次搜索)，覆盖官方文档、GitHub、技术博客、学术论文。

### 10.1 datasketch — MinHash LSH 去重

**GitHub**: https://github.com/ekzhu/datasketch | Stars: ~2,900 | Python | License: MIT

**核心算法**：MinHash + LSH (Locality-Sensitive Hashing) 用于 Jaccard 相似度估计与近似去重。

**关键类**：
- `MinHash` — 估计 Jaccard 相似度和基数
- `Weighted MinHash` — 估计加权 Jaccard 相似度
- `MinHashLSH` — Jaccard 阈值查询索引
- `MinHashLSHForest` — Jaccard Top-K 查询
- `MinHashLSHEnsemble` — Containment 阈值查询
- `LSHBloom` — 基于 Bloom filter 的 LSH 索引（2025 新增）

**关键参数与调优**：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `num_perm` | 哈希排列函数数量，越多精度越高但越慢 | 128 (标准), 256 (高精度) |
| `threshold` | Jaccard 相似度阈值 | 0.5 (宽松), 0.8 (严格去重) |
| `weights` | (fp_weight, fn_weight) 调节假阳/假阴权重 | (0.5, 0.5) 默认, (0.4, 0.6) 高召回 |
| `params` | (b, r) 手动指定 band 数和 band 大小 | 跳过自动优化时使用 |

**可复用代码模式**：

```python
from datasketch import MinHash, MinHashLSH

# 1. 创建 LSH 索引（自动优化 b 和 r 参数）
lsh = MinHashLSH(threshold=0.5, num_perm=128)

# 2. 为文档创建 MinHash 签名
m = MinHash(num_perm=128)
for word in document.lower().split():
    m.update(word.encode('utf8'))

# 3. 插入和查询
lsh.insert("doc_id", m)
results = lsh.query(m)  # 返回相似文档 ID 列表

# 4. 批量创建（GPU 加速模式，2025 新增）
m = MinHash(num_perm=256, gpu_mode="detect")
m.update_batch([b"token1", b"token2", b"token3"])

# 5. Redis 后端（大规模场景）
lsh = MinHashLSH(
    threshold=0.9, num_perm=128,
    storage_config={
        "type": "redis",
        "basename": b"mylsh",
        "redis": {"host": "localhost", "port": 6379},
    }
)

# 6. 异步批量插入（高性能）
import asyncio
async with MinHashLSH(threshold=0.5, num_perm=16) as lsh:
    async with lsh.insertion_session(batch_size=1000) as session:
        fs = [session.insert(key, mh, check_duplication=False) for key, mh in data]
        await asyncio.gather(*fs)
```

**2025 更新**：
- 新增 GPU 模式支持（CuPy/CUDA），`gpu_mode="detect"` 自动检测
- `update_batch()` 批量哈希，GPU 路径下性能提升显著
- 新增 `LSHBloom` 索引类型，基于 Bloom filter，内存效率更高
- 支持 Python 3.9+，依赖 NumPy 和 Scipy

**与其他工具的关系**：
- NeMo Curator、FineWeb、RedPajama v2 均使用 MinHash LSH 做模糊去重
- SlimPajama 使用 datasketch 的 CPU 实现
- FED 框架修复了 datasketch 的一些 bug 并做了 GPU 加速
- Milvus 2.6 支持原生 MinHash LSH 索引

---

### 10.2 RapidFuzz — 快速模糊字符串匹配

**GitHub**: https://github.com/rapidfuzz/RapidFuzz | Stars: ~3,900 | Python/C++ | License: MIT

**核心算法**：Levenshtein 距离、Damerau-Levenshtein、Jaro-Winkler 等字符串相似度度量，C++ 底层实现。

**性能**：比 FuzzyWuzzy 快 10-100x，最新版本 3.14.x (2026年3月)。

**关键函数**：

| 函数 | 用途 | 适用场景 |
|------|------|---------|
| `fuzz.ratio()` | 完整字符串相似度 | 短文本精确匹配 |
| `fuzz.partial_ratio()` | 子串匹配 | 部分匹配 |
| `fuzz.token_sort_ratio()` | 词序无关匹配 | 词序不同的近似匹配 |
| `fuzz.token_set_ratio()` | 集合匹配 | 包含关系的文本 |
| `process.extract()` | 批量匹配 | 从候选列表中找最佳匹配 |
| `process.extractOne()` | 单次匹配 | 找最佳单个匹配 |
| `cdist()` | 矩阵计算 | 大规模两两比较 |

**可复用代码模式**：

```python
from rapidfuzz import process, fuzz

# 1. 基本相似度计算
score = fuzz.ratio("Salesforce Street", "SAP Street")  # 0-100

# 2. 从候选列表中找最佳匹配
duplicates = process.extract(
    query="target text",
    choices=["text1", "text2", "..."],
    scorer=fuzz.token_sort_ratio,
    score_cutoff=85  # 阈值过滤
)

# 3. 大规模去重：阻塞策略 (blocking)
# 只比较共享相同前缀/音码的字符串，减少 90-95% 比较
from rapidfuzz import cdist
# cdist 计算矩阵形式的相似度，比逐对比较快得多
```

**生产建议**：
- 阈值 >= 80 为强匹配，60-80 需人工审核
- 大规模场景结合 blocking（前缀、音码、邮编）减少比较空间
- 与 datasketch (MinHash) 互补：MinHash 做粗筛，RapidFuzz 做精排

---

### 10.3 Dolma (AI2) — 数据整理工具包

**GitHub**: https://github.com/allenai/dolma | Stars: ~1,500 | Python/Rust | License: Apache 2.0

**核心定位**：Allen AI 为 OLMo 模型构建的开源数据整理工具包，处理 3 万亿 token 数据集。

**管道步骤**：

| 步骤 | 方法 | 说明 |
|------|------|------|
| 语言检测 | fastText lid.176 | 阈值 > 0.5 保留英文 |
| 质量过滤 | Gopher + C4 规则 | 启发式规则组合 |
| 去重 | Bloom filter + MinHash | URL 去重 + 段落去重 |
| 内容过滤 | 正则 + 分类器 | 有害内容、PII |
| 困惑度过滤 | KenLM | 过滤噪声/乱码文本 |

**Gopher 质量过滤规则**（Dolma 采用的核心规则集）：
- 文档词数在合理范围内
- 平均词长在 3-10 字符
- 行尾标点符号比例
- 停用词比例检查
- 重复行/重复段落比例
- 特殊字符比例上限

**C4 补充规则**：
- 移除不以标点结尾的段落（`C4 NoPunc`）

**代码数据过滤**（来自 RedPajama v1 + StarCoder）：
- 移除 JSON/CSV 扩展名文件
- 移除模板化文件头（许可证声明）
- 过滤过长行或主要为数字的文件
- 过滤低星仓库的代码
- 过滤注释比例异常的代码

**Dolma 3 更新 (2025)**：
- 新增万亿级全局去重工具
- 新增 olmOCR 科学 PDF 文本提取
- 使用 WebOrganizer 工具将文档分为 24 个主题
- fastText 蒸馏版主题分类器
- fastText 质量分类器（正例：OpenHermes-2.5 + ELI5 + UltraChat-200k + WildChat-1M，负例：DCLM-RefinedWeb）

---

### 10.4 NeMo Curator (NVIDIA) — 企业级文本数据管道

**GitHub**: https://github.com/NVIDIA-NeMo/Curator | Stars: 高星 (NVIDIA 官方) | Python | License: Apache 2.0

**核心定位**：GPU 加速的大规模数据预处理框架，支持文本/图像/视频多模态，可扩展到 100+ PB。

**性能数据**：
- 16x 快速模糊去重（8TB RedPajama v2，1.78 万亿 token）
- 比 CPU 方案降低 40% TCO
- 从 1 到 4 个 H100 80GB 节点近线性扩展（2.05h -> 0.50h）

**完整管道代码**：

```python
import nemo_curator as nc
from nemo_curator.datasets import DocumentDataset
from nemo_curator.filters import (
    WordCountFilter, MeanWordLengthFilter,
    RepeatedLinesByCharFilter, PunctuationFilter,
)
from nemo_curator import ExactDuplicates, MinHashDeduplicator
from nemo_curator.utils.distributed_utils import get_client

client = get_client(cluster_type="gpu")
dataset = DocumentDataset.read_json("./corpus/*.jsonl", add_filename=True)

# 阶段 1: 精确去重 (MD5)
exact_dup = ExactDuplicates(id_field="id", text_field="text", hash_method="md5")
dataset = exact_dup(dataset)

# 阶段 2: MinHash 模糊去重
minhash = MinHashDeduplicator(
    id_field="id", text_field="text",
    num_hashes=128, char_ngrams=5, jaccard_threshold=0.8,
)
dataset = minhash(dataset)

# 阶段 3: 启发式质量过滤
filters = nc.Sequential([
    WordCountFilter(min_words=50, max_words=100_000),
    MeanWordLengthFilter(min_mean_word_length=3, max_mean_word_length=10),
    RepeatedLinesByCharFilter(max_repeated_lines_fraction=0.3),
    PunctuationFilter(max_non_alpha_numeric_to_alpha_ratio=0.3),
])
dataset = filters(dataset)

dataset.to_parquet("./curated_output/")
```

**文本清洗模块**：

```python
from nemo_curator.stages.text.modifiers import Modify
from nemo_curator.stages.text.modifiers.string import UrlRemover, NewlineNormalizer
from nemo_curator.stages.text.modifiers.unicode import UnicodeReformatter

pipeline = Pipeline(name="text_cleaning_pipeline")
pipeline.add_stage(Modify(UnicodeReformatter()))    # Unicode 规范化
pipeline.add_stage(Modify(NewlineNormalizer()))     # 换行符标准化
pipeline.add_stage(Modify(UrlRemover()))            # URL 移除
```

**30+ 启发式过滤器**：WordCountFilter, MeanWordLengthFilter, RepeatedLinesByCharFilter, PunctuationFilter, UrlsFilter, NonAlphaNumericFilter, RepeatingTopNGramsFilter 等。

**去重策略三件套**：
1. `ExactDuplicates` — MD5 哈希精确去重
2. `MinHashDeduplicator` — MinHash LSH 模糊去重
3. `TextSemanticDeduplicationWorkflow` — 基于 embedding 的语义去重

---

### 10.5 RedPajama v2 (Together AI) — LLM 数据管道

**GitHub**: https://github.com/togethercomputer/RedPajama-Data | Stars: 高星 | Python | License: Apache 2.0

**核心定位**：30+ 万亿 token 的网络数据集，提供原始文本 + 质量信号 + 元数据，用户自行过滤。

**数据规模**：

| 语言 | 文档数 (去重后) | Token 数 (去重后) |
|------|----------------|-------------------|
| en | 24.5B | 37.0T |
| de | 2.7B | 4.1T |
| fr | 2.2B | 3.7T |
| es | 2.3B | 3.9T |
| it | 1.2B | 1.9T |
| 总计 | 32.9B | 50.6T |

**三步管道**：准备工件 -> 计算质量信号 (含 MinHash 签名) -> 去重 (Bloom filter + MinHash LSH)

**质量信号列表**（每个文档附带的元数据）：

| 信号名 | 说明 | 类别 |
|--------|------|------|
| `rps_doc_num_sentences` | 句子数 (正则: `r'\b[^.!?]+[.!?]'`) | 自然语言 |
| `rps_doc_frac_chars_dupe_10grams` | 重复 10-gram 字符比例 | 重复性 |
| `rps_doc_frac_chars_dupe_5grams` | 重复 5-gram 字符比例 | 重复性 |
| `rps_doc_frac_chars_dupe_6grams` | 重复 6-gram 字符比例 | 重复性 |
| `rps_doc_ut1_blacklist` | UT1 黑名单域名分类 | 内容安全 |

**可复用代码模式**：

```python
from datasets import load_dataset
import json, re

ds = load_dataset("togethercomputer/RedPajama-Data-V2", name="sample", streaming=True)
url_pattern = re.compile(r"https?://.*\.com")
for instance in ds["train"]:
    metadata = json.loads(instance["meta"])
    if url_pattern.search(metadata["url"]) is None:
        continue
    # 基于质量信号进一步过滤
```

---

### 10.6 Chonkie — 轻量级 RAG 分块库

**GitHub**: https://github.com/chonkie-inc/chonkie | Stars: 增长中 (2025年3月创建) | Python | License: MIT

**核心定位**：轻量、快速、易用的 RAG 分块库，默认安装仅 11.2MB。

**性能**：Token 分块 33x 快于替代方案，句子分块 2x，语义分块 2.5x。

**9 种分块器**：

| 分块器 | 原理 | 适用场景 |
|--------|------|---------|
| `TokenChunker` | 固定 token 数切分 | 通用 |
| `WordChunker` | 按词切分 | 简单文本 |
| `SentenceChunker` | 按句子边界切分 | 保持语义完整 |
| `RecursiveChunker` | 递归切分 (段落->句子->标点->词->字符) | 通用最佳选择 |
| `SemanticChunker` | 基于 embedding 相似度 | 主题边界检测 |
| `SDPMChunker` | Semantic Double-Pass Merge | 高质量语义分块 |
| `LateChunker` | 先 embedding 再分块 | 全局上下文感知 |
| `NeuralChunker` | 微调 BERT 检测语义转换 | 高精度主题分割 |
| `SlumberChunker` | LLM 驱动的智能分块 | 最高质量 |

**可复用代码模式**：

```python
from chonkie import RecursiveChunker, SemanticChunker, Pipeline

# 1. 递归分块（推荐通用场景）
chunker = RecursiveChunker(tokenizer="gpt2", chunk_size=512, recipe="markdown")
chunks = chunker("Your document text...")

# 2. 语义分块
chunker = SemanticChunker(
    embedding_model="minishlab/potion-base-32M",
    threshold=0.7, chunk_size=512,
    min_sentences_per_chunk=3, min_characters_per_sentence=30,
)
chunks = chunker("Your document text...")

# 3. Pipeline 模式（端到端）
pipe = (
    Pipeline()
    .chunk_with("recursive", tokenizer="gpt2", chunk_size=2048, recipe="markdown")
    .chunk_with("semantic", chunk_size=512)
    .refine_with("overlap", context_size=128)
    .refine_with("embeddings", embedding_model="sentence-transformers/all-MiniLM-L6-v2")
)
doc = pipe.run(texts="Your document text...")
```

---

### 10.7 spaCy — 工业级 NLP 管道

**GitHub**: https://github.com/explosion/spaCy | Stars: ~33,600 | Python | License: MIT

**核心定位**：工业级 NLP 库，支持 75+ 语言，84 个训练管道，生产级速度。

**NER 在文本清洗中的应用代码**：

```python
import spacy
nlp = spacy.load("en_core_web_sm")

# 识别实体
doc = nlp("Apple Inc. is planning to open a new office in San Francisco.")
for ent in doc.ents:
    print(ent.text, ent.label_)
    # Apple Inc. -> ORG, San Francisco -> GPE

# 自定义 EntityRuler（规则 + 字典）
ruler = nlp.add_pipe("entity_ruler", before="ner")
patterns = [
    {"label": "CHEMICAL", "pattern": "aspirin"},
    {"label": "GENE", "pattern": [{"TEXT": {"REGEX": r"[A-Z]{2,}[0-9]+"}}]},
]
ruler.add_patterns(patterns)
```

**在学术论文清洗中的应用场景**：PII 检测、术语提取、引用解析、领域分类。

---

### 10.8 trafilatura — 网页正文提取与样板去除

**GitHub**: https://github.com/adbar/trafilatura | Stars: ~5,400+ (2025初) | Python | License: MIT/AGPL

**核心定位**：从 HTML 中提取主要文本内容，去除样板。v2.0.0 于 2024年12月发布。HuggingFace、IBM、Microsoft Research、Stanford、Allen AI 均在生产中使用。

**关键参数**：

```python
import trafilatura
text = trafilatura.extract(
    downloaded,
    include_comments=False,     # 移除评论
    include_tables=True,        # 保留表格
    output_format='txt',        # txt/json/csv/xml/xmltei/markdown/html
    favor_precision=True,       # 优先精确
    favor_recall=False,         # 优先召回
    deduplicate=True,           # 移除重复内容
)
```

**在学术论文场景中的价值**：FineWeb 使用 trafilatura 从 Common Crawl HTML 中提取正文；适用于从期刊网站、预印本服务器提取论文 HTML 版本。

---

### 10.9 FineWeb (HuggingFace) — 质量过滤标杆

**GitHub**: 使用 datatrove 工具包 | 数据集: HuggingFace | 15T token

**完整管道（8 步）**：URL 过滤 -> trafilatura 提取 -> fastText 语言检测 (0.65) -> MassiveText 重复过滤 -> C4 质量过滤 -> 自定义过滤 -> MinHash 去重 (5-gram, 112 hashes) -> PII 脱敏

**关键发现**：跨 dump 去重效果不明显，dump 内去重有效。整体通过率仅 5-7%。

**FineWeb-Edu**：Llama-3-70B-Instruct 评分 500k 样本 -> 训练 fastText 分类器 -> 保留 8% (1.3T token)

**可复用代码模式（datatrove）**：

```python
from datatrove.executor import LocalPipelineExecutor
from datatrove.pipeline.readers import WarcReader
from datatrove.pipeline.filters import LanguageFilter, GopherQualityFilter, C4QualityFilter
from datatrove.pipeline.dedup import MinHashDeduplicator
from datatrove.pipeline.writers import JsonlWriter

executor = LocalPipelineExecutor(
    pipeline=[
        WarcReader("s3://commoncrawl/...", glob_pattern="*.warc.gz", compression="gzip"),
        LanguageFilter(language_threshold=0.65, languages=("en",)),
        GopherQualityFilter(min_doc_words=50, max_doc_words=100_000),
        C4QualityFilter(filter_no_terminal_punct=True),
        MinHashDeduplicator(num_hashes=128, jaccard_threshold=0.8),
        JsonlWriter("./output/"),
    ],
    tasks=64, workers=16,
)
executor.run()
```

---

### 10.10 Semantic Scholar / S2ORC — 学术论文专用处理

**GitHub**: https://github.com/allenai/science-parse | API: api.semanticscholar.org

**核心定位**：200M+ 论文，2.4B 引用链接。

**S2ORC 处理管道**（81.1M 论文）：PDF 选择 (移除非论文文档) -> ScienceParse v3 + GROBID v0.5.5 结构提取 -> LaTeX 处理 -> 元数据聚合 -> 质量过滤 -> 引用解析 (380.5M 引用链接)

**数据覆盖**：PDF 28.9M (35.6%), 参考文献 27.6M (34.1%), GROBID 全文 8.1M (10.0%), 出版商摘要 73.4M (90.4%)

**olmOCR (2025)**：AI2 新推出的科学 PDF 转文本工具，用于 OLMo 3 训练数据准备。

---

### 10.11 综合对比：各工具在 RAG 清洗管道中的定位

```
原始 PDF / HTML
    |
    v
[文本提取层] --- MinerU / GROBID / trafilatura / ScienceParse
    |
    v
[基础清洗层] --- Unicode 规范化 / 断词修复 / 连字修复 / 页眉页脚移除
    |              (NeMo Curator: UnicodeReformatter, NewlineNormalizer)
    |              (本项目: TextPostProcessor)
    v
[分块层] ------- Chonkie / LangChain / Docling HybridChunker
    |              (递归/语义/结构感知分块)
    v
[质量过滤层] --- 启发式规则 (Gopher/C4/Dolma)
    |              分类器 (FineWeb fastText / NeMo QualityClassifier)
    |              困惑度 (KenLM, Dolma)
    v
[去重层] ------- datasketch (MinHash LSH) / RapidFuzz (模糊匹配)
    |              NeMo Curator (GPU 加速 MinHash)
    v
[实体/PII层] --- spaCy NER / NeMo PIIRedactor
    |
    v
[Embedding + 向量数据库]
```

---

## 11. 参考资料

1. **MinerU** - opendatalab/MinerU: ★65,626 — PDF→Markdown/JSON，版面分析 https://github.com/opendatalab/MinerU
2. **Unstructured** - Unstructured-IO/unstructured: ★14,808 — 文档 ETL 全流程 https://github.com/Unstructured-IO/unstructured
3. **Nougat** - facebookresearch/nougat: ★9,993 — Meta 神经网络 PDF→Markdown https://github.com/facebookresearch/nougat
4. **GROBID** - kermitt2/grobid — 学术论文结构化解析 https://github.com/kermitt2/grobid
5. **RAPTOR** - parthsarthi03/raptor: ★1,680 — 递归抽象树状检索 https://github.com/parthsarthi03/raptor
6. **datasketch** - ekzhu/datasketch: ★2,900 — MinHash/LSH 近似去重 https://github.com/ekzhu/datasketch
7. **RapidFuzz** - maxbachmann/RapidFuzz: ★3,900 — 快速模糊匹配 https://github.com/maxbachmann/RapidFuzz
8. **dedupe** - dedupeio/dedupe: ★4,500 — 记录链接去重 https://github.com/dedupeio/dedupe
9. **Dolma** - allenai/dolma: ★1,500 — AI2 数据整理 https://github.com/allenai/dolma
10. **spaCy** - explosion/spaCy: ★33,600 — 工业级 NLP https://github.com/explosion/spaCy
11. **NLTK** - nltk/nltk: ★14,600 — 经典 NLP https://github.com/nltk/nltk
12. **langdetect** - Mimino666/langdetect: ★1,888 — 语言检测 https://github.com/Mimino666/langdetect
13. **lingua-py** - pemistahl/lingua-py: ★1,727 — 高精度语言检测 https://github.com/pemistahl/lingua-py
14. **trafilatura** - adbar/trafilatura: ★6,000 — 网页正文提取 https://github.com/adbar/trafilatura
15. **jusText** - miso-belica/jusText: ★818 — 样板文本去除 https://github.com/miso-belica/jusText
16. **Layout-Parser** - Layout-Parser/layout-parser: ★5,700 — 版面分析 https://github.com/Layout-Parser/layout-parser
17. **Chonkie** - chonkie-inc/chonkie: ★409 — RAG 分块库 https://github.com/chonkie-inc/chonkie
18. **pypdf** - py-pdf/pypdf: ★10,000 — PDF 读写 https://github.com/py-pdf/pypdf
19. **pdfplumber** - jsvine/pdfplumber: ★10,000 — PDF 文本提取 https://github.com/jsvine/pdfplumber
20. **PyMuPDF** - pymupdf/PyMuPDF: ★9,800 — 高性能 PDF https://github.com/pymupdf/PyMuPDF
21. **Late Chunking** - Jina AI, 2024 — 先 embedding 再分块 https://jina.ai/news/late-chunking-in-long-context-embedding-models/
22. **FineWeb** - HuggingFace, 2024 — 15T token 质量过滤数据集 https://huggingface.co/datasets/HuggingFaceFW/fineweb
23. **NeMo Curator** - NVIDIA — 企业级文本清洗管道 https://github.com/NVIDIA/NeMo-Curator
24. **RedPajama** - Together AI — 开源 LLM 数据管道 https://github.com/togethercomputer/RedPajama-Data
25. **Lost in the Middle** - Liu et al., 2023 — LLM 位置偏差研究 https://arxiv.org/abs/2307.03172
26. **DPR** - Karpukhin et al., 2020 — 密集段落检索 https://arxiv.org/abs/2004.04906
27. **science-parse** - allenai/science-parse: ★700 — 学术论文解析 https://github.com/allenai/science-parse
28. **Docling** - DS4SD/docling — IBM 文档解析框架 https://github.com/DS4SD/docling
29. **Marker** - VikParuchuri/marker — 深度学习 PDF→Markdown https://github.com/VikParuchuri/marker
30. **anystyle** - inukshuk/anystyle: ★1,200 — 参考文献解析 https://github.com/inukshuk/anystyle

### 第二轮搜索来源: 技术博客与实践指南 (2026-05-30)

31. **Firecrawl Blog** - Best Chunking Strategies for RAG (2026) — 递归 400-512 token 默认推荐; Chroma 上下文退化研究; overlap 争议 https://www.firecrawl.dev/blog/best-chunking-strategies-rag
32. **Weaviate Blog** - Chunking Strategies for RAG — 分块策略导致 9% recall 差距; PDF 先转 Markdown 再分块 https://weaviate.io/blog/chunking-strategies-for-rag
33. **Ailog** - RAG Chunking Strategies 2025 — 512 token + 50 overlap 推荐; 不同内容类型配置 https://app.ailog.fr/en/blog/guides/chunking-strategies
34. **NAACL 2025 Findings** - "Is Semantic Chunking Worth the Computational Cost?" — 固定分块匹配语义分块; 计算成本不被一致收益证明 https://aclanthology.org/2025.findings-naacl.114.pdf
35. **PMC Bioengineering (2025.11)** - Comparative Evaluation of Advanced Chunking — 自适应分块 87% vs 固定 13%; p=0.001 https://pmc.ncbi.nlm.nih.gov/articles/PMC12649634
36. **Applied AI** - PDF Parser Benchmark (800+ 文档) — 学术论文 40-60% 准确率; 领域差异 55+ 百分点 https://www.applied-ai.com/briefings/pdf-parsing-benchmark
37. **NVIDIA Blog** - Approaches to PDF Data Extraction (2025.07) — PDF 解析是 RAG 主要挑战; 表格/图表/信息图是难点 https://developer.nvidia.com/blog/approaches-to-pdf-data-extraction-for-information-retrieval
38. **Firecrawl** - Best PDF Parsers for AI and RAG (2026) — 布局错误级联; 结构保真度比纯文本提取更重要 https://www.firecrawl.dev/blog/best-pdf-parsers
39. **arXiv:2603.25333** - Optimizing Chunking-Method Selection for RAG (2026.03) — Split-then-Merge 递归分块; 过大 chunk 重新切分; 微小 chunk 合并 https://arxiv.org/pdf/2603.25333
40. **ACL 2025** - MAIN-RAG: Multi-Agent Filtering RAG — 自适应过滤提升 2-11%; 多 Agent 共识机制 https://aclanthology.org/2025.acl-long.131
41. **ChunkRAG** - arXiv 2025 — TF-IDF+余弦相似度过滤; 冗余度 >0.9 剔除; 动态阈值 https://arxiv.org/html/2410.19572v5
42. **Substack: RAG Playbook** - Advanced Parsing for PDFs — 脚注/参考文献默认移除; pdfplumber 字体分析; 页眉页脚污染案例 https://lettersfromacoder.substack.com/p/the-rag-playbook-advanced-parsing
43. **DEV.to** - 10 Chunking Strategies That Make or Break RAG (2026) — Parent-child +10-13 点; Agentic chunking 87%; Late chunking +6.5 nDCG https://dev.to/klement_gunndu/10-chunking-strategies-that-make-or-break-your-rag-pipeline-4cng
44. **Digital Applied** - RAG Chunking Strategies 2026 Playbook — 递归 512-token 默认; 语义分块 ~14x 慢; 句子分块匹配语义 <5000 token https://www.digitalapplied.com/blog/rag-chunking-strategies-2026-retrieval-quality-playbook
45. **AI Agents Buzz** - RAG Chunking Strategies Visual Guide (2026) — 300-500 token 基准; overlap 对 dense 检索更有益 https://aiagentsbuzz.com/guides/rag-chunking-strategies
46. **GPT-trainer** - RAG Chunking Strategy — 200-500 token 常见落点; 15% overlap; embedding 模型 token 限制决定 chunk 大小 https://gpt-trainer.com/blog/rag+chunking+strategy
47. **BuildMVPFast** - Chunking Strategies: Semantic vs Fixed-Size vs Recursive — NVIDIA 基准表: 数据集决定最优大小; 语义分块阈值问题 https://www.buildmvpfast.com/blog/chunking-strategies-rag-semantic-fixed-size-recursive-2026
48. **Kapa.ai** - How to Build a RAG Pipeline from Scratch in 2026 — 生产级 RAG 管道; 数据新鲜度; 查询转换; 评估监控 https://www.kapa.ai/blog/how-to-build-a-rag-pipeline-from-scratch-in-2026
49. **Medium (aa779)** - RAG in 2025: 7 Proven Strategies — 元数据评分; 置信度权重; 来源权威性排序 https://medium.com/@aa779/rag-in-2025-7-proven-strategies-to-deploy-retrieval-augmented-generation-at-scale-d1f71dfbfbba
50. **LinkedIn (Naman Goyal)** - Chunk Size Should Scale With Embedding Dimensionality — dim<512: 200-300; dim~768-1024: 300-700; dim>1536: 700-1200 https://www.linkedin.com/posts/naman-goyal1_the-most-overlooked-rag-secret-your-chunk-activity-7397852292621922304-NOYa
51. **OmniDocBench** - CVPR 2025 — 多样化 PDF 解析基准; Pipeline vs VLM 对比 https://openaccess.thecvf.com/content/CVPR2025/papers/Ouyang_OmniDocBench_Benchmarking_Diverse_PDF_Document_Parsing_with_Comprehensive_Annotations_CVPR_2025_paper.pdf
52. **arXiv:2604.12047** - Empirical Evaluation of PDF Parsing and Chunking for Financial PDFs — SPLADE+pdfplumber 最佳; 6 种 chunker 对比; overlap 0%/25%/50% 测试 https://arxiv.org/pdf/2604.12047
53. **Infinity-Parser** - arXiv 2025 — 布局感知强化学习; 多专家策略; 表格解析 86.4 分 https://arxiv.org/html/2506.03197v3
54. **arXiv:2603.18652** - Benchmarking PDF Parsers on Table Extraction (2026) — LaTeX 表格基准; 复杂度分类; 表格匹配管道 https://arxiv.org/html/2603.18652v1
55. **RAGFlow** - From RAG to Context (2025 年终回顾) — "Search" 与 "Retrieve" 解耦; 小 chunk 检索 + 大 chunk 生成 https://ragflow.io/blog/rag-review-2025-from-rag-to-context

### 第三轮搜索来源: 学术论文专项 (2026-05-30)

56. **Liu et al.** "Lost in the Middle: How Language Models Use Long Contexts." TACL 2024. https://cs.stanford.edu/~nfliu/papers/lost-in-the-middle.tacl2023.pdf
57. **Yu et al.** "Lost but not only in the Middle." 2024.
58. **arXiv:2605.27105** "Lost in the Evidence? Reproducing Document Position and Context Size Effects in RAG." 2025. https://arxiv.org/html/2605.27105v1
59. **HuggingFace 2025** "Do RAG Systems Suffer From Positional Bias?" https://huggingface.co/papers/2505.15561
60. **arXiv:2412.10684** "Inference Scaling for Bridging Retrieval and Augmented Generation." 2024. https://arxiv.org/html/2412.10684v1
61. **Günther et al.** "Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models." arXiv:2409.04701, 2024. https://jina.ai/news/late-chunking-in-long-context-embedding-models
62. **Sarthi et al.** "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval." ICML 2024.
63. **Karpukhin et al.** "Dense Passage Retrieval for Open-Domain Question Answering." EMNLP 2020. https://github.com/facebookresearch/DPR
64. **Chroma** "Evaluating Chunking Strategies for Retrieval." https://www.trychroma.com/research/evaluating-chunking
65. **Qu & Bao.** "Is Semantic Chunking Worth the Computational Cost?" Findings of NAACL 2025. arXiv:2410.13070. https://aclanthology.org/2025.findings-naacl.114.pdf
66. **Penedo et al.** "The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale." NeurIPS 2024. https://neurips.cc/virtual/2024/poster/97513
67. **arXiv:2505.05427** "Ultra-FineWeb: Efficient Data Filtering and Verification for High-Quality LLM Training Data." 2025. https://arxiv.org/abs/2505.05427
68. **Seo et al.** "Prior-based Noisy Text Data Filtering: Fast and Strong Alternative For Perplexity." ICLR 2026. https://openreview.net/forum?id=VDjbFzbD2f
69. **text-dedup** github.com/ChenghaoMou/text-dedup — MinHash/SimHash 去重基准
70. **semhash** minishlab.github.io/semhash-blogpost — 语义去重工具 (2025)
71. **arXiv:2410.21169** "Document Parsing Unveiled: Techniques, Challenges, and Prospects for Structured Data Extraction." 2024-2025. https://arxiv.org/html/2410.21169v5
72. **OmniDocBench** CVPR 2025. https://github.com/opendatalab/OmniDocBench
73. **READOC-Zenodo** "A Unified Benchmark for Realistic Document Structured Extraction." ACL Findings 2025. https://aclanthology.org/2025.findings-acl.1128.pdf
74. **Procycons** "PDF Data Extraction Benchmark 2025." https://procycons.com/en/blogs/pdf-data-extraction-benchmark
75. **arXiv:2406.00456** "Mix-of-Granularity: Optimize the Chunking Granularity for RAG." COLING 2025. https://arxiv.org/abs/2406.00456
76. **IEEE COINS 2025** "The Impact of Chunking Strategies on Domain-Specific Information Retrieval in RAG Systems." https://www.computer.org/csdl/proceedings-article/coins/2025/11125724/29o5VB1m1XO
77. **ChunkRAG** arXiv 2025. https://www.emergentmind.com/topics/chunkrag
78. **GROBID Documentation** https://grobid.readthedocs.io/en/latest/Grobid-specialized-processes
79. **Databricks** "Mastering Chunking Strategies for RAG." https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089
