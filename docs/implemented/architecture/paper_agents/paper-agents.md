# Paper Agents 论文流水线Agent详解

> 位置: `src/agents_v2/paper_agents/`

## 一、架构概览

```
paper_agents/
├── __init__.py              # 导出5个Agent
├── base_paper_agent.py     # PaperAgent基类 (11KB)
├── topic_agent.py          # 选题Agent (19KB)
├── literature_agent.py    # 文献调研Agent (12KB)
├── outline_agent.py        # 大纲制定Agent (11KB)
├── draft_writer.py        # 初稿撰写Agent (12KB)
├── digest_agent.py        # 论文摘要Agent (20KB)
└── deprecated/            # 已废弃模块
    ├── annotations.py
    ├── editor_agent.py
    ├── reviewer_agent.py
    ├── thesis_agent.py
    ├── versioning.py
    └── writing_pipeline.py
```

## 二、Agent清单

| Agent | 大小 | 职责 | 输入 | 输出 |
|-------|------|------|------|------|
| `TopicAgent` | 19KB | 选题生成与精炼 | 用户研究领域 | 候选课题列表 |
| `LiteratureAgent` | 12KB | 文献检索与综述 | 研究课题 | 参考文献列表 |
| `OutlineAgent` | 11KB | 大纲制定 | 参考文献 + 课题 | 论文大纲 |
| `DraftWriterAgent` | 12KB | 初稿撰写 | 大纲 + 参考文献 | 论文初稿 |
| `DigestAgent` | 20KB | 摘要生成 | 论文全文 | 摘要 |

## 三、BasePaperAgent 基类

```python
class BasePaperAgent(BaseAgent):
    """PaperAgent基类"""

    def __init__(self, llm_config: LLMConfig, agent_name: str):
        super().__init__(llm_config, agent_name)
        self.max_retries = 3
        self.timeout = 120

    async def _execute_core(self, user_input: str, context: dict = None) -> AgentOutput:
        """核心执行逻辑"""
        ...
```

## 四、TopicAgent 选题Agent

```python
class TopicAgent(BasePaperAgent):
    """选题Agent - 生成和精炼研究课题"""

    PROMPT_TEMPLATE = """你是一个学术研究顾问。
根据用户的研究领域和兴趣，帮助生成具有创新性的研究课题。

要求:
1. 课题应具有明确的研究问题
2. 课题应具有可操作性
3. 课题应具有学术价值

请输出JSON格式:
{
    "topics": [
        {"title": "课题标题", "description": "课题描述", "novelty": "创新点"},
        ...
    ]
}"""
```

## 五、LiteratureAgent 文献调研Agent

```python
class LiteratureAgent(BasePaperAgent):
    """文献调研Agent - 检索和综述文献"""

    async def search_and_review(
        self,
        topic: str,
        max_papers: int = 20
    ) -> LiteratureReviewResult:
        """
        1. 多源检索相关文献
        2. 筛选高质量论文
        3. 生成综述报告
        """
        # 并行搜索
        search_results = await self._parallel_search(topic, max_papers)

        # LLM筛选
        selected = await self._llm_filter(search_results, top_k=10)

        # 生成综述
        review = await self._generate_review(selected)

        return LiteratureReviewResult(
            papers=selected,
            review=review,
            citation_graph=self._build_citation_graph(selected)
        )
```

## 六、OutlineAgent 大纲制定Agent

```python
class OutlineAgent(BasePaperAgent):
    """大纲制定Agent - 基于文献生成论文大纲"""

    def generate_outline(
        self,
        topic: str,
        references: List[dict]
    ) -> Outline:
        """
        1. 分析参考文献的研究内容
        2. 提取关键研究点和方法
        3. 生成层级化大纲
        """
        outline = Outline(
            title=topic,
            chapters=[
                Chapter(
                    title="Introduction",
                    sections=["背景", "研究问题", "贡献点"]
                ),
                Chapter(
                    title="Related Work",
                    sections=["文献分类", "现有方法", "局限性"]
                ),
                Chapter(
                    title="Method",
                    sections=["问题定义", "方法论", "技术细节"]
                ),
                Chapter(
                    title="Experiment",
                    sections=["实验设置", "结果分析", "对比实验"]
                ),
                Chapter(
                    title="Conclusion",
                    sections=["工作总结", "未来工作"]
                )
            ]
        )
        return outline
```

## 七、DraftWriterAgent 初稿撰写Agent

```python
class DraftWriterAgent(BasePaperAgent):
    """初稿撰写Agent - 逐章节撰写论文"""

    async def write_draft(
        self,
        outline: Outline,
        references: List[dict]
    ) -> Draft:
        """
        1. 按章节顺序生成内容
        2. 引用相关论文
        3. 保持上下文连贯性
        """
        sections = []
        for chapter in outline.chapters:
            section_content = await self._write_chapter(
                chapter=chapter,
                context={"outline": outline, "references": references}
            )
            sections.append(section_content)

        return Draft(
            title=outline.title,
            sections=sections,
            citations=self._extract_citations(sections)
        )
```

## 八、流水线协作

```
┌─────────────────────────────────────────────────────────────────┐
│                    Paper Agent Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TopicAgent ─────────────────────────────────────────────────┐   │
│      │                                                      │   │
│      ▼                                                      │   │
│  LiteratureAgent ──────────────────────────────────────────┼───┤   │
│      │                                                      │   │
│      ▼                                                      │   │
│  OutlineAgent ─────────────────────────────────────────────┼───┤   │
│      │                                                      │   │
│      ▼                                                      │   │
│  DraftWriterAgent ─────────────────────────────────────────┼───┤   │
│      │                                                      │   │
│      ▼                                                      │   │
│  ReviewerAgent (外部) ──────────────────────────────────────┼───┤   │
│      │                                                      │   │
│      ▼                                                      │   │
│  PolisherAgent (外部)                                        │   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/paper_agents/`
