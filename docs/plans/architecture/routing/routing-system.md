# Routing 意图路由详解

> 位置: `src/agents_v2/routing/`

## 一、架构概览

```
routing/
├── __init__.py
├── intent_classifier.py     # 意图分类器 (9KB)
├── intent_confidence.py     # 置信度计算 (9KB)
├── llm_intent_classifier.py # LLM意图分类 (9KB)
├── multi_intent.py          # 多意图处理 (9KB)
├── semantic_expander.py    # 语义扩展 (12KB)
├── agent_selector.py       # Agent选择器 (8KB)
├── fallback_router.py      # 降级路由 (8KB)
└── routing_optimizer.py     # 路由优化 (9KB)
```

## 二、路由流程

```
用户输入
    │
    ▼
┌─────────────────────────────┐
│  IntentClassifier           │
│  (关键词快速匹配, <1ms)      │
│  - 命中 → 返回意图类型        │
│  - 未命中 → 进入LLM分类       │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  LLMIntentClassifier        │
│  (语义分类, 500ms-2s)        │
│  - 多意图检测               │
│  - 置信度评分               │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  ConfidenceCalibrator      │
│  (置信度校准)                │
│  - 关键词+LLM双重验证加分    │
│  - 冲突检测                 │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  AgentSelector             │
│  (Agent选择)                │
│  - 意图→Agent映射           │
│  - 协作模式判断             │
└─────────────────────────────┘
    │
    ▼
路由结果输出
```

## 三、意图分类

### 3.1 IntentClassifier 关键词分类

| 关键词 | 意图类型 |
|--------|----------|
| 找/搜索/论文 | LITERATURE_SEARCH |
| 综述/总结/对比 | LITERATURE_REVIEW |
| 选题/研究方向 | TOPIC_SELECT |
| 大纲/结构 | OUTLINE_GENERATE |
| 写作/撰写 | DRAFT_WRITE |
| 修改/修订 | PAPER_REVISION |
| 报告/资讯 | REPORT_REFINE |

### 3.2 LLMIntentClassifier 语义分类

```python
class LLMIntentClassifier:
    """基于LLM的意图分类"""

    def classify(self, query: str) -> List[IntentResult]:
        """
        1. 构建分类Prompt
        2. 调用LLM
        3. 解析返回的意图列表
        4. 返回带置信度的意图结果
        """
        prompt = f"""分析用户查询的意图:
查询: {query}

可选意图:
- literature_search: 搜索论文
- literature_review: 文献综述
- topic_select: 选题
- outline_generate: 大纲生成
- draft_write: 初稿撰写
- paper_revision: 智能改稿

返回JSON格式:
{{"intents": [{"intent": "类型", "confidence": 0.0-1.0}]}}"""

        response = self.llm.invoke(prompt)
        return self._parse_intents(response)
```

## 四、多意图处理

### 4.1 MultiIntentProcessor

```python
class MultiIntentProcessor:
    """多意图处理器"""

    def process(
        self,
        primary: Intent,
        secondary: List[Intent]
    ) -> ProcessingMode:
        """
        判断处理模式:
        - single: 单一意图，单独执行
        - collaboration: 多意图协作
        - pipeline: 流水线顺序执行
        """
        if not secondary:
            return ProcessingMode.SINGLE

        # 检查是否存在冲突意图
        if self._has_conflict(primary, secondary):
            return ProcessingMode.PIPELINE

        # 多意图协作模式
        return ProcessingMode.COLLABORATION
```

### 4.2 意图冲突检测

| 意图对 | 是否冲突 | 处理方式 |
|--------|----------|----------|
| SEARCH vs SUMMARY | 部分 | Pipeline |
| SEARCH vs WRITING | 否 | Collaboration |
| OUTLINE vs WRITING | 否 | Pipeline |
| REVIEW vs REVISION | 部分 | Pipeline |

## 五、置信度计算

### 5.1 IntentConfidence

```python
class IntentConfidence:
    """置信度计算器"""

    def calibrate(
        self,
        keyword_match: bool,
        llm_confidence: float,
        intent_count: int
    ) -> float:
        """
        置信度校准规则:
        1. 双重验证(关键词+LLM) → +0.15
        2. 多意图 → 主意图置信度 × 0.9
        3. 上限封顶 1.0
        """
        confidence = llm_confidence

        if keyword_match:
            confidence += 0.15

        if intent_count > 1:
            confidence *= 0.9

        return min(confidence, 1.0)

    def get_level(self, confidence: float) -> ConfidenceLevel:
        """置信度等级"""
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
```

## 六、Agent选择

### 6.1 AgentSelector

```python
class AgentSelector:
    """Agent选择器"""

    INTENT_AGENT_MAP = {
        "literature_search": "PaperSearchAgent",
        "literature_review": "LiteratureAgent",
        "topic_select": "TopicAgent",
        "outline_generate": "OutlineAgent",
        "draft_write": "DraftWriterAgent",
        "paper_revision": "SmartReviserAgent",
    }

    def select(
        self,
        intent: Intent,
        mode: ProcessingMode
    ) -> SelectionResult:
        """
        1. 查询意图→Agent映射
        2. 判断是否需要多Agent协作
        3. 返回Agent列表和执行顺序
        """
        primary_agent = self.INTENT_AGENT_MAP.get(intent.type)

        if mode == ProcessingMode.SINGLE:
            return SelectionResult(agents=[primary_agent])

        elif mode == ProcessingMode.COLLABORATION:
            # 返回主要Agent + 协作Agent
            return SelectionResult(
                agents=[primary_agent, *self._get_collaborators(intent)],
                mode="collaboration"
            )

        elif mode == ProcessingMode.PIPELINE:
            # 返回流水线Agent顺序
            return SelectionResult(
                agents=self._get_pipeline_agents(intent),
                mode="pipeline"
            )
```

## 七、降级路由

### 7.1 FallbackRouter

```python
class FallbackRouter:
    """降级路由 - 当主路由失败时"""

    def route_with_fallback(
        self,
        query: str,
        primary_intent: Intent,
        confidence: float
    ) -> RoutingResult:
        """
        降级规则:
        1. 置信度 < 0.3 → 使用默认意图
        2. LLM不可用 → 使用关键词匹配
        3. Agent执行失败 → 尝试降级Agent
        """
        if confidence < 0.3:
            return self._route_to_default(query)

        try:
            return self._route_to_agent(primary_intent)
        except AgentExecutionError:
            return self._route_to_fallback_agent(primary_intent)
```

## 八、路由优化

### 8.1 RoutingOptimizer

```python
class RoutingOptimizer:
    """路由性能优化"""

    def optimize_routing(
        self,
        query: str,
        candidates: List[Intent]
    ) -> OptimizedRouting:
        """
        优化策略:
        1. 缓存高频查询的路由结果
        2. 批量处理相似查询
        3. 预热常用意图的LLM
        """
        # 缓存命中检查
        cache_key = self._generate_cache_key(query)
        if cached := self.cache.get(cache_key):
            return cached

        # 执行路由
        result = self._route(query, candidates)

        # 缓存结果
        if self._is_cacheable(query):
            self.cache.set(cache_key, result, ttl=3600)

        return result
```

---

**更新日期**: 2026-05-02
**基于代码**: `src/agents_v2/routing/`