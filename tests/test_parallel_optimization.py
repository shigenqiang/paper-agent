"""
并行化优化验证脚本

测试搜索和章节写作的并行化效果。
"""
import asyncio
import time
import logging
import sys

sys.path.insert(0, 'D:/pycharmprojects/pythonProject1')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_parallel_search():
    """测试并行搜索"""
    from src.agents_v2.search import (
        OpenAlexSearcher,
        ArxivSearcher,
        SearchOrchestrator,
        SearchConfig,
        SearchStrategy,
    )

    query = "machine learning transformer"

    # 创建搜索器
    searchers = {
        "openalex": OpenAlexSearcher(),
        "arxiv": ArxivSearcher(),
    }

    orchestrator = SearchOrchestrator(searchers)
    config = SearchConfig(
        strategy=SearchStrategy.BALANCED,
        max_results_per_source=10,
        enable_cache=True,
    )

    print("\n=== 测试: 并行搜索 ===")
    start = time.time()
    results = await orchestrator.search(query, config)
    elapsed = time.time() - start

    print(f"搜索结果: {len(results)} 篇")
    print(f"耗时: {elapsed:.2f}s")

    return elapsed


async def test_parallel_writing():
    """测试并行章节写作"""
    from src.agents_v2.langgraph_workflow.nodes.writer import WriterAgent
    from src.agents_v2.langgraph_workflow.state import PaperAgentState

    sections = [
        {
            "title": "Introduction",
            "description": "介绍研究背景",
            "key_points": ["背景1", "背景2"],
            "references": []
        },
        {
            "title": "Methods",
            "description": "介绍方法",
            "key_points": ["方法1", "方法2"],
            "references": []
        },
        {
            "title": "Experiments",
            "description": "实验结果",
            "key_points": ["实验1", "实验2"],
            "references": []
        },
    ]

    state = PaperAgentState()
    state.outline = {"title": "Test Paper", "sections": sections}
    state.selected_papers = []
    state.feedback = []

    writer = WriterAgent(llm=None)  # 使用模板生成，无需LLM

    print("\n=== 测试: 并行章节写作 ===")
    start = time.time()
    result = writer.execute(state)
    elapsed = time.time() - start

    print(f"草稿长度: {len(result.draft)} 字符")
    print(f"耗时: {elapsed:.2f}s")

    return elapsed


async def test_crawler_parallel():
    """测试 Crawler 并行搜索"""
    from src.agents_v2.langgraph_workflow.nodes.crawler import CrawlerAgent
    from src.agents_v2.langgraph_workflow.state import PaperAgentState

    state = PaperAgentState()
    state.user_query = "neural network optimization"

    crawler = CrawlerAgent(
        sources=["openalex", "arxiv"],
        max_per_source=5,
    )

    print("\n=== 测试: Crawler 并行搜索 ===")
    start = time.time()
    result = crawler.execute(state)
    elapsed = time.time() - start

    print(f"找到论文: {len(result.papers)} 篇")
    print(f"耗时: {elapsed:.2f}s")

    return elapsed


async def main():
    print("=" * 60)
    print("并行化优化验证")
    print("=" * 60)

    times = {}

    # 测试并行搜索
    try:
        times["parallel_search"] = await test_parallel_search()
    except Exception as e:
        logger.error(f"并行搜索测试失败: {e}")

    # 测试并行写作
    try:
        times["parallel_writing"] = await test_parallel_writing()
    except Exception as e:
        logger.error(f"并行写作测试失败: {e}")

    # 测试 Crawler
    try:
        times["crawler"] = await test_crawler_parallel()
    except Exception as e:
        logger.error(f"Crawler测试失败: {e}")

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, t in times.items():
        print(f"{name}: {t:.2f}s")

    print("\n" + "=" * 60)
    print("优化验证完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
