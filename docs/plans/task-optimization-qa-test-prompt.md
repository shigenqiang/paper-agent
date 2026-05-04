# PaperAgent 性能优化与QA系统测试任务提示词

## 任务概述

完成以下两个核心任务，**必须全部完成**：

1. **QA系统测试与完善**（优先）- 使用Neo4j（Docker容器）进行测试直到QA系统功能完整
2. **论文生成流程性能优化** - 缩减论文写作的运行时间，采用并行等技术

**强制要求**：如果不完成上述所有要求，不允许停止，直到完成为止。

---

## 任务0：QA系统测试与完善（优先执行）

### 0.1 QA系统质量指标

QA系统必须达到以下指标才算合格：

| 指标类别 | 具体指标 | 合格标准 | 测试方法 |
|---------|---------|---------|---------|
| **准确性** | 答案正确率 | ≥85% | 与标准答案对比 |
| **相关性** | 答案与问题相关度 | ≥0.8 | RAGAs Answer Relevance |
| **忠实度** | 答案基于context程度 | ≥0.8 | RAGAs Faithfulness |
| **上下文利用** | 上下文精确度 | ≥0.75 | RAGAs Context Precision |
| **幻觉检测** | 幻觉风险识别率 | ≥90% | 植入虚构内容测试 |
| **置信度校准** | 置信度准确性 | ±0.15 | 与实际正确率对比 |
| **多跳推理** | 多跳问题回答正确率 | ≥75% | 多跳测试集 |
| **响应时间** | P95延迟 | <5秒 | 性能监控 |
| **知识图谱** | 图谱检索召回率 | ≥80% | KG相关问题测试 |

### 0.2 Neo4j环境搭建

```bash
# 启动Neo4j容器
docker run -d \
  --name paper-agent-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:latest

# 检查容器状态
docker ps
```

### 0.3 QA系统架构理解

基于 `src/agents_v2/paper_search/base_qa_agent.py` 和 `demos/academic_qa/demo_academic_qa.py`：

```
用户问题 → 问题类型判断 → 路由决策
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
              knowledge_base paper_search llm_enhanced
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
                  向量检索   知识图谱    关键词检索
                    ↓         ↓         ↓
                    └─────────┬─────────┘
                              ↓
                         答案合成
```

### 0.4 测试用例设计

| 测试类型 | 测试用例 | 预期结果 | 评估指标 |
|---------|---------|---------|---------|
| 基础查询 | "什么是Transformer？" | 准确回答，使用context | Answer Relevance ≥0.8 |
| 专业问题 | "BERT和GPT的区别是什么？" | 引用相关论文 | Faithfulness ≥0.8 |
| 前沿探索 | "2024年大语言模型最新进展？" | 搜索最新论文 | Context Precision ≥0.75 |
| 多跳推理 | "Transformer的注意力机制如何工作？" | 展示推理链 | 多跳正确率 ≥75% |
| 幻觉检测 | "量子计算在医学影像中的应用"（虚构） | 识别幻觉风险 | 识别率 ≥90% |
| 置信度校准 | 随机问题 | 显示合理的置信度 | 误差 ±0.15 |
| KG检索 | "Attention机制在哪些模型中使用？" | 返回实体关系 | 召回率 ≥80% |
| 综合评估 | 10个问题综合测试 | 平均分达标 | 平均≥85% |

### 0.5 功能测试步骤

#### 步骤1：基础QA功能测试
```python
from src.agents_v2.academic_qa import AcademicQASystem

system = AcademicQASystem(...)
result = await system.ask(
    query="你的测试问题",
    contexts=[...],
    mode="strict"
)
```

#### 步骤2：知识图谱集成测试
```python
from src.agents_v2.academic_qa import AcademicQAKGIntegration

kg_qa = AcademicQAKGIntegration(...)
result = await kg_qa.ask(
    query="多跳问题",
    enable_kg_retrieval=True
)
```

#### 步骤3：评估指标测试
```python
# 测试RAGAs指标
result = await system.ask(query, contexts, mode="strict")
print(f"Faithfulness: {result.ragas_metrics.get('faithfulness', 0):.2f}")
print(f"Answer Relevance: {result.ragas_metrics.get('answer_relevance', 0):.2f}")
print(f"Context Precision: {result.ragas_metrics.get('context_precision', 0):.2f}")
```

### 0.6 质量不达标时的调研方案

**如果QA系统质量不达标**，立即执行调研：

1. **调研内容**：
   - 搜索关键词：`academic QA agent design`, `RAG evaluation metrics`, `knowledge graph QA system`, `multi-hop reasoning QA`
   - 搜索频率：至少40次，覆盖官方文档≥5次、学术论文≥8次、开源项目≥8次、技术博客≥10次

