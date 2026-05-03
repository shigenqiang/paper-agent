# Intent Router 意图路由

> 位置: `src/agents_v2/unified/intent_router.py`
> 版本：v1.0
> 更新日期：2026-05-03

## 概述

意图路由模块，用于识别和路由用户意图到对应处理模块。

---

## IntentType 枚举 (11 种意图)

```python
class IntentType(Enum):
    # 文献类
    LITERATURE_SEARCH = "literature_search"      # 搜索论文
    LITERATURE_REVIEW = "literature_review"      # 文献综述
    LITERATURE_TRACKING = "literature_tracking"  # 文献追踪
    LITERATURE_SUMMARY = "literature_summary"    # 文献对比

    # 写作类
    TOPIC_SELECT = "topic_select"                # 选题
    THESIS_FORMULATE = "thesis_formulate"        # Thesis 凝练
    OUTLINE_GENERATE = "outline_generate"        # 大纲生成
    DRAFT_WRITE = "draft_write"                  # 初稿撰写
    PAPER_REVISION = "paper_revision"           # 智能改稿
    REPORT_REFINE = "report_refine"             # 报告精炼

    # 流水线
    FULL_PAPER = "full_paper"                   # 完整论文
    DIAGNOSTIC = "diagnostic"                   # 诊断
```

---

## 路由流程 (6 步)

```
用户输入: "帮我找几篇关于transformer注意力机制的论文"
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 关键词匹配 (快速路径, 无 LLM 调用)                      │
│                                                                  │
│  INTENT_KEYWORDS = {                                             │
│    "找": LITERATURE_SEARCH,                                      │
│    "论文": LITERATURE_SEARCH,                                    │
│    "搜索": LITERATURE_SEARCH,                                    │
│    ...                                                           │
│  }                                                               │
│                                                                  │
│  扫描用户输入 → 命中关键词 → 快速识别意图                          │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: LLM 辅助识别 (复杂/多意图)                               │
│                                                                  │
│  langchain ChatOpenAI.ainvoke([                                  │
│    SystemMessage("你是一个意图识别专家..."),                       │
│    HumanMessage("分析以下用户请求的所有意图: {user_input}")       │
│  ])                                                               │
│                                                                  │
│  → 返回 JSON: {intents: [...], reasoning: "..."}                 │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 合并结果 + 按优先级排序                                  │
│                                                                  │
│  关键词结果: [LITERATURE_SEARCH]                                 │
│  LLM 结果: [LITERATURE_SEARCH, LITERATURE_SUMMARY]              │
│  合并去重后 → 按 priority 排序                                    │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 置信度校准                                              │
│                                                                  │
│  keyword_match=True AND llm_match=True → +0.15                  │
│  base_confidence=0.92 → calibrated=1.0 (cap at 1.0)            │
│                                                                  │
│  confidence_level:                                              │
│    HIGH ≥ 0.8                                                   │
│    MEDIUM: 0.5-0.8                                              │
│    LOW < 0.5                                                    │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: 意图冲突检测                                            │
│                                                                  │
│  检查是否存在冲突意图对 (如 SEARCH vs SUMMARY 可能有冲突)        │
│  不在冲突对列表中 → 无冲突                                       │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: 查询 intent_agent_map → 输出路由结果                    │
│                                                                  │
│  LITERATURE_SEARCH → agent="literature"                         │
│  LITERATURE_SUMMARY → agent="literature_review"                │
│  mode = "collaboration" (有次要意图时)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 路由结果结构

```python
{
    "primary_intent": "literature_search",      # 主意图
    "confidence": 1.0,                           # 置信度
    "confidence_level": "high",                 # HIGH/MEDIUM/LOW
    "is_multi_intent": True,                     # 是否多意图
    "secondary_intents": ["literature_summary"], # 次要意图
    "suggested_agents": ["literature", "literature_review"],  # 建议 Agent
    "mode": "collaboration",                    # single/collaboration/pipeline
    "requires_collaboration": True
}
```

---

## 意图 → Agent 映射表

| IntentType | Agent | 模块 |
|-----------|-------|------|
| LITERATURE_SEARCH | PaperSearchAgent | search |
| LITERATURE_REVIEW | LiteratureAgent | paper_agents |
| TOPIC_SELECT | TopicAgent | paper_agents |
| THESIS_FORMULATE | ThesisAgent | paper_agents |
| OUTLINE_GENERATE | OutlineAgent | paper_agents |
| DRAFT_WRITE | DraftWriterAgent | paper_agents |
| PAPER_REVISION | SmartReviserAgent | writing |
| FULL_PAPER | MasterSupervisor (5 Agent) | unified |
| DIAGNOSTIC | 3 Agent 协作 | problem_oriented |

---

## 关键代码片段

### 意图关键词匹配

```python
INTENT_KEYWORDS = {
    "找": IntentType.LITERATURE_SEARCH,
    "搜索": IntentType.LITERATURE_SEARCH,
    "论文": IntentType.LITERATURE_SEARCH,
    "选题": IntentType.TOPIC_SELECT,
    "大纲": IntentType.OUTLINE_GENERATE,
    "写作": IntentType.DRAFT_WRITE,
    "修改": IntentType.PAPER_REVISION,
    # ...
}
```

### LLM 辅助识别

```python
def _llm_assist_identify(self, user_input: str) -> List[Dict]:
    prompt = f"""分析以下用户请求的所有意图:
    用户输入: {user_input}

    返回格式:
    {{
        "intents": [
            {{"intent": "类型", "confidence": 0.0-1.0}},
            ...
        ],
        "reasoning": "分析理由"
    }}"""
```

---

## 置信度计算

```python
def _calibrate_confidence(
    keyword_match: bool,
    llm_confidence: float,
    intent_count: int
) -> float:
    confidence = llm_confidence

    # 双重验证加分
    if keyword_match:
        confidence += 0.15

    # 多意图略微降低主意图置信度
    if intent_count > 1:
        confidence *= 0.9

    # 上限封顶
    return min(confidence, 1.0)
```

---

## 三级级联路由架构（推荐）

```
用户输入
  → Layer 1: 关键词快速匹配（<1ms, acc 60-75%）
    → 置信度不足 ↓
  → Layer 2: 语义向量路由（10-50ms, acc 80-92%）
    → 置信度不足 ↓
  → Layer 3: LLM 深度分类（500ms-2s, acc 90-96%）
    → Layer 4: 降级兜底（默认意图 / 人工确认）
```

### 推荐工具

| 工具 | 用途 | 推荐度 |
|------|------|-------|
| Semantic Router | Layer 2 语义路由 | ★★★★★ |
| FastEmbed | 本地 Embedding | ★★★★★ |
| Instructor | 结构化输出增强 | ★★★★★ |

---

## 目录结构

```
src/agents_v2/intent/
├── intent_classifier.py   # 关键词分类器
├── intent_router.py       # 主路由器
├── semantic_expander.py   # 语义扩展器
├── multi_intent.py        # 多意图检测
└── intent_confidence.py   # 置信度校准
```

---

**更新日期**: 2026-05-03
**基于代码**: `src/agents_v2/unified/intent_router.py`