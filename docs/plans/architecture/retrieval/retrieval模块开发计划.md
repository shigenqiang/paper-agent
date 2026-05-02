# retrieval 模块开发计划

> 规划日期：2026-05-02
> 基于：`docs/implemented/architecture/retrieval/retrieval-system.md` + `docs/research/意图识别技术调研报告.md`
> 现状：AdaptiveRetrieval/HyDE/CrossEncoderReranker/SelfRAG 已实现

---

## 一、模块概述

### 1.1 现有架构

```
retrieval/
├── adaptive_retrieval.py       # 自适应检索 ✅
├── hyde_retriever.py         # HyDE检索 ✅
├── cross_encoder_reranker.py # Cross-Encoder重排 ✅
├── self_rag_controller.py     # Self-RAG控制 ✅
├── confidence_calculator.py   # 置信度计算 ✅
├── deduplicator.py           # 去重 ✅
├── document_evaluator.py     # 文档评估 ✅
├── priority_matcher.py       # 优先级匹配 ✅
├── query_classifier.py       # 查询分类 ✅
├── result_fuser.py           # 结果融合 ✅
├── retrieval_chain.py        # 检索链 ✅
├── rewrite_validator.py      # 重写验证 ✅
├── score_parser.py           # 分数解析 ✅
└── keyword_sets.py           # 关键词集合
```

### 1.2 提升目标

| 组件 | 当前 | 目标 |
|------|------|------|
| **AdaptiveRetrieval** | 4种策略 | 动态策略选择 + 学习 |
| **HyDE** | 基础 | 多假设生成 + 重排 |
| **CrossEncoder** | 基础重排 | 多模型集成 |
| **SelfRAG** | 基础控制 | 自适应阈值 |
| **意图融合** | 分离 | 意图感知检索 |

---

## 二、任务清单

### 2.1 AdaptiveRetrieval 增强（P1）

**目标**：动态策略选择 + 在线学习

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 动态策略选择 | P1 | 根据查询类型自适应 | `src/agents_v2/retrieval/dynamic_strategy.py` |
| 反馈学习 | P2 | 从用户反馈学习策略 | `src/agents_v2/retrieval/feedback_learner.py` |
| 策略效果追踪 | P2 | 策略评分历史 | `src/agents_v2/retrieval/strategy_tracker.py` |

### 2.2 HyDE 增强（P1）

**目标**：多假设生成 + 重排

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 多假设生成 | P1 | 生成 Top-K 假设文档 | `src/agents_v2/retrieval/multi_hypothesis.py` |
| 假设重排 | P1 | 假设间相关性 | `src/agents_v2/retrieval/hypothesis_rerank.py` |
| 假设融合 | P2 | 多假设结果合并 | `src/agents_v2/retrieval/hypothesis_fusion.py` |

### 2.3 CrossEncoder 多模型（P1）

**目标**：多模型集成重排

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 多模型支持 | P1 | cross-encoder 多模型 | `src/agents_v2/retrieval/multimodel_reranker.py` |
| 模型选择 | P2 | 根据查询自动选择 | `src/agents_v2/retrieval/model_selector.py` |
| 集成重排 | P1 | 多模型结果融合 | `src/agents_v2/retrieval/ensemble_rerank.py` |

### 2.4 SelfRAG 自适应（P2）

**目标**：自适应阈值

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 自适应阈值 | P2 | 根据上下文调整阈值 | `src/agents_v2/retrieval/adaptive_threshold.py` |
| 检索判断 | P2 | 是否需要检索 | `src/agents_v2/retrieval/retrieve_decider.py` |
| 自我反思 | P2 | 生成反思 token | `src/agents_v2/retrieval/self_reflect.py` |

### 2.5 意图感知检索（P0）

**目标**：与 IntentRouter 深度集成

**任务**：

| 任务 | 优先级 | 说明 | 文件 |
|------|--------|------|------|
| 意图注入 | P0 | 将意图信息注入检索 | `src/agents_v2/retrieval/intent_injector.py` |
| 意图重写 | P1 | 根据意图重写查询 | `src/agents_v2/retrieval/intent_rewrite.py` |
| 意图过滤 | P1 | 根据意图过滤结果 | `src/agents_v2/retrieval/intent_filter.py` |

---

## 三、检索流程增强

### 3.1 意图感知检索流程

```
用户查询
  ↓
IntentRouter (获取意图)
  ↓
意图注入 + 查询重写
  ↓
┌─────────────────────────────────────────────────────┐
│                  AdaptiveRetrieval                   │
│  STRATEGIES:                                       │
│    factual → dense (向量检索)                        │
│    conceptual → hybrid (混合检索)                   │
│    comparative → sparse (稀疏检索)                 │
│    temporal → dense (时间感知)                       │
│    research → multi-hypothesis (多假设)              │
└─────────────────────────────────────────────────────┘
  ↓
HyDE: 生成多个假设文档
  ↓
CrossEncoder 重排
  ↓
SelfRAG 判断相关性
  ↓
结果融合 (RRF/MRR)
  ↓
意图过滤
  ↓
Top-K 结果
```

### 3.2 多假设 HyDE 实现

```python
class MultiHypothesisHyDE:
    """多假设 HyDE 检索"""

    def __init__(self, num_hypotheses: int = 5):
        self.num_hypotheses = num_hypotheses

    async def generate_hypotheses(
        self,
        query: str,
        llm: ChatOpenAI
    ) -> List[str]:
        """生成多个假设文档"""
        prompt = f"""
        针对以下研究问题，生成 {self.num_hypotheses} 个不同的假设性回答：

        研究问题: {query}

        每个假设应该：
        1. 从不同角度切入
        2. 包含可能的论证和证据
        3. 2-3段落长度
        """

        response = await llm.ainvoke([HumanMessage(prompt)])
        hypotheses = self._parse_hypotheses(response.content)

        return hypotheses

    async def retrieve(
        self,
        query: str,
        collection: Any,
        top_k: int = 5
    ) -> List[Document]:
        """多假设检索"""
        # 1. 生成多个假设
        hypotheses = await self.generate_hypotheses(query, self.llm)

        # 2. 检索每个假设
        all_results = []
        for hyp in hypotheses:
            results = await collection.similarity_search(hyp, top_k)
            all_results.extend(results)

        # 3. 重排融合
        reranked = await self.reranker.rerank(query, all_results)

        return reranked[:top_k]
```

---

## 四、实施计划

### Phase 1：意图感知检索（1周）

```
Day 1-2:
  - 意图注入实现
  - 意图重写实现

Day 3-4:
  - 意图过滤实现
  - 与 IntentRouter 集成

Day 5:
  - 测试验证
```

### Phase 2：检索增强（2周）

```
Week 2:
  - 动态策略选择实现
  - 多假设 HyDE 实现

Week 3:
  - CrossEncoder 多模型集成
  - 模型选择实现
```

### Phase 3：SelfRAG 增强（1周）

```
Week 4:
  - 自适应阈值实现
  - 检索判断实现
  - 自我反思机制
```

---

## 五、验收标准

- [ ] 意图感知检索正常工作
- [ ] 多假设 HyDE 生成正常
- [ ] CrossEncoder 多模型重排正常
- [ ] AdaptiveRetrieval 策略选择合理
- [ ] 检索延迟 < 500ms

---

**版本**：v1.0
**规划日期**：2026-05-02
