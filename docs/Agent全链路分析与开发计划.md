# Paper Agent 全链路分析与开发计划

> 最后更新: 2026-04-27

---

## 一、全链路架构总览

```
用户输入
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. 输入处理层 (api_server.py / demo.py)                    │
│    - HTTP端点或脚本入口                                     │
│    - 输入验证 (InputValidator) [待增强]                     │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 意图路由层 (IntentRouter)                              │
│    - 关键词匹配 + LLM fallback                             │
│    - 11种IntentType                                       │
│    - Agent建议生成                                         │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. MasterSupervisor (全局协调器)                           │
│    - 状态管理 (PaperState)                                 │
│    - 6阶段流转: diagnostic→topic→literature→methodology  │
│    - 质量控制 (CircuitBreaker, FallbackHandler)            │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. PhaseSupervisor (阶段协调器)                            │
│    - 单阶段执行管理                                        │
│    - diagnostic: topic_refiner, literature_mapper           │
│    - topic: TopicAgent                                     │
│    - literature: LiteratureAgent                            │
│    - methodology: MethodologyAdvisor, ArgumentBuilder       │
│    - writing: Thesis, Outline, Draft                       │
│    - polish: ChartFormatter, LanguagePolisher              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. 执行层 (Agent)                                         │
│    ┌──────────┬──────────┬──────────┬──────────┐         │
│    │PaperSearch│Thesis   │Outline   │Draft     │         │
│    │Agent      │Agent    │Agent     │Writer    │         │
│    └──────────┴──────────┴──────────┴──────────┘         │
└─────────────────────────────────────────────────────────────┘
    ↓
用户输出
```

---

## 二、核心入口文件

| 文件路径 | 功能 |
|---------|------|
| `src/agents_v2/api_server.py` | HTTP API服务入口 |
| `src/agents_v2/demo.py` | 演示脚本入口 |
| `src/agents_v2/unified/master_supervisor.py` | 核心协调器（主流程入口） |

---

## 三、链路各环节现状分析

### 3.1 输入处理层

| 环节 | 当前实现 | 问题/改进点 |
|------|----------|-------------|
| 文本输入 | 直接接收 | ❌ 缺乏输入验证 |
| 意图识别 | IntentRouter (关键词匹配+LLM) | ⚠️ 规则简单 |
| 意图分类 | 11种IntentType | ⚠️ 分类可能不准 |
| 多语言 | 支持中英 | ⚠️ 混合语言处理弱 |
| 输入验证 | 缺失 | ❌ 需添加InputValidator |

### 3.2 意图路由层 (IntentRouter)

**识别的意图类型**:
- `literature_search` - 搜索论文
- `literature_review` - 文献综述
- `topic_select` - 选题
- `thesis_formulate` - Thesis凝练
- `outline_generate` - 大纲生成
- `draft_write` - 初稿撰写
- `full_paper` - 完整论文流程
- `diagnostic` - 诊断

**问题**:
- 依赖关键词匹配 + LLM fallback
- 复杂场景可能不准确
- 当关键词和LLM都返回UNKNOWN时，系统降级为默认处理

### 3.3 检索链路

| 环节 | 当前实现 | 问题/改进点 |
|------|----------|-------------|
| 查询解析 | QueryParser | ✅ 已精细化 |
| 查询分类 | QueryTypeClassifier | ✅ 已精细化 |
| 查询改写 | QueryRewriter (新增) | ⚠️ 待集成到链路 |
| 查询扩展 | QueryExpander (新增) | ⚠️ 待集成到链路 |
| 检索策略 | DynamicPlanner | ✅ 已精细化 |
| ArXiv搜索 | ArxivMCPClient | ✅ 支持高级参数 |
| PubMed搜索 | PubmedMCPClient | ✅ 支持MeSH词 |
| SS搜索 | SemanticScholarSearcher | ⚠️ API有限 |
| 重排序 | CrossEncoderReranker | ✅ 已实现 |
| 迭代检索 | IterativeRetriever | ✅ 已实现 |
| 查询扩展 | QueryExpander (新增) | ⚠️ 待集成到链路 |
| 检索策略 | DynamicPlanner | ✅ 已精细化 |
| ArXiv搜索 | ArxivMCPClient | ✅ 支持高级参数 |
| PubMed搜索 | PubmedMCPClient | ✅ 支持MeSH词 |
| SS搜索 | SemanticScholarSearcher | ⚠️ API有限 |
| 重排序 | CrossEncoderReranker | ✅ 已实现 |
| 迭代检索 | IterativeRetriever | ✅ 已实现 |

