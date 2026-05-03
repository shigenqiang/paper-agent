# Paper Agents 论文流水线Agent详解

> 位置: `src/agents_v2/paper_agents/`

## 一、架构概览

```
paper_agents/
├── __init__.py              # 导出5个Agent
├── base_paper_agent.py     # PaperAgent基类
├── topic_agent.py          # 选题Agent
├── literature_agent.py     # 文献调研Agent
├── outline_agent.py        # 大纲制定Agent
├── draft_writer.py         # 初稿撰写Agent
└── digest_agent.py         # 学术资讯快报Agent
```

## 二、Agent清单 (5个)

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| `TopicAgent` | 选题生成与精炼 | 用户研究领域描述 | 候选课题列表 |
| `LiteratureAgent` | 文献检索与综述 | 研究课题 | 文献列表+综述报告 |
| `OutlineAgent` | 大纲制定 | 参考文献 + 课题 | 论文大纲 |
| `DraftWriterAgent` | 分节撰写 | 大纲 + 参考文献 | 论文初稿 |
| `DigestReportAgent` | 学术资讯快报 | 关键词/日期范围 | 快报报告 |

## 三、BasePaperAgent 基类

```python
class PaperAgentBase(EnglishFirstMixin, BaseAgent):
    """Paper Agent基类 - 继承BaseAgent"""

    def __init__(self, name: str, llm_config: Optional[LLMConfig], description: str, system_prompt: str):
        super().__init__(name, llm_config, description, system_prompt)

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """执行Agent主逻辑"""
        ...

    async def _process_text_english(self, text: str) -> str:
        """EnglishFirstMixin实现：用LLM处理英文文本"""
        return await self._llm_call(text)
```

特性: `EnglishFirstMixin` - 研究主题和章节信息先翻译为英文再处理，提升LLM理解质量

## 四、TopicAgent 选题Agent

```python
class TopicAgent(PaperAgentBase):
    """选题Agent - 生成和精炼研究课题"""

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """
        输入: { "task_description": "用户研究兴趣描述" }
        输出: {
            "selected_topic": {...},
            "alternative_topics": [...],
            "domain_analysis": {...},
            "all_candidates": [...]
        }
        """
```

## 五、LiteratureAgent 文献调研Agent

```python
class LiteratureAgent(PaperAgentBase):
    """文献调研Agent - 检索和综述文献"""

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """
        输入: { "topic": "研究主题", "research_question": "具体问题" }
        输出: {
            "papers": [...],
            "paper_analyses": [...],
            "research_gaps": [...],
            "search_queries": [...],
            "total_found": int,
            "total_analyzed": int
        }
        """

    async def _generate_search_queries(self, topic: str) -> List[str]:
        """生成8-12个搜索查询"""

    async def _multi_engine_search(self, queries: List[str]) -> List[Paper]:
        """多引擎并行搜索"""

    async def _rank_papers(self, papers: List[Paper]) -> List[Paper]:
        """质量筛选与排序"""

    async def _deep_read(self, papers: List[Paper], top_k: int = 20) -> List[dict]:
        """深度阅读Top N论文"""

    async def _identify_gaps(self, analyses: List[dict]) -> List[str]:
        """识别研究空白"""
```

## 六、OutlineAgent 大纲制定Agent

```python
class OutlineAgent(EnglishFirstMixin, PaperAgentBase):
    """大纲制定Agent - 设计论文结构"""

    async def _design_structure(self, thesis: str) -> Dict[str, Any]:
        """设计章节结构（英文优先模式）"""

    async def _plan_chapters(
        self,
        structure: Dict[str, Any],
        literature: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """规划各章节内容"""

    async def _identify_key_arguments(
        self,
        thesis: str,
        literature: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """确定关键论点"""
```

**EnglishFirst特性**:
- 研究主题先翻译为英文，提升LLM理解质量
- 章节信息也进行英文处理
- 通过 `EnglishFirstMixin` 实现

## 七、DraftWriterAgent 初稿撰写Agent

```python
class DraftWriterAgent(PaperAgentBase):
    """初稿撰写Agent - 逐章节撰写论文"""

    async def _write_introduction(self, chapter: dict, context: dict) -> str:
        """撰写引言章节"""

    async def _write_literature_review(self, chapter: dict, context: dict) -> str:
        """撰写文献综述章节"""

    async def _write_methodology(self, chapter: dict, context: dict) -> str:
        """撰写方法论章节"""

    async def _write_results(self, chapter: dict, context: dict) -> str:
        """撰写结果章节"""

    async def _write_discussion(self, chapter: dict, context: dict) -> str:
        """撰写讨论章节"""

    async def _write_conclusion(self, chapter: dict, context: dict) -> str:
        """撰写结论章节"""
```

## 八、DigestReportAgent 学术资讯快报Agent

```python
class DigestReportAgent(PaperAgentBase):
    """学术资讯快报Agent"""

    # 报告类型
    DIGEST_TYPES = {
        "daily": (500, 800, "今日热点 + 代表性论文5篇"),
        "weekly": (1000, 1500, "本周概览 + 主题聚类 + 趋势分析"),
        "monthly": (2000, 3000, "月度概览 + 深度分析 + 前沿展望")
    }

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentOutput:
        """
        输入: { "papers": [...], "keywords": [...], "digest_type": "daily|weekly|monthly" }
        输出: { "report": str, "theme_groups": [...], "paper_count": int }
        """
```

## 九、流水线协作

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Paper Agent Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TopicAgent ─────────────────────────────────────────────────┐ │
│      │                                                      │   │
│      ▼                                                      │   │
│  LiteratureAgent ──────────────────────────────────────────┼──▼──┤
│      │                                                      │     │
│      ▼                                                      │     │
│  OutlineAgent ─────────────────────────────────────────────┼─────┤
│      │                                                      │     │
│      ▼                                                      │     │
│  DraftWriterAgent ─────────────────────────────────────────┼─────┤
│      │                                                      │     │
│      ▼                                                      │     │
│  (传递给writing模块进行润色)                                │     │
└─────────────────────────────────────────────────────────────────┘
```

---

**更新日期**: 2026-05-03
**基于代码**: `src/agents_v2/paper_agents/`