2. **调研方向**：
   - 学术QA系统的最佳实践
   - RAGAs评估指标的正确使用方式
   - 知识图谱与向量检索的结合方案
   - 多跳推理的实现方法
   - 幻觉检测的先进技术

3. **方案实施**：
   - 根据调研结果改进QA系统
   - 重新测试并验证
   - 迭代直到达标

### 0.7 QA系统必须完成的功能清单

| 功能 | 状态 | 测试结果 |
|-----|------|---------|
| 基础问答 | 待测试 | - |
| 问题类型判断 | 待测试 | - |
| 路由决策 | 待测试 | - |
| 向量检索 | 待测试 | - |
| 知识图谱检索 | 待测试 | - |
| 关键词检索 | 待测试 | - |
| 答案合成 | 待测试 | - |
| RAGAs评估 | 待测试 | - |
| 幻觉检测 | 待测试 | - |
| 置信度校准 | 待测试 | - |
| 多跳推理 | 待测试 | - |
| Neo4j集成 | 待测试 | - |

**必须完成所有功能测试并达标才能结束任务0。**

---

## 任务1：论文生成流程性能优化

### 1.0 状态隔离测试（优先探索）

#### 1.0.1 当前状态设计分析

当前实现：
```
状态通过 dict 在节点间传递
每次调用 run() 创建新状态
不会与之前的请求混在一起
```

问题探索：
- 是否真的完全隔离？
- 并发请求时状态是否会泄露？
- 多轮对话时状态是否正确保持？

#### 1.0.2 隔离测试设计

测试并发和多会话场景下的状态隔离：

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 测试1：并发请求状态隔离
async def test_concurrent_isolation():
    """测试并发请求时状态是否隔离"""
    results = []
    errors = []

    async def run_request(request_id, topic):
        try:
            # 每个请求使用不同的state
            state = PaperAgentState()  # 独立状态实例
            result = await paper_agent.run(
                {"topic": topic, "state_id": request_id},
                config={"configurable": {"thread_id": str(request_id)}}
            )
            return (request_id, result)
        except Exception as e:
            return (request_id, None, str(e))

    # 并发执行10个不同请求
    tasks = [
        run_request(i, f"topic_{i}")
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)

    # 验证：每个请求的结果是否只包含自己的数据
    # 没有出现topic混淆、状态泄露
    for req_id, result in results:
        if result and f"topic_{req_id}" not in str(result):
            print(f"❌ 请求{req_id}状态泄露")

# 测试2：多轮对话状态保持
async def test_multiturn_state():
    """测试多轮对话中状态是否正确保持"""
    session_id = "test_session_1"
    state = PaperAgentState()

    # 第1轮：输入topic
    result1 = await agent.run(
        {"action": "set_topic", "topic": "深度学习"},
        config={"configurable": {"thread_id": session_id}}
    )

    # 第2轮：继续对话，检查状态是否包含第1轮的信息
    result2 = await agent.run(
        {"action": "get_topic"},
        config={"configurable": {"thread_id": session_id}}
    )

    # 验证：result2应该能获取到第1轮设置的topic
    if result2.get("topic") != "深度学习":
        print(f"❌ 状态隔离失败：第2轮无法获取第1轮状态")
```

#### 1.0.3 隔离判断标准

**需要增强隔离的情况**：
- 并发请求出现状态混淆
- 多轮对话状态丢失
- 出现非预期的状态共享

**当前隔离足够的情况**：
- 每个请求的状态完全独立
- 多轮对话状态正确保持
- 无状态泄露

#### 1.0.4 隔离增强方案（如需要）

如果测试发现隔离问题，实施以下方案：

**方案A：LangGraph Memory Checkpoint**
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph.compile(checkpointer=checkpointer)

# 每个请求使用不同的thread_id
config = {"configurable": {"thread_id": str(uuid.uuid4())}}
```

**方案B：独立State实例**
```python
class PaperAgentState:
    """每个会话独立的State实例"""
    def __init__(self, session_id):
        self.session_id = session_id
        self.data = {}
        self.history = []

    def create_new():
        return PaperAgentState(session_id=uuid.uuid4())
```

#### 1.0.5 测试记录模板

```markdown
### 状态隔离测试结果

| 测试场景 | 隔离前 | 隔离后 | 结论 |
|---------|-------|-------|------|
| 并发请求10个 | X个成功 | X个成功 | 需/不需增强 |
| 多轮对话3轮 | 状态丢失 | 状态保持 | 需/不需增强 |
| 内存占用 | XMB | XMB | ±X% |
```

