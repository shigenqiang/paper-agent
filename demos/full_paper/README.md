# 全链路论文生成模块 (full_paper)

将 `run_full_paper.py` 拆分为独立的小模块，每个模块输出文本与全链路一致。

## 目录结构

```
full_paper/
├── __init__.py
├── runner.py              # 主运行器，协调全流程
├── test_runner.py         # 测试脚本
├── phases/
│   ├── __init__.py
│   ├── diagnostic.py     # 诊断阶段 - 并行诊断Agent
│   ├── topic.py          # 选题阶段 - TopicAgent
│   ├── literature.py     # 文献阶段 - LiteratureAgent
│   ├── methodology.py    # 方法阶段 - 问题导向Agent
│   ├── writing.py        # 写作阶段 - OutlineAgent + DraftWriterAgent
│   └── polish.py         # 润色阶段 - 多Agent协同润色
└── utils/
    ├── __init__.py
    ├── config.py         # PhaseConfig 配置管理
    └── output.py         # PhaseOutput & OutputManager 输出管理
```

## 使用方式

### 1. Make 命令（推荐）

```bash
# 全链路论文生成（模块化版本）
make paper-full TOPIC='人工智能在教育领域的应用'

# 测试单个阶段
make paper-phase PHASE=diagnostic
make paper-phase PHASE=topic
make paper-phase PHASE=literature
make paper-phase PHASE=methodology
make paper-phase PHASE=writing
make paper-phase PHASE=polish

# 测试完整流程
make paper-test
```

### 2. Python 直接运行

```bash
# 全链路运行
python demos/full_paper/runner.py "人工智能在教育领域的应用"

# 测试单个阶段
python demos/full_paper/test_runner.py diagnostic
python demos/full_paper/test_runner.py topic
python demos/full_paper/test_runner.py --full
```

### 3. 作为模块导入

```python
import asyncio
from demos.full_paper import FullPaperRunner

runner = FullPaperRunner()
result = await runner.run("人工智能在教育领域的应用")
```

#### 单独使用某个阶段

```python
import asyncio
from demos.full_paper.phases import TopicPhase
from demos.full_paper.utils.config import PhaseConfig

config = PhaseConfig(phase_name="topic")
phase = TopicPhase(config)
output = await phase.run("人工智能在教育领域的应用")

print(f"状态: {output.status}")
print(f"质量: {output.quality_score:.2f}")
print(f"输出: {output.text}")
```

## 测试命令与输入

```bash
# 测试单个阶段
make paper-phase PHASE=diagnostic
make paper-phase PHASE=topic
make paper-phase PHASE=literature
make paper-phase PHASE=methodology
make paper-phase PHASE=writing
make paper-phase PHASE=polish

# 测试完整流程
make paper-test
```

### 测试输入说明

| 阶段 | 测试输入 |
|------|---------|
| diagnostic | `"人工智能在教育领域的应用"` |
| topic | `"人工智能在教育领域的应用"` |
| literature | `"人工智能在教育领域的应用"` |
| methodology | `"人工智能在教育领域的应用"` |
| writing | `"人工智能在教育领域的应用"` |
| polish | `"这是一段测试文本用于润色"` |
| full pipeline | `"人工智能在教育领域的应用"` |

### 自定义测试输入

如需自定义测试主题，可修改 `test_runner.py` 中的 `topic` 变量：

```python
# test_runner.py 第 41 行
topic = "你的自定义研究主题"
```

或直接运行 Python 代码：

```python
import asyncio
from demos.full_paper.phases import TopicPhase
from demos.full_paper.utils.config import PhaseConfig

config = PhaseConfig(phase_name="topic")
phase = TopicPhase(config)
output = await phase.run("你的自定义研究主题")
```

### 各阶段详细输入输出

