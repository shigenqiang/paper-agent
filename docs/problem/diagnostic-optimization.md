# Diagnostic 阶段优化问题记录

> 更新日期: 2026-05-09

## 问题列表

### 问题1: Diagnostic 结果未传递到后续节点 [已修复]

**问题描述**: `LiteratureMapperAgent.diagnose()` 的结果需要传递到 Literature 节点

**修复文件**: `src/agents_v2/langgraph_workflow/nodes/diagnostic.py`

**修复内容**:
- 移除对不存在变量 `literature_result` 的引用
- 直接从 `diag_result["papers"]` 获取论文列表

---

### 问题2: Literature Embedding 预计算 [已修复]

**问题描述**:
- LiteratureMapperAgent 在 Diagnostic 阶段搜索论文
- LiteratureAgent 在后续阶段再次搜索并计算 embedding
- 重复工作，可预计算后复用

**修复文件**:
1. `src/agents_v2/problem_oriented/literature_mapper.py`
2. `src/agents_v2/paper_agents/literature_agent.py`

**修复内容**:

1. 在 `literature_mapper.py` 中添加 `_embed_papers()` 方法:
```python
async def _embed_papers(self, papers: List[Dict[str, Any]], topic: str = "") -> List[Dict[str, Any]]:
    """后台预计算论文embedding，供后续LiteratureAgent复用"""
    # 使用本地embedding模型计算
    # 限制20篇，避免耗时过长
```

2. 在 `diagnose()` 中启动后台embedding预计算:
```python
asyncio.create_task(self._embed_papers(papers, topic))
```

3. 在 `literature_agent.py` 的 `process_paper()` 中复用预计算的embedding:
```python
# 检查是否已有预计算的embedding
existing_embedding = paper.get("embedding")
if existing_embedding and topic_embedding:
    similarity = self._cosine_similarity(topic_embedding, existing_embedding)
    return paper, similarity
```

**效果**: LiteratureAgent 收到 diagnostic_papers 后直接使用预计算结果，避免重复计算

---

### 问题3: Outline LLM 失败后备问题 [已修复]

**问题描述**:
- 原本 LLM 失败时使用 `FALLBACK_STRUCTURE` 静默降级
- 根据 CLAUDE.md 要求，必须使用 LLM，禁止模板回退

**修复文件**: `src/agents_v2/paper_agents/outline_agent.py`

**修复内容**:
1. `execute()` 方法: LLM 失败时抛出 `ValueError` 而非返回 AgentOutput
2. `_design_structure()` 方法: 失败时抛出错误而非返回 fallback

```python
# execute() 中
raise ValueError(f"OutlineAgent LLM 调用失败: {e}. 不支持模板回退.") from None

# _design_structure() 中
raise ValueError(f"OutlineAgent._design_structure LLM 调用失败: {e}. 不支持规则后备.") from None
```

---

### 问题4: Polish 节点 [已确认存在]

**确认**: `src/agents_v2/langgraph_workflow/nodes/polish.py` 存在，LangGraph 工作流已包含 `polish` 节点

---

### 问题5: 思考过程块清理 [已修复]

**问题描述**: 最终输出的论文包含 `<think>` 思考过程块

**修复文件**:
1. `demos/full_paper/runner.py`
2. `src/agents_v2/unified/master_supervisor.py`

**修复内容**:
- 在 runner.py 结果编译阶段添加清理逻辑，移除 `<think>` 等干扰信息
- 在 `_clean_final_paper()` 中也添加了思考块清理

```python
# runner.py 中
final_paper = re.sub(r'<think>[\s\S]*?', '', final_paper)
final_paper = re.sub(r'```json\s*.*?\s*```', '', final_paper, flags=re.DOTALL)
final_paper = re.sub(r'【[^】]*】', '', final_paper)
final_paper = re.sub(r'\[[A-Z_]+(?:\|[^\]]+)?\]', '', final_paper)
```

---

## 优先级

| 优先级 | 问题 | 影响 | 状态 |
|--------|------|------|------|
| P1 | Diagnostic 结果传递 | 避免重复分析，提升性能 | ✅ 已修复 |
| P2 | Embedding 预计算 | 减少 Literature 阶段时间 | ✅ 已修复 |
| P1 | Outline LLM 失败 | 违反 CLAUDE.md 要求 | ✅ 已修复 |
| P2 | Polish 节点缺失 | 论文质量无法保证 | ✅ 已确认存在 |
| P1 | 思考过程块清理 | 论文包含干扰信息 | ✅ 已修复 |

---

## 验证方法

```bash
# 测试完整论文生成流程
PYTHONPATH=. PYTHONIOENCODING=utf-8 D:/anaconda/envs/paper-agent-test/python.exe demos/full_paper/runner.py "深度学习医学图像诊断" --paper-only

# 预期结果
# - 最终论文文件中不包含 <think> 思考过程块
# - Diagnostic 阶段结果能传递给后续节点
# - Literature 阶段直接使用预计算的 embedding
# - Outline 失败时抛出明确错误而非降级
# - 最终输出经过 Polish 阶段
```

---

## 已修复问题总结 (2026-05-09)

| 问题 | 文件 | 修复内容 |
|------|------|----------|
| Diagnostic 结果传递 | diagnostic.py | 从 diag_result 获取论文列表 |
| Embedding 预计算 | literature_mapper.py, literature_agent.py | 后台预计算 + 复用 |
| Outline LLM 后备 | outline_agent.py | 移除规则后备，抛出错误 |
| Polish 节点 | - | 确认存在 |
| 思考块清理 | runner.py, master_supervisor.py | 添加清理逻辑 |