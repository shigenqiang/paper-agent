# API文档

> 文档版本: v1.0
> 更新日期: 2026-04-26

---

## 一、快速开始

### 1.1 安装依赖

```bash
pip install -r requirements.txt
```

### 1.2 配置API密钥

在项目根目录创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key_here
# 可选：设置代理
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890
```

### 1.3 基本使用

```python
import asyncio
from src.agents_v2.paper_agents import TopicAgent
from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

# 配置LLM
llm_config = LLMConfig(
    provider="openai",
    model_name="minimax",  # 使用MiniMax模型
    temperature=0.7
)

# 创建Agent并执行
async def main():
    agent = TopicAgent(llm_config)
    result = await agent.execute({
        "user_request": "机器学习在医疗诊断中的应用"
    })
    print(f"Success: {result.success}")
    print(f"Quality: {result.quality_score}")
    print(f"Topic: {result.result}")

asyncio.run(main())
```

---

## 二、Agent类型

### 2.1 PaperAgent (Pipeline型)

用于从零写完整论文，串起完整流程。

**基类**: `PaperAgentBase`

```python
from src.agents_v2.paper_agents.base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
```

**核心方法**:
- `execute(input_data, context) -> AgentOutput`: 执行Agent任务
- `add_tool(tool)`: 添加工具
- `get_tool_schemas() -> List[Dict]`: 获取工具schema

### 2.2 ProblemAgent (问题导向型)

用于修复论文局部缺陷。

**基类**: `ProblemAgentBase`

```python
from src.agents_v2.problem_oriented.base_problem_agent import ProblemAgentBase
```

**核心方法**:
- `diagnose(input_data, context) -> AgentOutput`: 诊断问题
- `fix(input_data, context) -> AgentOutput`: 修复问题

### 2.3 WritingAgent (写作型)

用于论文写作全流程。

**基类**: `BaseWritingAgent`

```python
from src.agents_v2.writing.base_writing_agent import BaseWritingAgent
```

---

## 三、核心Agent API

### 3.1 TopicAgent

主题选择与研究问题凝练。

```python
from src.agents_v2.paper_agents import TopicAgent

agent = TopicAgent(llm_config=None)  # 使用默认配置

result = await agent.execute({
    "user_request": "你的研究兴趣或方向"
})
```

**输入**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_request | string | 是 | 用户的研究请求 |

**输出** (AgentOutput):
```python
{
    "success": True,
    "result": {
        "selected_topic": {
            "title": "...",
            "description": "...",
            "scope": "...",
            "potential_methods": [...],
            "expected_contribution": "...",
            "scores": {...},
            "overall_score": 0.8,
            "risk_factors": [...]
        },
        "alternative_topics": [...],
        "domain_analysis": {...},
        "all_candidates": [...]
    },
    "agent_name": "topic_agent",
    "quality_score": 0.8
}
```

---

### 3.2 LiteratureAgent

文献搜索、筛选与综述。

```python
from src.agents_v2.paper_agents import LiteratureAgent

agent = LiteratureAgent(llm_config)
result = await agent.execute({
    "topic": "研究主题"
}, context={"research_question": "具体问题"})
```

**输入**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic | string | 是 | 研究主题 |
| research_question | string | 否 | 具体研究问题 |

**输出**:
```python
{
    "success": True,
    "result": {
        "papers": [...],           # 排序后的论文列表
        "paper_analyses": [...],    # 深度分析结果
        "research_gaps": [...],     # 识别的研究空白
        "search_queries": [...],   # 使用的搜索查询
        "total_found": 50,         # 总找到论文数
        "total_analyzed": 20       # 深度分析论文数
    },
    "quality_score": 0.7
}
```

---

### 3.3 ThesisAgent

研究Thesis的凝练与优化。

```python
from src.agents_v2.paper_agents import ThesisAgent

agent = ThesisAgent(llm_config)
result = await agent.execute({
    "topic": "研究主题",
    "literature_result": {...}  # LiteratureAgent的结果
})
```

---

### 3.4 OutlineAgent

论文大纲制定。

```python
from src.agents_v2.paper_agents import OutlineAgent

agent = OutlineAgent(llm_config)
result = await agent.execute({
    "topic": "研究主题",
    "thesis_statement": "Thesis陈述",
    "literature_summary": {...}
})
```

---

### 3.5 DraftWriterAgent

分节撰写论文初稿。

```python
from src.agents_v2.paper_agents import DraftWriterAgent

