"""
知识图谱GraphRAG问答测试
"""
import pytest
from src.agents_v2.knowledge_graph import kg_graphrag


class TestQueryType:
    """QueryType枚举测试"""

    def test_query_types(self):
        """测试查询类型存在"""
        assert kg_graphrag.QueryType.FACTUAL.value == "factual"
        assert kg_graphrag.QueryType.COMPARATIVE.value == "comparative"
        assert kg_graphrag.QueryType.EXPLORATORY.value == "exploratory"
        assert kg_graphrag.QueryType.CAUSAL.value == "causal"
        assert kg_graphrag.QueryType.SUMMARY.value == "summary"


class TestQuery:
    """Query类测试"""

    def test_creation(self):
        """测试创建"""
        query = kg_graphrag.Query(
            text="谁写了深度学习论文",
            query_type=kg_graphrag.QueryType.FACTUAL,
            entities=["paper_1"],
            keywords=["深度学习", "论文"]
        )
        assert query.text == "谁写了深度学习论文"
        assert query.query_type == kg_graphrag.QueryType.FACTUAL
        assert "paper_1" in query.entities

    def test_default_fields(self):
        """测试默认字段"""
        query = kg_graphrag.Query(
            text="测试查询",
            query_type=kg_graphrag.QueryType.FACTUAL
        )
        assert query.entities == []
        assert query.relations == []
        assert query.keywords == []


class TestRetrievalItem:
    """RetrievalItem类测试"""

    def test_creation(self):
        """测试创建"""
        item = kg_graphrag.RetrievalItem(
            entity_id="paper_1",
            entity_type="Paper",
            score=0.95,
            method="vector",
            content="Deep Learning论文"
        )
        assert item.entity_id == "paper_1"
        assert item.score == 0.95
        assert item.method == "vector"


class TestGraphRAGContext:
    """GraphRAGContext类测试"""

    def test_creation(self):
        """测试创建"""
        query = kg_graphrag.Query("测试", kg_graphrag.QueryType.FACTUAL)
        context = kg_graphrag.GraphRAGContext(
            query=query,
            retrieved_items=[],
            subgraph_summary="摘要",
            entity_map={"e1": "实体1"},
            evidence=["证据1"]
        )
        assert context.query == query
        assert context.subgraph_summary == "摘要"

    def test_to_prompt_context(self):
        """测试转prompt上下文"""
        query = kg_graphrag.Query("测试", kg_graphrag.QueryType.FACTUAL)
        context = kg_graphrag.GraphRAGContext(
            query=query,
            retrieved_items=[],
            subgraph_summary="测试摘要",
            entity_map={"paper_1": "深度学习"},
            evidence=["证据1"]
        )

        prompt = context.to_prompt_context()
        assert "factual" in prompt
        assert "深度学习" in prompt
        assert "测试摘要" in prompt
        assert "证据1" in prompt


class TestQueryClassifier:
    """QueryClassifier类测试"""

    def test_classify_factual(self):
        """测试事实查询分类"""
        classifier = kg_graphrag.QueryClassifier()
        qtype = classifier.classify("谁写了深度学习论文")
        assert qtype == kg_graphrag.QueryType.FACTUAL

    def test_classify_comparative(self):
        """测试比较查询分类"""
        classifier = kg_graphrag.QueryClassifier()
        qtype = classifier.classify("比较Transformer和CNN哪个更好")
        assert qtype == kg_graphrag.QueryType.COMPARATIVE

    def test_classify_causal(self):
        """测试因果查询分类"""
        classifier = kg_graphrag.QueryClassifier()
        qtype = classifier.classify("因为什么原因导致深度学习效果好")
        assert qtype == kg_graphrag.QueryType.CAUSAL

    def test_classify_exploratory(self):
        """测试探索查询分类"""
        classifier = kg_graphrag.QueryClassifier()
        qtype = classifier.classify("关于自然语言处理的研究趋势")
        assert qtype == kg_graphrag.QueryType.EXPLORATORY

    def test_classify_summary(self):
        """测试摘要查询分类"""
        classifier = kg_graphrag.QueryClassifier()
        qtype = classifier.classify("总结一下机器学习的发展")
        assert qtype == kg_graphrag.QueryType.SUMMARY

    def test_extract_entities_quoted(self):
        """测试提取带引号实体"""
        classifier = kg_graphrag.QueryClassifier()
        entities = classifier.extract_entities('介绍一下"深度学习"这本书')
        assert "深度学习" in entities

    def test_extract_entities_reference(self):
        """测试提取引用实体"""
        classifier = kg_graphrag.QueryClassifier()
        entities = classifier.extract_entities("论文#1的作者是谁")
        assert "paper_1" in entities

    def test_extract_keywords(self):
        """测试关键词提取"""
        classifier = kg_graphrag.QueryClassifier()
        keywords = classifier.extract_keywords("Deep Learning is a branch of Machine Learning")
        assert "deep" in keywords or "learning" in keywords or "machine" in keywords


