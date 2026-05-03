# Writing 论文写作模块详解

> 位置: `src/agents_v2/writing/`

## 一、架构概览

```
writing/
├── __init__.py              # 导出所有Agent和工具
├── base_writing_agent.py    # WritingAgent基类
├── literature_review.py     # 文献综述Agent
├── outline_generator.py     # 大纲生成Agent
├── draft_generator.py      # 全文初稿Agent
├── report_refiner.py        # 报告精炼Agent
├── proposal_generator.py    # 开题报告Agent
├── reference_processor.py  # 参考文献处理Agent
├── smart_reviser.py         # 智能改稿Agent + LanguagePolisherAgent
├── reflection_engine.py     # 反思引擎
├── answer_quality_checker.py # 答案质量检查
├── streaming_generator.py  # 流式生成
├── generation_optimizer.py  # 生成优化
├── citation_generator.py    # 引用生成器
└── diff_manager.py          # 文本对比与补丁
```

## 二、Agent清单 (9个)

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| `LiteratureReviewAgent` | 文献综述生成 | topic, papers | 综述报告 |
| `OutlineGeneratorAgent` | 大纲生成 | topic, literature | 结构化大纲 |
| `DraftGeneratorAgent` | 全文初稿 | topic, outline, literature | 完整论文 |
| `ReportRefinerAgent` | 报告精炼(多轮) | draft, focus_areas | 精炼后报告 |
| `ReviewerAgent` | 评审反馈 | draft | 评审意见 |
| `ProposalGeneratorAgent` | 开题报告 | topic, literature | 开题报告 |
| `ReferenceProcessorAgent` | 参考文献处理 | raw_references | 格式化引用 |
| `SmartReviserAgent` | 智能改稿 | original_text, feedback | 修订后文本 |
| `LanguagePolisherAgent` | 语言润色 | text, language | 润色后文本 |

## 三、WritingAgentBase 基类

```python
class WritingAgentBase(BaseAgent):
    """写作Agent基类"""

    def __init__(self, name: str, llm_config: Optional[LLMConfig], description: str, system_prompt: str):
        super().__init__(name, llm_config, description, system_prompt)

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> WritingOutput:
        """执行写作任务"""
        ...
```

## 四、SmartReviserAgent 智能改稿

```python
class SmartReviserAgent(WritingAgentBase):
    """
    智能改稿Agent

    职责：
    - 解析导师/审稿人意见
    - 针对性修改文本
    - 保持修改一致性
    """

    async def _parse_feedback(self, feedback: str) -> List[Dict[str, Any]]:
        """解析导师意见"""

    async def _categorize_feedback(
        self,
        feedback_items: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """将意见分类 - content/structure/language/citation/logic/format"""

    async def _apply_revisions(
        self,
        original_text: str,
        categorized: Dict[str, List[Dict[str, Any]]],
        highlight_changes: bool
    ) -> str:
        """应用修改"""
```

## 五、LanguagePolisherAgent 语言润色

```python
class LanguagePolisherAgent(WritingAgentBase):
    """
    语言润色Agent

    诊断维度：
    - GRAMMAR_ERROR：语法错误
    - SPELLING_ERROR：拼写错误
    - COLLOQUIALISM：口语化表达
    - SUBJECTIVITY：主观性过强
    - VERBOSITY：冗余表达
    - INCONSISTENCY：术语不一致
    - LOGIC_BREAK：逻辑断裂
    - FORMAT_ERROR：格式错误
    """

    SYSTEM_PROMPT_TEMPLATE = """## 角色
你是一位专业的学术语言诊断与润色专家"""

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        输入: { "text": str, "language": "zh|en", "polish_level": "light|medium|heavy" }
        输出: {
            "polished_text": str,
            "diagnosis": {...},
            "grammar_issues": int,
            "style_issues": int
        }
        """
```

## 六、ReportRefinerAgent 报告精炼

```python
class ReportRefinerAgent(WritingAgentBase):
    """报告精炼Agent - 多轮迭代精炼"""

    async def _refine_report(
        self,
        report: str,
        focus_areas: List[str],
        max_iterations: int
    ) -> str:
        """多轮精炼"""
        for i in range(max_iterations):
            diagnosis = await self._diagnose(report, focus_areas)
            if diagnosis.quality_score >= self.quality_threshold:
                break
            report = await self._apply_improvements(report, diagnosis)
        return report
```

## 七、ReflectionEngine 反思引擎

```python
class ReflectionEngine:
    """SciSage式多层反思器"""

    class ReflectionLevel(Enum):
        SINGLE = "single"           # 单点反思
        OUTLINE = "outline"        # 大纲层反思
        SECTION = "section"        # 章节层反思
        DOCUMENT = "document"      # 全文层反思

    async def reflect(
        self,
        content: str,
        level: ReflectionLevel = ReflectionLevel.SINGLE
    ) -> ReflectionResult:
        """执行反思"""
```

## 八、WritingTools 工具集

| 工具 | 职责 |
|------|------|
| `ReflectionEngine` | 多层反思 |
| `AnswerQualityChecker` | 质量检查 |
| `StreamingGenerator` | 流式生成 |
| `GenerationOptimizer` | 生成优化 |
| `CitationGenerator` | 引用生成 |
| `DiffManager` | 文本对比 |

---

**更新日期**: 2026-05-03
**基于代码**: `src/agents_v2/writing/`