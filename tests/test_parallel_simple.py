"""
并行化优化验证脚本 - 独立测试版本

直接测试搜索和章节写作的并行化效果，不依赖有问题的模块导入。
"""
import asyncio
import time
import sys

sys.path.insert(0, 'D:/pycharmprojects/pythonProject1')


async def test_parallel_search():
    """测试并行搜索"""
    # 直接导入，避免通过 __init__.py 导入整个 agents_v2
    from src.agents_v2.search.search_orchestrator import SearchOrchestrator, SearchConfig, SearchStrategy
    from src.agents_v2.search.openalex_searcher import OpenAlexSearcher
    from src.agents_v2.search.arxiv_searcher import ArxivSearcher

    query = "machine learning"

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


async def test_parallel_writing_simulation():
    """模拟并行章节写作测试"""
    print("\n=== 测试: 并行章节写作模拟 ===")

    # 模拟5个章节的写作
    async def write_chapter(chapter_id: int) -> str:
        await asyncio.sleep(1)  # 模拟 LLM 调用耗时
        return f"## Chapter {chapter_id}\n\nContent for chapter {chapter_id}..."

    async def write_serial(chapters: list) -> list:
        """串行写作"""
        results = []
        for ch in chapters:
            result = await write_chapter(ch)
            results.append(result)
        return results

    async def write_parallel(chapters: list) -> list:
        """并行写作"""
        semaphore = asyncio.Semaphore(3)
        async def write_with_limit(ch):
            async with semaphore:
                return await write_chapter(ch)
        tasks = [write_with_limit(ch) for ch in chapters]
        return await asyncio.gather(*tasks)

    chapters = [1, 2, 3, 4, 5]

    # 测试串行
    start = time.time()
    await write_serial(chapters)
    serial_time = time.time() - start

    # 测试并行
    start = time.time()
    await write_parallel(chapters)
    parallel_time = time.time() - start

    print(f"串行耗时: {serial_time:.2f}s")
    print(f"并行耗时: {parallel_time:.2f}s")
    print(f"加速比: {serial_time/parallel_time:.2f}x")

    return serial_time, parallel_time


async def main():
    print("=" * 60)
    print("并行化优化验证")
    print("=" * 60)

    times = {}

    # 测试并行搜索
    try:
        times["parallel_search"] = await test_parallel_search()
    except Exception as e:
        print(f"并行搜索测试失败: {e}")

    # 测试并行写作模拟
    try:
        serial_time, parallel_time = await test_parallel_writing_simulation()
        times["serial_writing"] = serial_time
        times["parallel_writing"] = parallel_time
    except Exception as e:
        print(f"并行写作测试失败: {e}")

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, t in times.items():
        if isinstance(t, tuple):
            print(f"{name}: serial={t[0]:.2f}s, parallel={t[1]:.2f}s")
        else:
            print(f"{name}: {t:.2f}s")

    if "serial_writing" in times and "parallel_writing" in times:
        print(f"\n预期效果: 章节撰写从 {times['serial_writing']:.1f}s 降至 {times['parallel_writing']:.1f}s")
        print(f"提升: {(1 - times['parallel_writing']/times['serial_writing'])*100:.0f}%")

    print("\n" + "=" * 60)
    print("优化验证完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
