# 07-记忆系统 (Memory System)

本目录收录关于 Paper Agent 记忆系统的三份文档，从调研到实现的完整链条。

---

## 文档列表

| 文档 | 类型 | 说明 |
|------|------|------|
| `长期记忆写入短期记忆机制调研报告.md` | 调研报告 | 25次搜索，55+参考来源，完整的行业调研 |
| `记忆系统与数据存储融合方案.md` | 方案设计 | v3.0 精简版，PostgreSQL + Qdrant + Neo4j 融合架构 |
| `长期记忆写入短期记忆机制改进方案.md` | 改进实施 | v1.0，代码改进具体方案 |

---

## 文档关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  调研报告 (Research)                                                        │
│  ├── 来源: 25次搜索，覆盖 Mem0/Letta/MemoryOS/HippoRAG 等                  │
│  ├── 内容: LTM→STM 触发机制、重要性评分、遗忘曲线、主流框架对比              │
│  └── 结论: 为方案设计提供理论基础                                            │
│                                                                             │
│         ↓                                                                   │
│                                                                             │
│  方案设计 (Design)                                                          │
│  ├── 来源: 基于调研结论设计                                                  │
│  ├── 内容: 存储架构设计 (PostgreSQL/Qdrant/Neo4j)、流转机制、五级重要性      │
│  └── 结论: 定义"怎么做"                                                     │
│                                                                             │
│         ↓                                                                   │
│                                                                             │
│  改进实施 (Implementation)                                                  │
│  ├── 来源: 方案设计的代码实现                                                │
│  ├── 内容: context_injector.py 改进、MemoryNode 导入修复、遗忘曲线实现      │
│  └── 结论: 落地到代码                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 内容概要

### 1. 调研报告

**主题**: AI Agent 长期记忆(LTM)何时写入短期记忆(STM)的机制

**核心发现**:
- **触发机制**: 用户提问涉及历史、会话冷启动、Context 快满时、Agent 主动判断
- **重要性评分**: `score = relevance×0.3 + explicit×0.4 + recency×0.2 + access_boost×0.1`
- **遗忘曲线**: `retention = importance × e^(-t/S)` (Ebbinghaus 模型)
- **主流框架**: Mem0 (向量+图谱)、Letta (层级存储)、MemoryOS (EMNLP 2025 Oral)

### 2. 方案设计

**主题**: Agent 记忆系统与数据持久化融合方案

**核心设计**:
- **存储**: PostgreSQL (sessions/profiles) + Qdrant (向量) + Neo4j (图)
- **流转**: STG→SESSION (消息数≥30) → LONG_TERM (重要性≥0.7) → FORGOTTEN (retention<0.1)
- **五级重要性**: CRITICAL (1.0) / HIGH (0.8) / MEDIUM (0.5) / LOW (0.3) / FORGOTTEN (<0.1)

### 3. 改进实施

**主题**: 原系统问题修复 + 新功能实现

**改进项**:
- 修复 MemoryNode 导入 (使用 UnifiedMemoryManager 替换不存在的 EnhancedMemorySystem)
- 智能触发判断 (HISTORY_KEYWORDS 匹配)
- 遗忘曲线时间衰减 (_calculate_retention_score)
- 重要性阈值过滤 (importance_threshold = 0.3)

---

## 核心公式汇总

### 保留分数公式

```
retention = importance × e^(-t/S)

参数:
- importance: 初始重要性 (0.0-1.0)
- t: 距上次访问的时间（秒）
- S: 记忆强度参数
  - CRITICAL: ∞
  - HIGH: 604,800 (7天)
  - MEDIUM: 86,400 (1天)
  - LOW: 3,600 (1小时)
```

### 重要性评分公式

```
score = relevance×0.3 + explicit×0.4 + recency×0.2 + access_boost×0.1

其中:
- access_boost = min(access_count / 10, 1.0)
```

### SM-2 间隔复习公式

```
I(1) = 1
I(2) = 6
I(n) = I(n-1) × EF (n > 2)

EF' = EF + 0.1 - (5-q) × (0.08 + (5-q) × 0.02)
```

---

## 相关代码文件

| 文件 | 作用 |
|------|------|
| `src/agents_v2/core/context_injector.py` | 智能上下文注入器（已改进） |
| `src/agents_v2/langgraph_workflow/nodes/memory.py` | 记忆节点（已修复导入） |
| `src/agents_v2/memory/unified.py` | 统一记忆管理器 |
| `src/agents_v2/memory/types.py` | MemoryEntry（含遗忘曲线定义） |
| `src/agents_v2/memory/services.py` | ForgettingController（遗忘控制器） |

---

**维护者**: Paper Agent Team
**最后更新**: 2026-05-02