#### diagnostic - 诊断阶段
```python
# 输入: user_request (用户请求/研究主题)
user_request = "我想研究人工智能在教育领域的应用"
output = await diagnostic_phase.run(user_request)

# output.result 传递给下一阶段:
{
    "issues": [...],           # 发现的问题列表
    "recommendations": [...],  # 改进建议
    "agents_run": [...],       # 运行的Agent列表
    "success_count": 3
}
```

#### topic - 选题阶段
```python
# 输入: user_request (用户请求/研究主题)
user_request = "我想研究人工智能在教育领域的应用"
output = await topic_phase.run(user_request)

# output.result 传递给下一阶段 (literature):
{
    "selected_topic": {
        "title": "基于多模态数据融合的学习困难预警系统研究",
        "description": "通过融合学习行为数据、作业表现...",
        "scope": "",
        "innovation": "",
        "feasibility": 7.4,
        "scores": {
            "literature_adequacy": 8.0,
            "method_feasibility": 7.0,
            "novelty": 7.0,
            "time_reasonableness": 7.0,
            "resource_accessibility": 8.0
        },
        "potential_methods": [...],
        "expected_contribution": "..."
    },
    "alternative_topics": [...],      # 备选主题
    "domain_analysis": {...},         # 领域分析
    "all_candidates": [...]          # 所有候选主题
}
# 同时 context["thesis_statement"] = selected_topic["title"]
```

#### literature - 文献阶段
```python
# 输入: topic (研究主题字符串或 selected_topic 对象)
topic = "基于多模态数据融合的学习困难预警系统研究"
output = await literature_phase.run(topic)

# output.result 传递给下一阶段:
{
    "papers": [...],               # 论文列表
    "paper_analyses": [...],       # 深度分析的论文
    "research_gaps": [...],        # 研究空白
    "search_queries": [...],       # 搜索查询
    "total_found": 50,             # 总文献数
    "total_analyzed": 20            # 分析的文献数
}
```

#### methodology - 方法阶段
```python
# 输入: topic, literature_result (来自 literature 阶段)
output = await methodology_phase.run(topic, literature_result)

# output.result 传递给下一阶段:
{
    "methodology": {...},           # 方法论详情
    "research_design": "...",       # 研究设计
    "feasibility": {...},          # 可行性评估
    "expected_outcomes": [...]     # 预期成果
}
```

#### writing - 写作阶段
```python
# 输入: topic, literature_result
output = await writing_phase.run(topic, literature_result)

# output.result 传递给下一阶段 (polish):
{
    "outline": {...},              # 论文大纲
    "draft": {...},                # 初稿详情
    "thesis_statement": "..."      # 论文陈述
}
# output.text = full_draft (完整论文文本)
```

#### polish - 润色阶段
```python
# 输入: text (待润色文本), language, polish_level
text = "这是论文初稿..."
output = await polish_phase.run(text=text, language="zh", polish_level="medium")

# output.result:
{
    "original_length": 5000,
    "polished_length": 5200,
    "iterations": 3,
    "fallback": false
}
# output.text = polished_text (润色后的完整文本)
```

## 输出格式

每个阶段返回 `PhaseOutput` 对象：

```python
@dataclass
class PhaseOutput:
    phase_name: str        # 阶段名称
    success: bool         # 是否成功
    status: str           # pending/running/completed/failed
    text: str             # 主要输出文本
    result: Dict          # 完整结果字典
    quality_score: float  # 质量评分 0-1
    quality_level: str     # excellent/good/acceptable/poor
    execution_time: float  # 执行时间(秒)
    error: str            # 错误信息(如果有)
```

## 与原版全链路的区别

| 特性 | 原版 `run_full_paper.py` | 模块化版本 |
|------|-------------------------|-----------|
| 文件组织 | 单文件 | 多文件模块 |
| 阶段输出 | 统一result | 每个阶段独立 PhaseOutput |
| 文本输出 | 内嵌在result中 | 独立的 `text` 字段 |
| 测试方式 | 需要完整运行 | 可单独测试每个阶段 |
| 调试便利性 | 较低 | 较高 |