### 1.1 测试当前性能

运行 `test_perf.py` 和 `paper_pipeline.py` 获取基准数据：

```bash
python test_perf.py
python paper_pipeline.py "深度学习医学图像诊断"
```

记录：各阶段耗时、总运行时间、内存使用、瓶颈环节

### 1.2 分析瓶颈

1. **串行执行问题** - 哪些阶段可以并行？
2. **API调用延迟** - LLM调用是否为主要耗时？
3. **I/O阻塞** - 是否有大量同步操作？
4. **重复计算** - 是否有可缓存的结果？

### 1.3 优化方案

#### 方案A：阶段并行化
- `topic_agent` 和 `literature_agent` 并行启动
- `outline_generator` 不等待literature完成
- 使用 `asyncio.gather()` 并行执行

#### 方案B：LLM调用优化
- 批量处理
- 流式输出
- 模型降级

#### 方案C：缓存机制
- 缓存文献搜索结果
- 缓存大纲生成结果

#### 方案D：异步I/O

### 1.4 调研与实现

如果性能提升不满意：
- 搜索：`asyncio parallel LLM optimization`, `paper generation performance tuning`
- 至少30次搜索
- 验证并实现

### 1.5 性能评估标准

- 总运行时间减少 **30%-50%**
- 论文质量不下降

---

## 任务2：性能与测试记录

### 2.1 记录模板

```markdown
## 测试记录 - [日期]

### QA系统测试
| 测试用例 | 状态 | 响应时间 | Faithfulness | Answer Relevance | Context Precision |
|---------|------|---------|-------------|------------------|-------------------|
| 基础查询 | 通过/失败 | Xms | X.XX | X.XX | X.XX |
| ... | ... | ... | ... | ... | ... |

### 性能测试
| 阶段 | 优化前 | 优化后 | 提升率 |
|-----|-------|-------|--------|
| 总计 | X.Xs | X.Xs | XX% |

### 发现的问题与解决
1. 问题：... 解决方案：...
```

### 2.2 输出位置

- `docs/test_results/qa_system_test_report.md` - QA系统测试报告
- `docs/test_results/performance_optimization_report.md` - 性能优化报告

---

## 执行流程

**步骤0（优先）**：QA系统测试
1. 启动Neo4j容器
2. 执行所有QA功能测试
3. 检查指标是否达标
4. 如不达标，调研并改进
5. 重复直到达标

**步骤1**：性能优化
1. 运行测试获取基准
2. 分析瓶颈
3. 实现优化
4. 验证性能提升

**步骤2**：记录与提交
1. 保存所有测试结果
2. 提交到GitHub

---

## 上下文溢出处理方案

### 问题场景

在论文生成过程中可能出现：
- 上下文长度超出LLM限制
- 多个文献信息无法一次传递
- 会话历史过长导致内存压力

### 解决方案：临时文件存储

当上下文即将超出限制时，创建临时文件夹和文件保存重要信息：

```python
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

class ContextOverflowHandler:
    """上下文溢出处理：使用临时文件存储"""

    def __init__(self, base_dir=None):
        # 创建临时工作目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_dir = tempfile.mkdtemp(prefix=f"paper_agent_{timestamp}_")
        self.base_dir = base_dir or self.temp_dir

    def save_state(self, state_data, label="state"):
        """保存状态到临时文件"""
        file_path = os.path.join(self.base_dir, f"{label}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
        return file_path

    def save_papers(self, papers, label="papers"):
        """保存文献列表到临时文件"""
        file_path = os.path.join(self.base_dir, f"{label}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        return file_path

    def save_outline(self, outline, label="outline"):
        """保存大纲到临时文件"""
        file_path = os.path.join(self.base_dir, f"{label}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(outline, f, ensure_ascii=False, indent=2)
        return file_path

    def save_draft_section(self, section_text, section_name):
        """保存草稿段落到临时文件"""
        file_path = os.path.join(self.base_dir, f"draft_{section_name}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(section_text)
        return file_path

    def load_state(self, label="state"):
        """从临时文件加载状态"""
        file_path = os.path.join(self.base_dir, f"{label}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def cleanup(self):
        """清理临时目录"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
```

### 使用场景