### 2.3 PDF解析链路

| 环节 | 当前实现 | 问题/改进点 |
|------|----------|-------------|
| 引用提取 | CitationExtractor | ✅ 已精细化 |
| 参考文献解析 | ReferenceParser | ✅ 已精细化 |
| 章节解析 | SectionParser | ✅ 已精细化 |
| 元数据提取 | MetadataParser | ✅ 已精细化 |
| 表格检测 | TableDetector (新增) | ⚠️ 待集成 |
| 图表分类 | FigureClassifier (新增) | ⚠️ 待集成 |
| 查重检测 | PlagiarismChecker (新增) | ⚠️ 待集成 |

### 2.4 生成链路

| 环节 | 当前实现 | 问题/改进点 |
|------|----------|-------------|
| SELF-RAG | SELF_RAGController | ✅ 已精细化 |
| 答案生成 | AnswerGenerator | ✅ 已精细化 |
| 反思机制 | Reflection | ⚠️ 简单实现 |
| 引用生成 | Citation Generation | ❌ 缺失 |

### 2.5 输出链路

| 环节 | 当前实现 | 问题/改进点 |
|------|----------|-------------|
| 格式输出 | 直接返回 | ❌ 缺乏格式化 |
| 结果排序 | 按相关性 | ⚠️ 可多维度 |
| 结果去重 | 简单去重 | ⚠️ 需增强 |
| 输出验证 | 缺失 | ❌ 需添加 |

---

## 三、薄弱环节详细分析

### 3.1 意图识别薄弱

**问题**:
- 当前仅基于关键词匹配
- 无法处理复杂隐含意图
- 多意图情况处理不当

**改进方案**:
```python
# 增强意图识别
class IntentClassifier:
    """使用LLM进行意图分类"""

    async def classify(self, query: str) -> List[IntentType]:
        """返回可能的多个意图及置信度"""
        # 1. LLM分析用户真实意图
        # 2. 处理复合意图
        # 3. 返回置信度排序
```

### 3.2 检索链路薄弱

**问题**:
- 查询改写未集成
- 查询扩展未集成
- 多源检索结果融合简单

**改进方案**:
```python
# 检索链路增强
class EnhancedRetrievalChain:
    """增强检索链路"""

    async def retrieve(self, query: str):
        # 1. 查询理解
        parsed = self.query_parser.parse(query)

        # 2. 查询改写
        if need_rewrite(parsed):
            rewritten = self.rewriter.rewrite(query)

        # 3. 查询扩展
        expanded = self.expander.expand(rewritten)

        # 4. 多源并行检索
        results = await asyncio.gather(
            self.arxiv.search(expanded),
            self.pubmed.search(expanded),
            self.ss.search(expanded)
        )

        # 5. 结果融合
        fused = self.fuser.fuse(results)

        # 6. 重排序
        reranked = await self.reranker.rerank(query, fused)

        return reranked
```

### 3.3 PDF解析链路薄弱

**问题**:
- 表格检测、图表分类未集成
- 跨页表格处理缺失
- 复杂布局处理弱

### 3.4 生成链路薄弱

**问题**:
- 引用生成缺失
- 反思机制简单
- 长文本生成不稳定

---

## 四、30次迭代开发计划

### 迭代分类

| 类别 | 迭代次数 | 重点 |
|------|----------|------|
| 链路增强 | 1-5 | 输入处理、意图识别 |
| 检索增强 | 6-10 | 查询改写、扩展、融合 |
| 解析增强 | 11-15 | PDF解析、表格图表 |
| 生成增强 | 16-20 | 引用生成、反思机制 |
| 输出增强 | 21-25 | 格式化、验证、评估 |
| 集成测试 | 26-30 | 全链路集成、压测 |

---

### Phase 1: 链路增强 (迭代 1-5)

#### 迭代1: 输入验证与规范化

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| InputValidator | input_validator.py | 15 | P0 |
| TextCleaner | text_cleaner.py | 10 | P0 |
| QueryNormalizer | query_normalizer.py | 12 | P1 |

#### 迭代2: 意图识别增强

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| LLMIntentClassifier | intent_classifier.py | 20 | P0 |
| MultiIntentDetector | multi_intent.py | 15 | P1 |
| IntentConfidence | intent_confidence.py | 10 | P2 |