agent = DraftWriterAgent(llm_config)
result = await agent.execute({
    "topic": "研究主题",
    "outline": {...},           # OutlineAgent的结果
    "literature_summary": {...}  # 文献总结
})
```

---

## 四、问题导向Agent API

### 4.1 TopicRefinerAgent

选题精炼与可行性评估。

```python
from src.agents_v2.problem_oriented import TopicRefinerAgent

agent = TopicRefinerAgent(llm_config)
result = await agent.diagnose({
    "topic_idea": "初步想法",
    "research_field": "研究领域"
})
```

---

### 4.2 DiscussionDeepenerAgent

深化讨论部分。

```python
from src.agents_v2.problem_oriented import DiscussionDeepenerAgent

agent = DiscussionDeepenerAgent(llm_config)
result = await agent.fix({
    "current_discussion": "当前讨论内容",
    "literature_context": {...}  # 文献上下文
})
```

---

### 4.3 LanguagePolisherAgent

语言润色。

```python
from src.agents_v2.problem_oriented import LanguagePolisherAgent

agent = LanguagePolisherAgent(llm_config)
result = await agent.fix({
    "text": "需要润色的文本",
    "language": "en"  # 或 "zh"
})
```

---

## 五、Writing Agent API

### 5.1 DraftGeneratorAgent

生成完整论文初稿。

```python
from src.agents_v2.writing import DraftGeneratorAgent

agent = DraftGeneratorAgent(llm_config)
result = await agent.execute({
    "title": "论文标题",
    "outline": {...},  # 大纲
    "requirements": ["创新性", "实用性"]
})
```

---

### 5.2 ProposalGeneratorAgent

生成开题报告。

```python
from src.agents_v2.writing import ProposalGeneratorAgent

agent = ProposalGeneratorAgent(llm_config)
result = await agent.execute({
    "research_topic": "研究主题",
    "background": "研究背景"
})
```

---

## 六、错误处理

### 6.1 错误类型

```python
from src.agents_v2.unified.error_handler import ErrorType

ErrorType.LLM_FAILURE           # LLM调用失败
ErrorType.PARSING_FAILURE       # JSON解析失败
ErrorType.EXTERNAL_API_FAILURE  # 外部API失败
ErrorType.VALIDATION_FAILURE   # 验证失败
ErrorType.SYSTEM_ERROR         # 系统错误
```

### 6.2 降级处理

所有Agent都有fallback处理：

```python
from src.agents_v2.unified.error_handler import FallbackHandler

handler = FallbackHandler()
fallback = handler.get_fallback("topic", context, error)
```

---

## 七、日志配置

### 7.1 智能日志

```python
from src.agents_v2.unified.error_handler import log_error_with_context

# 有fallback恢复的错误 -> warning级别
log_error_with_context(logger, error, "context", recovered=True)

# 无fallback的错误 -> error级别
log_error_with_context(logger, error, "context", recovered=False)
```

### 7.2 日志级别

| 级别 | 含义 |
|------|------|
| WARNING | LLM/解析/外部API失败，有fallback恢复 |
| ERROR | 真正需要关注的错误 |

---

## 八、配置参数

### 8.1 LLMConfig

```python
from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

config = LLMConfig(
    provider="openai",        # openai 或 anthropic
    model_name="minimax",     # 模型名称
    temperature=0.7,          # 温度参数
    max_tokens=4096,         # 最大token数
    api_key=None,            # API密钥（从环境变量读取）
    base_url=None            # API基础URL
)
```

### 8.2 质量阈值

```python
QUALITY_THRESHOLDS = {
    "diagnostic": 6.0,
    "topic": 7.0,
    "literature": 7.0,
    "methodology": 7.0,
    "writing": 7.0,
    "polish": 8.0
}
```

---

## 九、测试

### 9.1 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_error_handler.py -v

# 运行特定测试类
python -m pytest tests/test_agents.py::TestTopicAgent -v
```

### 9.2 测试覆盖

| 模块 | 测试文件 | 测试数 |
|------|----------|--------|
| 错误处理 | test_error_handler.py | 12 |
| 核心Agent | test_agents.py | 12 |
| **总计** | | **24** |

---

**文档版本**: v1.0
**创建日期**: 2026-04-26
**最后更新**: 2026-04-26