class TestGraphRAGRetriever:
    """GraphRAGRetriever类测试"""

    def test_creation(self):
        """测试创建"""
        retriever = kg_graphrag.GraphRAGRetriever()
        assert retriever.vector_weight == 0.4
        assert retriever.graph_weight == 0.3
        assert retriever.keyword_weight == 0.3

    def test_custom_weights(self):
        """测试自定义权重"""
        retriever = kg_graphrag.GraphRAGRetriever(
            vector_weight=0.5,
            graph_weight=0.2,
            keyword_weight=0.3
        )
        assert retriever.vector_weight == 0.5

    def test_add_entity(self):
        """测试添加实体"""
        retriever = kg_graphrag.GraphRAGRetriever()
        retriever.add_entity(
            entity_id="paper_1",
            entity_type="Paper",
            text="Deep Learning论文",
            properties={"year": 2024}
        )

        assert "paper_1" in retriever._entities
        assert retriever._entities["paper_1"]["type"] == "Paper"

    def test_add_relation(self):
        """测试添加关系"""
        retriever = kg_graphrag.GraphRAGRetriever()
        retriever.add_entity("paper_1", "Paper", "Paper 1")
        retriever.add_entity("author_1", "Author", "Author 1")
        retriever.add_relation("paper_1", "author_1", "AUTHORED_BY")

        assert len(retriever._relations) == 1

    def test_search_by_keywords(self):
        """测试关键词检索"""
        retriever = kg_graphrag.GraphRAGRetriever()
        retriever.add_entity("paper_1", "Paper", "Deep Learning论文")
        retriever.add_entity("paper_2", "Paper", "Machine Learning论文")
        retriever.add_entity("author_1", "Author", "John Doe")

        results = retriever.search_by_keywords(["Deep", "Learning"])

        assert len(results) >= 1
        entity_ids = [r[0] for r in results]
        assert "paper_1" in entity_ids

    def test_search_by_keywords_no_match(self):
        """测试关键词无匹配"""
        retriever = kg_graphrag.GraphRAGRetriever()
        retriever.add_entity("paper_1", "Paper", "Deep Learning论文")

        results = retriever.search_by_keywords(["量子计算"])
        assert len(results) == 0

    def test_search_by_graph(self):
        """测试图检索"""
        retriever = kg_graphrag.GraphRAGRetriever()
        retriever.add_entity("paper_1", "Paper", "Paper 1")
        retriever.add_entity("paper_2", "Paper", "Paper 2")
        retriever.add_entity("paper_3", "Paper", "Paper 3")
        retriever.add_relation("paper_1", "paper_2", "CITES")
        retriever.add_relation("paper_2", "paper_3", "CITES")

        results = retriever.search_by_graph(["paper_1"], depth=1)

        entity_ids = [r[0] for r in results]
        assert "paper_1" in entity_ids
        assert "paper_2" in entity_ids

    def test_search_by_graph_no_entities(self):
        """测试图检索无实体"""
        retriever = kg_graphrag.GraphRAGRetriever()
        results = retriever.search_by_graph([], depth=1)
        assert results == []

    def test_retrieve(self):
        """测试完整检索"""
        retriever = kg_graphrag.GraphRAGRetriever()
        retriever.add_entity("paper_1", "Paper", "Deep Learning Paper", keywords=["deep", "learning"])
        retriever.add_entity("author_1", "Author", "John Doe", keywords=["john"])

        context = retriever.retrieve("Who wrote Deep Learning Paper")

        assert isinstance(context, kg_graphrag.GraphRAGContext)
        assert context.query.query_type == kg_graphrag.QueryType.FACTUAL
        assert len(context.retrieved_items) > 0

    def test_retrieve_empty(self):
        """测试空检索"""
        retriever = kg_graphrag.GraphRAGRetriever()
        context = retriever.retrieve("测试查询")

        assert len(context.retrieved_items) == 0


class TestGraphRAGQA:
    """GraphRAGQA类测试"""

    def test_creation(self):
        """测试创建"""
        qa = kg_graphrag.GraphRAGQA()
        assert qa.retriever is not None

    def test_build_index(self):
        """测试构建索引"""
        qa = kg_graphrag.GraphRAGQA()
        qa.build_index(
            entities=[
                ("paper_1", "Paper", "Deep Learning论文"),
                ("author_1", "Author", "John Doe")
            ],
            relations=[
                ("paper_1", "author_1", "AUTHORED_BY")
            ]
        )

        assert "paper_1" in qa.retriever._entities

    def test_query(self):
        """测试问答"""
        qa = kg_graphrag.GraphRAGQA()
        qa.build_index(
            entities=[
                ("paper_1", "Paper", "Deep Learning论文"),
                ("author_1", "Author", "John Doe")
            ],
            relations=[
                ("paper_1", "author_1", "AUTHORED_BY")
            ]
        )

        context = qa.query("Deep Learning论文的作者是谁")

        assert isinstance(context, kg_graphrag.GraphRAGContext)
        assert len(context.retrieved_items) > 0

    def test_batch_query(self):
        """测试批量问答"""
        qa = kg_graphrag.GraphRAGQA()
        qa.build_index(
            entities=[
                ("paper_1", "Paper", "Deep Learning论文"),
                ("paper_2", "Paper", "Machine Learning论文")
            ],
            relations=[]
        )

        contexts = qa.batch_query([
            "Deep Learning论文的作者是谁",
            "Machine Learning论文是什么"
        ])

        assert len(contexts) == 2


class TestCreateGraphRAGQA:
    """create_graphrag_qa工厂函数测试"""

    def test_create(self):
        """测试创建"""
        qa = kg_graphrag.create_graphrag_qa()
        assert isinstance(qa, kg_graphrag.GraphRAGQA)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
