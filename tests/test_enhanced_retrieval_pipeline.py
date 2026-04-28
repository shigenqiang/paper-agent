"""
测试增强检索管道

验证阶段1的检索优化功能
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.agents_v2.retrieval.enhanced_retrieval_pipeline import (
    EnhancedRetrievalPipeline,
    PipelineConfig,
    RetrievalResult,
    enhanced_retrieve
)


class MockRetriever:
    """模拟检索器"""

    async def retrieve(self, query: str, top_k: int = 10):
        """模拟检索"""
        # 返回模拟文档
        return [
            f"Document about {query} - result {i}"
            for i in range(min(top_k, 20))
        ]


class MockLLM:
    """模拟LLM"""

    async def agenerate(self, prompts):
        """模拟生成"""
        # 简单返回
        class Generation:
            def __init__(self, text):
                self.text = text

        class Result:
            def __init__(self, text):
                self.generations = [[Generation(text)]]

        # 根据提示返回不同结果
        prompt = prompts[0]
        if "是否需要" in prompt or "需要检索" in prompt:
            return Result("是")
        elif "评分" in prompt or "相关性" in prompt:
            return Result("0.8")
        else:
            return Result("这是一个测试回答")


@pytest.mark.asyncio
async def test_basic_retrieval():
    """测试基础检索"""
    retriever = MockRetriever()
    pipeline = EnhancedRetrievalPipeline(
        retriever=retriever,
        config=PipelineConfig(
            enable_query_rewrite=False,
            enable_query_expansion=False,
            enable_reranking=False,
            enable_self_rag=False
        )
    )

    result = await pipeline.retrieve("machine learning", top_k=10)

    assert isinstance(result, RetrievalResult)
    assert result.query == "machine learning"
    assert len(result.documents) > 0
    assert len(result.documents) <= 10
    assert result.total_time > 0


@pytest.mark.asyncio
async def test_query_optimization():
    """测试查询优化"""
    retriever = MockRetriever()
    pipeline = EnhancedRetrievalPipeline(
        retriever=retriever,
        config=PipelineConfig(
            enable_query_rewrite=True,
            enable_query_expansion=True,
            enable_reranking=False,
            enable_self_rag=False
        )
    )

    result = await pipeline.retrieve("AI research", top_k=10)

    assert result.query_rewritten or result.query_expanded
    assert len(result.documents) > 0
    assert "optimized_queries" in result.metadata


@pytest.mark.asyncio
async def test_reranking():
    """测试重排序"""
    retriever = MockRetriever()
    pipeline = EnhancedRetrievalPipeline(
        retriever=retriever,
        config=PipelineConfig(
            enable_query_rewrite=False,
            enable_query_expansion=False,
            enable_reranking=True,
            enable_self_rag=False
        )
    )

    result = await pipeline.retrieve("deep learning", top_k=10)

    assert result.reranked
    assert result.rerank_time > 0
    assert len(result.scores) == len(result.documents)


@pytest.mark.asyncio
async def test_self_rag():
    """测试SELF-RAG"""
    retriever = MockRetriever()
    llm = MockLLM()

    pipeline = EnhancedRetrievalPipeline(
        retriever=retriever,
        llm=llm,
        config=PipelineConfig(
            enable_query_rewrite=False,
            enable_query_expansion=False,
            enable_reranking=False,
            enable_self_rag=True
        )
    )

    result = await pipeline.retrieve("neural networks", top_k=10)

    assert result.self_rag_applied
    assert len(result.documents) > 0


@pytest.mark.asyncio
async def test_full_pipeline():
    """测试完整管道"""
    retriever = MockRetriever()
    llm = MockLLM()

    pipeline = EnhancedRetrievalPipeline(
        retriever=retriever,
        llm=llm,
        config=PipelineConfig(
            enable_query_rewrite=True,
            enable_query_expansion=True,
            enable_reranking=True,
            enable_self_rag=True
        )
    )

    result = await pipeline.retrieve("transformer architecture", top_k=10)

    assert result.query_rewritten or result.query_expanded
    assert result.reranked
    assert result.self_rag_applied
    assert len(result.documents) > 0
    assert result.total_time > 0

    print(f"\n完整管道测试结果:")
    print(f"- 查询: {result.query}")
    print(f"- 返回文档数: {len(result.documents)}")
    print(f"- 总耗时: {result.total_time:.2f}s")
    print(f"- 检索耗时: {result.retrieval_time:.2f}s")
    print(f"- 重排序耗时: {result.rerank_time:.2f}s")
    print(f"- Query优化: {result.query_rewritten or result.query_expanded}")
    print(f"- 重排序: {result.reranked}")
    print(f"- SELF-RAG: {result.self_rag_applied}")


@pytest.mark.asyncio
async def test_iterative_retrieval():
    """测试迭代检索"""
    retriever = MockRetriever()
    llm = MockLLM()

    pipeline = EnhancedRetrievalPipeline(
        retriever=retriever,
        llm=llm,
        config=PipelineConfig(
            enable_iterative=True,
            max_iterations=2,
            min_relevant_docs=5
        )
    )

    result = await pipeline.iterative_retrieve("computer vision")

    assert len(result.documents) >= 5
    assert "iterations" in result.metadata
    print(f"\n迭代检索: {result.metadata['iterations']}次迭代")


@pytest.mark.asyncio
async def test_convenience_function():
    """测试便捷函数"""
    retriever = MockRetriever()
    llm = MockLLM()

    result = await enhanced_retrieve(
        query="natural language processing",
        retriever=retriever,
        llm=llm,
        top_k=15,
        enable_all_optimizations=True
    )

    assert isinstance(result, RetrievalResult)
    assert len(result.documents) <= 15
    assert result.total_time > 0


def test_pipeline_config():
    """测试管道配置"""
    config = PipelineConfig(
        enable_query_rewrite=True,
        enable_query_expansion=True,
        enable_reranking=True,
        enable_self_rag=True,
        initial_top_k=100,
        final_top_k=20
    )

    assert config.enable_query_rewrite
    assert config.enable_query_expansion
    assert config.enable_reranking
    assert config.enable_self_rag
    assert config.initial_top_k == 100
    assert config.final_top_k == 20


if __name__ == "__main__":
    # 运行测试
    print("开始测试增强检索管道...")

    asyncio.run(test_basic_retrieval())
    print("✓ 基础检索测试通过")

    asyncio.run(test_query_optimization())
    print("✓ 查询优化测试通过")

    asyncio.run(test_reranking())
    print("✓ 重排序测试通过")

    asyncio.run(test_self_rag())
    print("✓ SELF-RAG测试通过")

    asyncio.run(test_full_pipeline())
    print("✓ 完整管道测试通过")

    asyncio.run(test_iterative_retrieval())
    print("✓ 迭代检索测试通过")

    asyncio.run(test_convenience_function())
    print("✓ 便捷函数测试通过")

    test_pipeline_config()
    print("✓ 配置测试通过")

    print("\n所有测试通过！✨")
