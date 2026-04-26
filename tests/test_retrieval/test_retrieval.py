"""
检索模块测试 - 第二迭代

测试动态检索规划器、SELF-RAG控制器、交叉编码器重排序和迭代式检索
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# 测试动态检索规划器
from src.agents_v2.retrieval.dynamic_planner import (
    DynamicRetrievalPlanner,
    QueryType,
    RetrievalPlan,
    RetrievalStrategy,
    STRATEGY_CONFIGS,
    create_retrieval_plan
)

# 测试SELF-RAG控制器
from src.agents_v2.retrieval.self_rag_controller import (
    SELF_RAGController,
    RAGResponse,
    DocumentEvaluation,
    self_rag_answer
)

# 测试交叉编码器重排序
from src.agents_v2.retrieval.cross_encoder_reranker import (
    CrossEncoderReranker,
    HybridReranker,
    RerankedDoc,
    rerank_documents
)

# 测试迭代式检索
from src.agents_v2.retrieval.iterative_retriever import (
    IterativeRetriever,
    AdaptiveRetriever,
    RetrievalResult,
    RetrievalStep,
    iterative_retrieve
)


class TestDynamicRetrievalPlanner:
    """测试动态检索规划器"""

    def test_planner_init(self):
        """测试规划器初始化"""
        planner = DynamicRetrievalPlanner()
        assert planner is not None
        assert len(planner.query_history) == 0

    def test_classify_fact_lookup(self):
        """测试事实查找分类"""
        planner = DynamicRetrievalPlanner()

        query = "Transformer的作者是谁？"
        qtype = planner._classify_with_rules(query)
        assert qtype == QueryType.FACT_LOOKUP

    def test_classify_definition(self):
        """测试定义分类"""
        planner = DynamicRetrievalPlanner()

        query = "什么是大语言模型？"
        qtype = planner._classify_with_rules(query)
        assert qtype == QueryType.DEFINITION

    def test_classify_comparison(self):
        """测试比较分类"""
        planner = DynamicRetrievalPlanner()

        query = "BERT和GPT有什么区别？"
        qtype = planner._classify_with_rules(query)
        assert qtype == QueryType.COMPARISON

    def test_classify_complex_reasoning(self):
        """测试复杂推理分类"""
        planner = DynamicRetrievalPlanner()

        query = "为什么Transformer效果更好？请分析原因"
        qtype = planner._classify_with_rules(query)
        assert qtype == QueryType.COMPLEX_REASONING

    def test_classify_exploration(self):
        """测试探索分类"""
        planner = DynamicRetrievalPlanner()

        query = "了解最新的AI研究方向"
        qtype = planner._classify_with_rules(query)
        assert qtype in [QueryType.EXPLORATION, QueryType.UNKNOWN]

    def test_plan_generation(self):
        """测试计划生成"""
        planner = DynamicRetrievalPlanner()

        plan = asyncio.run(planner.plan("什么是机器学习？"))

        assert isinstance(plan, RetrievalPlan)
        assert plan.primary_strategy in ["sparse", "dense", "hybrid"]
        assert plan.depth >= 1
        assert plan.max_iterations >= 1

    def test_plan_for_fact_lookup(self):
        """测试事实查找的计划"""
        planner = DynamicRetrievalPlanner()

        plan = asyncio.run(planner.plan("谁发明了Transformer？"))

        assert plan.query_type == QueryType.FACT_LOOKUP
        assert plan.primary_strategy == "sparse"
        assert plan.use_rerank == False

    def test_plan_for_complex_reasoning(self):
        """测试复杂推理的计划"""
        planner = DynamicRetrievalPlanner()

        plan = asyncio.run(planner.plan("分析Transformer架构的优缺点"))

        assert plan.primary_strategy in ["sparse", "dense", "hybrid"]
        assert plan.depth >= 2

    def test_strategy_configs(self):
        """测试策略配置"""
        assert QueryType.FACT_LOOKUP in STRATEGY_CONFIGS
        assert QueryType.COMPLEX_REASONING in STRATEGY_CONFIGS
        assert QueryType.EXPLORATION in STRATEGY_CONFIGS
        assert QueryType.COMPARISON in STRATEGY_CONFIGS
        assert QueryType.DEFINITION in STRATEGY_CONFIGS

    def test_depth_for_type(self):
        """测试不同类型对应的深度"""
        planner = DynamicRetrievalPlanner()

        assert planner._get_depth_for_type(QueryType.FACT_LOOKUP) == 1
        assert planner._get_depth_for_type(QueryType.COMPLEX_REASONING) == 3
        assert planner._get_depth_for_type(QueryType.EXPLORATION) == 2


class TestSelfRAGController:
    """测试SELF-RAG控制器"""

    def test_controller_init(self):
        """测试控制器初始化"""
        mock_llm = MagicMock()
        controller = SELF_RAGController(mock_llm, relevance_threshold=0.7)

        assert controller.relevance_threshold == 0.7
        assert controller.llm == mock_llm

    @pytest.mark.asyncio
    async def test_evaluate_relevance(self):
        """测试相关性评估"""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.generations = [[MagicMock(text="0.8")]]
        mock_llm.agenerate = AsyncMock(return_value=mock_result)

        controller = SELF_RAGController(mock_llm)
        score = await controller.evaluate_relevance(
            "这是一篇关于机器学习的论文",
            "机器学习"
        )

        assert 0 <= score <= 1

    @pytest.mark.asyncio
    async def test_evaluate_documents(self):
        """测试批量文档评估"""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.generations = [[MagicMock(text="0.75")]]
        mock_llm.agenerate = AsyncMock(return_value=mock_result)

        controller = SELF_RAGController(mock_llm)

        docs = [
            "机器学习是人工智能的分支",
            "今天天气很好",
            "深度学习使用神经网络"
        ]

        evaluations = await controller.evaluate_documents(docs, "机器学习")

        assert len(evaluations) == 3
        assert all(isinstance(e, DocumentEvaluation) for e in evaluations)

    @pytest.mark.asyncio
    async def test_generate_with_reflection(self):
        """测试带反思的生成"""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.generations = [[MagicMock(text="根据文档，机器学习是...")]]
        mock_llm.agenerate = AsyncMock(return_value=mock_result)

        controller = SELF_RAGController(mock_llm)

        docs = ["机器学习是人工智能的分支", "深度学习是机器学习的分支"]
        query = "什么是机器学习？"

        response = await controller.generate_with_reflection(query, docs)

        assert isinstance(response, RAGResponse)
        assert response.answer != ""
        assert response.documents_evaluated == 2

    @pytest.mark.asyncio
    async def test_generate_without_relevant_docs(self):
        """测试无相关文档时的生成"""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.generations = [[MagicMock(text="根据我的知识，机器学习是...")]]
        mock_llm.agenerate = AsyncMock(return_value=mock_result)

        controller = SELF_RAGController(mock_llm)

        docs = ["今天天气很好", "晚饭吃什么"]
        query = "机器学习的定义"

        response = await controller.generate_with_reflection(query, docs)

        assert isinstance(response, RAGResponse)


class TestCrossEncoderReranker:
    """测试交叉编码器重排序"""

    def test_reranker_init(self):
        """测试重排序器初始化"""
        reranker = CrossEncoderReranker()
        assert reranker is not None

    @pytest.mark.asyncio
    async def test_rerank_simple(self):
        """测试简单重排序"""
        reranker = CrossEncoderReranker()  # 不加载真实模型

        query = "机器学习"
        candidates = [
            "机器学习是人工智能的分支",
            "今天天气很好",
            "深度学习属于机器学习"
        ]

        results = await reranker.rerank(query, candidates, top_k=3)

        assert len(results) == 3
        assert all(isinstance(r, RerankedDoc) for r in results)
        # 检查是否按分数排序
        for i in range(len(results) - 1):
            assert results[i].score >= results[i+1].score

    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self):
        """测试top_k参数"""
        reranker = CrossEncoderReranker()

        query = "AI"
        candidates = [f"文档{i}" for i in range(20)]

        results = await reranker.rerank(query, candidates, top_k=5)

        assert len(results) == 5
        assert results[0].rank == 1

    @pytest.mark.asyncio
    async def test_compute_similarity(self):
        """测试单文档相似度计算"""
        reranker = CrossEncoderReranker()

        score = await reranker.compute_similarity(
            "机器学习",
            "机器学习是人工智能的分支"
        )

        assert 0 <= score <= 2  # 简单实现可能返回重叠词数

    def test_normalize_scores(self):
        """测试分数归一化"""
        reranker = HybridReranker()

        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = reranker._normalize_scores(scores)

        assert min(normalized) == 0.0
        assert max(normalized) == 1.0
        assert len(normalized) == len(scores)

    def test_normalize_scores_same_values(self):
        """测试相同分数的归一化"""
        reranker = HybridReranker()

        scores = [0.5, 0.5, 0.5]
        normalized = reranker._normalize_scores(scores)

        assert all(s == 0.5 for s in normalized)


class TestHybridReranker:
    """测试混合重排序器"""

    @pytest.mark.asyncio
    async def test_hybrid_rerank(self):
        """测试混合重排序"""
        reranker = HybridReranker(
            vector_weight=0.4,
            cross_encoder_weight=0.4,
            bm25_weight=0.2
        )

        query = "机器学习"
        candidates = [
            "机器学习是人工智能的分支",
            "今天天气很好",
            "深度学习使用神经网络"
        ]
        vector_scores = [0.9, 0.1, 0.7]
        bm25_scores = [0.8, 0.2, 0.6]

        results = await reranker.rerank(
            query, candidates,
            vector_scores=vector_scores,
            bm25_scores=bm25_scores,
            top_k=3
        )

        assert len(results) == 3
        assert all(r.score <= 1.0 for r in results)

    @pytest.mark.asyncio
    async def test_hybrid_without_scores(self):
        """测试无预定义分数的混合重排序"""
        reranker = HybridReranker()

        query = "机器学习"
        candidates = [
            "机器学习是人工智能的分支",
            "深度学习是机器学习的分支"
        ]

        results = await reranker.rerank(query, candidates, top_k=2)

        assert len(results) == 2


class TestIterativeRetriever:
    """测试迭代式检索器"""

    def test_retriever_init(self):
        """测试检索器初始化"""
        mock_base = MagicMock()
        mock_controller = MagicMock()

        retriever = IterativeRetriever(
            base_retriever=mock_base,
            self_rag_controller=mock_controller,
            max_iterations=3
        )

        assert retriever.max_iterations == 3
        assert len(retriever.iteration_history) == 0

    @pytest.mark.asyncio
    async def test_iterative_retrieve(self):
        """测试迭代检索"""
        # 模拟基础检索器
        mock_base = MagicMock()
        mock_base.retrieve = AsyncMock(side_effect=[
            ["文档1", "文档2", "文档3"],
            ["文档4", "文档5"]
        ])

        # 模拟控制器
        mock_controller = MagicMock()
        mock_controller.evaluate_documents = AsyncMock(return_value=[
            MagicMock(should_use=True),
            MagicMock(should_use=True),
            MagicMock(should_use=False)
        ])

        retriever = IterativeRetriever(
            base_retriever=mock_base,
            self_rag_controller=mock_controller,
            max_iterations=3,
            min_relevant_docs=2
        )

        result = await retriever.retrieve("机器学习")

        assert isinstance(result, RetrievalResult)
        assert result.iterations >= 1
        assert result.total_time > 0

    @pytest.mark.asyncio
    async def test_deduplicate(self):
        """测试去重"""
        mock_base = MagicMock()
        mock_controller = MagicMock()

        retriever = IterativeRetriever(
            base_retriever=mock_base,
            self_rag_controller=mock_controller
        )

        docs = [
            "机器学习是人工智能的分支",
            "机器学习是人工智能的分支",  # 重复
            "深度学习是机器学习的分支"
        ]

        unique = retriever._deduplicate(docs)

        assert len(unique) == 2

    def test_get_retrieval_stats(self):
        """测试获取统计信息"""
        mock_base = MagicMock()
        mock_controller = MagicMock()

        retriever = IterativeRetriever(
            base_retriever=mock_base,
            self_rag_controller=mock_controller
        )

        # 无历史记录
        stats = retriever.get_retrieval_stats()
        assert stats["status"] == "no_history"


class TestAdaptiveRetriever:
    """测试自适应检索器"""

    def test_adaptive_retriever_init(self):
        """测试自适应检索器初始化"""
        mock_iterative = MagicMock()
        adaptive = AdaptiveRetriever(mock_iterative)

        assert adaptive.retriever == mock_iterative

    @pytest.mark.asyncio
    async def test_classify_difficulty(self):
        """测试难度分类"""
        mock_iterative = MagicMock()
        adaptive = AdaptiveRetriever(mock_iterative)

        # 简单查询
        difficulty = await adaptive.classify_difficulty("AI定义")
        assert difficulty <= 0.5

        # 复杂查询
        difficulty = await adaptive.classify_difficulty(
            "分析比较深度学习框架在大规模分布式训练中的性能差异和优化策略"
        )
        assert difficulty >= 0.3


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_retrieval_pipeline(self):
        """完整检索流程测试"""
        # 1. 创建组件
        planner = DynamicRetrievalPlanner()
        controller = SELF_RAGController(MagicMock())

        # 模拟基础检索器
        mock_base = MagicMock()
        mock_base.retrieve = AsyncMock(return_value=[
            "机器学习是人工智能的分支",
            "深度学习使用神经网络",
            "今天天气很好"
        ])

        retriever = IterativeRetriever(
            base_retriever=mock_base,
            self_rag_controller=controller,
            max_iterations=2
        )

        # 2. 规划
        plan = await planner.plan("机器学习的定义")

        # 3. 检索
        result = await retriever.retrieve("机器学习的定义")

        # 4. 验证
        assert result is not None
        assert isinstance(result.documents, list)

    def test_all_modules_importable(self):
        """测试所有模块可导入"""
        from src.agents_v2.retrieval import (
            DynamicRetrievalPlanner,
            SELF_RAGController,
            CrossEncoderReranker,
            IterativeRetriever
        )

        assert DynamicRetrievalPlanner is not None
        assert SELF_RAGController is not None
        assert CrossEncoderReranker is not None
        assert IterativeRetriever is not None