#### 迭代3: 意图路由优化

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| RoutingOptimizer | routing_optimizer.py | 15 | P0 |
| AgentSelector | agent_selector.py | 12 | P1 |
| FallbackRouter | fallback_router.py | 10 | P2 |

#### 迭代4: 状态管理增强

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| PaperStateV2 | state_model.py | 18 | P0 |
| StateValidator | state_validator.py | 12 | P1 |
| StatePersistence | state_persistence.py | 10 | P2 |

#### 迭代5: 链路监控

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| ChainMonitor | chain_monitor.py | 15 | P0 |
| LatencyTracker | latency_tracker.py | 10 | P1 |
| ChainDebugger | chain_debugger.py | 8 | P2 |

---

### Phase 2: 检索增强 (迭代 6-10)

#### 迭代6: 查询改写集成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| QueryRewriter (集成) | query_rewriter.py | 15 | P0 |
| RewriteValidator | rewrite_validator.py | 10 | P1 |

#### 迭代7: 查询扩展集成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| QueryExpander (集成) | query_expander.py | 15 | P0 |
| ExpansionValidator | expansion_validator.py | 10 | P1 |

#### 迭代8: 多源检索融合

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| ResultFuser | result_fuser.py | 18 | P0 |
| WeightOptimizer | weight_optimizer.py | 12 | P1 |
| FuserEvaluator | fuser_evaluator.py | 10 | P2 |

#### 迭代9: 检索结果增强

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| DeduplicatorV2 | deduplicator.py | 15 | P0 |
| RelevanceScorer | relevance_scorer.py | 12 | P1 |
| DiversityRanker | diversity_ranker.py | 10 | P2 |

#### 迭代10: 检索反馈优化

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| RetrievalFeedback | retrieval_feedback.py | 12 | P0 |
| FeedbackAnalyzer | feedback_analyzer.py | 10 | P1 |
| AdaptiveRetrieval | adaptive_retrieval.py | 8 | P2 |

---

### Phase 3: 解析增强 (迭代 11-15)

#### 迭代11: 表格检测集成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| TableDetector (集成) | table_detector.py | 20 | P0 |
| TableParser | table_parser.py | 15 | P1 |
| TableNormalizer | table_normalizer.py | 10 | P2 |

#### 迭代12: 图表分类集成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| FigureClassifier (集成) | figure_classifier.py | 18 | P0 |
| FigureExtractor | figure_extractor.py | 12 | P1 |
| CaptionGenerator | caption_generator.py | 10 | P2 |

#### 迭代13: 引用图谱集成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| CitationGraph (集成) | citation_graph.py | 15 | P0 |
| CitationLinker | citation_linker.py | 12 | P1 |
| CitationAnalyzer | citation_analyzer.py | 10 | P2 |

#### 迭代14: 查重检测集成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| PlagiarismChecker (集成) | plagiarism_checker.py | 18 | P0 |
| SimilarityCalculator | similarity_calculator.py | 12 | P1 |
| OriginalityReporter | originality_reporter.py | 10 | P2 |

#### 迭代15: PDF解析优化

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| LayoutAnalyzer | layout_analyzer.py | 15 | P0 |
| MultiColumnDetector | multi_column_detector.py | 12 | P1 |
| TextExtractorV2 | text_extractor.py | 10 | P2 |

---

### Phase 4: 生成增强 (迭代 16-20)

#### 迭代16: 引用生成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| CitationGenerator | citation_generator.py | 20 | P0 |
| ReferenceFormatter | reference_formatter.py | 15 | P1 |
| CitationStyleAdapter | citation_style_adapter.py | 10 | P2 |

#### 迭代17: 反思机制增强

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| ReflectionEngine | reflection_engine.py | 18 | P0 |
| SelfCritic | self_critic.py | 15 | P1 |
| ImprovementGenerator | improvement_generator.py | 12 | P2 |

#### 迭代18: 答案质量增强

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| AnswerQualityChecker | answer_quality_checker.py | 15 | P0 |
| FactChecker | fact_checker.py | 12 | P1 |
| ConsistencyValidator | consistency_validator.py | 10 | P2 |

#### 迭代19: 长文本生成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| StreamingGenerator | streaming_generator.py | 15 | P0 |
| ChunkManager | chunk_manager.py | 12 | P1 |
| CoherenceEnforcer | coherence_enforcer.py | 10 | P2 |

