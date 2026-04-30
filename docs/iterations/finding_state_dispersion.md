# 发现：状态分散问题

**日期**：2026-04-30

---

## 1. 问题描述

项目中存在多个状态模型，职责不清：

1. **PaperState** (unified/state_model.py)
2. **AgentContext** (models/state.py)
3. **AgentState** (models/state.py)

---

## 2. 具体问题

### 字段重复
- task_id 在多个类中都有
- status 在多个类中都有

### 无事务性
- 状态更新没有原子性保证
- 并发场景下可能出问题

### 无历史追踪
- 无法追溯状态变更历史
- 调试困难

---

## 3. 改进建议

统一为 TypedDict：



---

## 4. 参考

- LangGraph StateGraph 使用统一状态
- CrewAI 使用 Agent 属性存储状态