```python
# 场景1：文献收集超限
async def collect_papers_with_overflow_handling():
    handler = ContextOverflowHandler()

    papers = []
    for i, paper in enumerate(all_papers):
        papers.append(paper)

        # 如果papers数量超过阈值，保存到临时文件
        if len(papers) >= 50:
            handler.save_papers(papers, label=f"papers_batch_{i//50}")
            papers = []

    # 保存最后一批
    if papers:
        handler.save_papers(papers, label="papers_final")

# 场景2：长对话历史保存
async def long_conversation_handling():
    handler = ContextOverflowHandler()

    history = []
    for turn in conversation_turns:
        history.append(turn)

        # 如果历史超过100条，保存到临时文件
        if len(history) >= 100:
            handler.save_state({"history": history}, label="history_batch_1")
            history = []

# 场景3：分块处理长论文
async def process_long_paper():
    handler = ContextOverflowHandler()

    sections = ["摘要", "引言", "方法", "实验", "结论", "参考文献"]
    for section in sections:
        section_text = await generate_section(section)
        handler.save_draft_section(section_text, section)

    # 最后合并所有section
    full_paper = merge_sections(handler.load_all_sections())
```

### 溢出检测与自动处理

```python
# 检测上下文即将超限
def should_overflow(context, max_tokens=100000):
    """检测是否需要溢出处理"""
    current_tokens = estimate_tokens(context)
    return current_tokens > max_tokens * 0.8  # 80%阈值

# 自动溢出处理
async def auto_overflow_handler(agent, context):
    if should_overflow(context):
        handler = ContextOverflowHandler()

        # 保存当前状态
        handler.save_state(context, label="overflow_context")

        # 记录溢出点
        overflow_marker = {
            "type": "overflow",
            "temp_dir": handler.temp_dir,
            "overflow_at": "literature_agent",
            "token_count": estimate_tokens(context)
        }
        handler.save_state(overflow_marker, label="overflow_marker")

        # 返回溢出标记，告知后续处理
        return {"overflow": True, "handler": handler, "marker": overflow_marker}

    return {"overflow": False}
```

### 临时文件结构

```
/tmp/paper_agent_20260503_143022/
├── state.json                    # 当前状态
├── papers_batch_0.json          # 文献批次1
├── papers_batch_1.json          # 文献批次2
├── outline.json                 # 论文大纲
├── draft_摘要.txt               # 摘要草稿
├── draft_引言.txt               # 引言草稿
├── draft_方法.txt               # 方法草稿
├── draft_实验.txt               # 实验草稿
├── draft_结论.txt               # 结论草稿
├── draft_参考文献.txt           # 参考文献草稿
├── overflow_marker.json         # 溢出标记
└── history_batch_0.json         # 历史记录批次
```

### 恢复处理

```python
# 从溢出中恢复
async def recover_from_overflow(marker):
    handler = ContextOverflowHandler(base_dir=marker["temp_dir"])

    # 加载所有保存的数据
    state = handler.load_state("state")
    papers = load_all_batches(handler, "papers")
    outline = handler.load_state("outline")
    sections = load_all_sections(handler, "draft")

    # 恢复上下文
    restored_context = {
        "state": state,
        "papers": papers,
        "outline": outline,
        "sections": sections,
        "overflow_recovered": True
    }

    return restored_context
```

### 注意事项

1. **自动清理**：任务完成后自动删除临时目录
2. **命名规范**：使用时间戳确保唯一性
3. **错误处理**：如果临时文件读取失败，记录日志并尝试恢复
4. **磁盘空间**：监控磁盘空间，避免写入过多临时文件
5. **安全删除**：确保临时文件不包含敏感信息

---

## 最终输出要求

### 论文生成流程

- **中间过程**：可以有流程信息（日志、进度等）
- **最终输出**：只保留干净的论文内容，无任何流程痕迹

### QA系统

- **测试过程**：显示所有测试指标
- **最终报告**：包含完整的评估结果

---

## 验收标准（必须全部完成）

| 任务 | 验收条件 | 状态 |
|-----|---------|------|
| QA系统 | 所有功能测试通过，指标达标 | 待验证 |
| QA系统 | Neo4j集成正常工作 | 待验证 |
| QA系统 | 知识图谱检索召回率≥80% | 待验证 |
| QA系统 | 幻觉检测识别率≥90% | 待验证 |
| QA系统 | 多跳推理正确率≥75% | 待验证 |
| QA系统 | RAGAs指标全部达标 | 待验证 |
| 论文优化 | 运行时间减少40%以上 | 待验证 |
| 论文输出 | 最终只输出纯净论文 | 待验证 |
| 测试记录 | 所有报告已保存 | 待验证 |
| 代码提交 | 已提交到GitHub | 待验证 |

**重要**：上述所有验收条件必须全部完成才能结束任务。如果某一验收条件未达标，必须继续优化直到达标，**不允许停止**。