#### 迭代20: 生成优化

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| GenerationOptimizer | generation_optimizer.py | 12 | P0 |
| PromptTuner | prompt_tuner.py | 10 | P1 |
| OutputCache | output_cache.py | 8 | P2 |

---

### Phase 5: 输出增强 (迭代 21-25)

#### 迭代21: 输出格式化

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| OutputFormatter | output_formatter.py | 15 | P0 |
| MarkdownRenderer | markdown_renderer.py | 12 | P1 |
| JSONExporter | json_exporter.py | 10 | P2 |

#### 迭代22: 输出验证

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| OutputValidator | output_validator.py | 18 | P0 |
| SchemaChecker | schema_checker.py | 12 | P1 |
| QualityVerifier | quality_verifier.py | 10 | P2 |

#### 迭代23: 结果排序优化

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| MultiDimensionRanker | multi_dimension_ranker.py | 15 | P0 |
| PersonalizationRanker | personalization_ranker.py | 12 | P1 |
| ContextAwareRanker | context_aware_ranker.py | 10 | P2 |

#### 迭代24: 评估机制

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| RAGEvaluator | rag_evaluator.py | 18 | P0 |
| AnswerSimilarity | answer_similarity.py | 12 | P1 |
| RetrievalMetrics | retrieval_metrics.py | 10 | P2 |

#### 迭代25: 反馈闭环

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| FeedbackCollector | feedback_collector.py | 12 | P0 |
| PreferenceLearner | preference_learner.py | 15 | P1 |
| ModelUpdater | model_updater.py | 10 | P2 |

---

### Phase 6: 集成测试 (迭代 26-30)

#### 迭代26: 全链路集成

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| ChainIntegrator | chain_integrator.py | 20 | P0 |
| IntegrationTester | integration_tester.py | 15 | P1 |

#### 迭代27: 性能测试

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| PerformanceBenchmark | performance_benchmark.py | 15 | P0 |
| LoadTester | load_tester.py | 12 | P1 |
| StressTester | stress_tester.py | 10 | P2 |

#### 迭代28: 稳定性测试

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| ChaosTester | chaos_tester.py | 12 | P0 |
| RecoveryTester | recovery_tester.py | 10 | P1 |
| TimeoutHandler | timeout_handler.py | 8 | P2 |

#### 迭代29: 端到端测试

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| E2ETestSuite | e2e_test_suite.py | 25 | P0 |
| RegressionTester | regression_tester.py | 15 | P1 |

#### 迭代30: 发布准备

| 任务 | 文件 | 测试数 | 优先级 |
|------|------|--------|--------|
| DocumentationUpdater | docs_updater.py | 10 | P0 |
| MigrationGuide | migration_guide.py | 8 | P1 |
| ReleaseChecker | release_checker.py | 5 | P2 |

---

## 五、预期成果

### 5.1 小模块数量

| 当前 | 目标 |
|------|------|
| 52 | 120+ |

### 5.2 测试数量

| 当前 | 目标 |
|------|------|
| 1253 | 3000+ |

### 5.3 链路完整性

| 链路环节 | 当前 | 目标 |
|----------|------|------|
| 输入处理 | 40% | 100% |
| 意图识别 | 50% | 100% |
| 检索增强 | 70% | 100% |
| PDF解析 | 60% | 100% |
| 生成增强 | 50% | 100% |
| 输出增强 | 30% | 100% |

---

## 六、验收标准

### 阶段验收

| 阶段 | 迭代 | 验收标准 |
|------|------|----------|
| Phase 1 | 1-5 | 输入验证100%，意图识别准确率>85% |
| Phase 2 | 6-10 | 查询改写集成，检索召回率提升20% |
| Phase 3 | 11-15 | 表格检测准确率>90%，图表识别>85% |
| Phase 4 | 16-20 | 引用生成准确率>90%，反思有效率>80% |
| Phase 5 | 21-25 | 输出格式化率100%，验证覆盖率>95% |
| Phase 6 | 26-30 | 全链路通过率>95%，性能达标 |

### 最终验收

- [ ] 小模块总数 > 120
- [ ] 测试总数 > 3000
- [ ] 全链路集成测试通过
- [ ] 性能指标达标
- [ ] 文档完整

---

**最后更新: 2026-04-27**
