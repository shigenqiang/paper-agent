# Tools 工具模块详解

> 位置: `src/agents_v2/tools/`

## 一、架构概览

```
tools/
├── __init__.py
├── buildin_tools.py           # 内置工具
├── chart_generator.py         # 图表生成
├── citation_extractor.py      # 引用提取
├── citation_graph.py          # 引用图
├── citation_mapper.py         # 引用映射
├── contribution_extractor.py  # 贡献提取
├── doi_utils.py              # DOI工具
├── dynamic_registry.py        # 动态注册表
├── enhanced_chart_generator.py # 增强图表生成
├── enhanced_pdf_parser.py     # 增强PDF解析
├── extended_search.py         # 扩展搜索
├── figure_classifier.py       # 图表分类
├── formula_processor.py       # 公式处理
├── layout_analyzer.py         # 布局分析
├── marker_pdf_parser.py       # Marker PDF解析
├── metadata_parser.py          # 元数据解析
├── paper_tools.py            # 论文工具
├── pdf_parser.py             # PDF解析
├── plagiarism_checker.py     # 查重检测
├── reference_parser.py        # 参考文献解析
├── registry.py               # 工具注册表
├── section_parser.py          # 章节解析
├── sentence_splitter.py       # 句子分割
├── table_detector.py         # 表格检测
├── text_cleaner.py           # 文本清洗
├── text_segmenter.py         # 文本分块
├── tool_coordinator.py       # 工具协调器
├── tool_spec.py              # 工具规格
├── tool_version.py           # 工具版本
└── zotero_client.py          # Zotero客户端
```

## 二、工具分类

### 2.1 PDF解析工具

| 工具 | 大小 | 说明 |
|------|------|------|
| `pdf_parser.py` | 27KB | 基础PDF解析 |
| `enhanced_pdf_parser.py` | 25KB | 增强PDF解析 |
| `marker_pdf_parser.py` | 18KB | Marker高精度解析 |

```python
class PDFParser:
    """PDF解析器"""

    def parse(self, pdf_path: str) -> ParsedPDF:
        """解析PDF，返回结构化内容"""
        pages = self._extract_pages(pdf_path)
        text = self._extract_text(pages)
        tables = self._extract_tables(pages)
        figures = self._extract_figures(pages)
        formulas = self._extract_formulas(pages)

        return ParsedPDF(
            text=text,
            tables=tables,
            figures=figures,
            formulas=formulas,
            metadata=self._extract_metadata(pdf_path)
        )
```

### 2.2 图表处理工具

| 工具 | 大小 | 说明 |
|------|------|------|
| `chart_generator.py` | 21KB | 图表生成 |
| `enhanced_chart_generator.py` | 27KB | 增强图表生成 |
| `figure_classifier.py` | 8KB | 图表分类 |
| `table_detector.py` | 12KB | 表格检测 |

```python
class ChartGenerator:
    """学术图表生成器"""

    def generate_chart(
        self,
        data: dict,
        chart_type: str,  # bar, line, scatter, heatmap
        title: str,
        x_label: str,
        y_label: str
    ) -> bytes:
        """生成图表图片"""
        ...
```

### 2.3 引用处理工具

| 工具 | 大小 | 说明 |
|------|------|------|
| `citation_extractor.py` | 1KB | 引用提取 |
| `citation_graph.py` | 7KB | 引用图构建 |
| `citation_mapper.py` | 15KB | 引用映射 |
| `reference_parser.py` | 4KB | 参考文献解析 |
| `doi_utils.py` | 12KB | DOI工具 |

```python
class CitationExtractor:
    """引用提取器"""

    def extract_citations(self, paper_text: str) -> List[Citation]:
        """从论文文本中提取引用"""
        # 匹配 [1], [2,3], [1-5] 等格式
        pattern = r'\[(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\]'
        matches = re.findall(pattern, paper_text)
        return [self._parse_citation(m) for m in matches]
```

### 2.4 文本处理工具

| 工具 | 大小 | 说明 |
|------|------|------|
| `text_cleaner.py` | 4KB | 文本清洗 |
| `text_segmenter.py` | 8KB | 文本分块 |
| `sentence_splitter.py` | 5KB | 句子分割 |
| `section_parser.py` | 3KB | 章节解析 |

```python
class TextCleaner:
    """文本清洗器"""

    def clean(self, text: str) -> str:
        """清洗文本"""
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        # 标准化空白字符
        text = re.sub(r'\s+', ' ', text)
        # 修复UTF-8转义
        text = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: bytes.fromhex(m.group(1)).decode('utf-8'), text)
        return text.strip()
```

### 2.5 公式处理工具

```python
class FormulaProcessor:
    """学术公式处理器"""

    def extract_formulas(self, pdf_page) -> List[Formula]:
        """提取PDF中的公式"""
        ...

    def latex_to_image(self, latex: str) -> bytes:
        """LaTeX公式渲染为图片"""
        ...
```

### 2.6 查重工具

```python
class PlagiarismChecker:
    """查重检测器"""

    def check(
        self,
        text: str,
        threshold: float = 0.8
    ) -> PlagiarismReport:
        """检测文本相似度"""
        # 1. 生成文本指纹
        fingerprint = self._generate_fingerprint(text)
        # 2. 与已有文本比对
        matches = self.db.search_similar(fingerprint, threshold)
        # 3. 生成报告
        return PlagiarismReport(
            originality_score=1.0 - max(matches),
            matches=matches
        )
```

## 三、工具注册表

```python
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, name: str, tool: ToolSpec):
        """注册工具"""
        self._tools[name] = tool

    def get(self, name: str) -> Optional[ToolSpec]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())

    def get_tools_by_category(self, category: str) -> List[ToolSpec]:
        """按类别获取工具"""
        return [t for t in self._tools.values() if t.category == category]
```

## 四、工具协调器

```python
class ToolCoordinator:
    """工具协调器"""

    def __init__(self, llm_config: LLMConfig):
        self.registry = ToolRegistry()
        self.executor = ToolExecutor()

    async def execute_task(
        self,
        task: str,
        context: dict
    ) -> ExecutionResult:
        """
        1. LLM分析任务需要的工具
        2. 按依赖顺序执行工具链
        3. 合并结果
        """
        # 分析所需工具
        required_tools = self._analyze_requirements(task)

        # 执行工具链
        results = []
        for tool_name in required_tools:
            tool = self.registry.get(tool_name)
            result = await self.executor.execute(tool, context)
            results.append(result)
            context.update(result)

        return self._merge_results(results)
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/tools/`