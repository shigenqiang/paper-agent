"""
Query Rewrite Comparison Test
对比直接搜索 vs 查询改写后的搜索效果

测试目标：
1. 直接使用用户输入的query进行搜索
2. 对用户输入进行QueryRewriter处理后进行搜索
3. 对比两者的相关性得分
"""

import asyncio
import time
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents_v2.search.query_parser import QueryParser, parse_query
from src.agents_v2.retrieval.query_rewriter import QueryRewriter, rewrite_query
from src.agents_v2.paper_search.paper_search import PaperSearchAgent


class ComparisonTestResult:
    """比较测试结果"""
    def __init__(self):
        self.query: str = ""
        self.original_query: str = ""
        self.rewritten_query: str = ""
        self.rewrite_type: str = ""
        self.rewrite_confidence: float = 0.0
        self.rewrite_reasons: List[str] = []

        # 原始查询结果
        self.original_results: List[Dict] = []
        self.original_avg_score: float = 0.0

        # 改写后查询结果
        self.rewritten_results: List[Dict] = []
        self.rewritten_avg_score: float = 0.0

        # 对比指标
        self.relevance_improvement: float = 0.0
        self.overlap_rate: float = 0.0
        self.new_results_count: int = 0

        # 性能指标
        self.original_time: float = 0.0
        self.rewritten_time: float = 0.0


def calculate_relevance_score(paper: Dict, query: str) -> float:
    """计算论文与查询的相关性得分"""
    score = 0.0
    query_lower = query.lower()
    query_terms = set(query_lower.split())

    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()

    # 标题匹配（权重3）
    for term in query_terms:
        if term in title:
            score += 3.0
        # 摘要匹配（权重1）
        if term in abstract:
            score += 1.0

    # 关键词匹配（权重2）
    keywords = paper.get("keywords", [])
    for kw in keywords:
        if isinstance(kw, str):
            kw_lower = kw.lower()
            for term in query_terms:
                if term in kw_lower:
                    score += 2.0

    # 年份加分（近期论文）
    year = paper.get("year", 2020)
    if year >= 2024:
        score += 1.0
    elif year >= 2023:
        score += 0.5

    return score


def run_query_parser_analysis(query: str) -> Dict[str, Any]:
    """使用QueryParser分析查询"""
    parser = QueryParser()
    parsed = parser.parse(query)

    return {
        "intent": parsed.intent.value,
        "keywords": parsed.keywords,
        "entities": parsed.entities,
        "modifiers": parsed.modifiers,
        "is_temporal": parsed.is_temporal,
        "is_quantity": parsed.is_quantity,
        "language": parsed.language
    }


def run_query_rewrite(query: str) -> Dict[str, Any]:
    """使用QueryRewriter改写查询"""
    rewriter = QueryRewriter()
    result = rewriter.rewrite(query, rewrite_type="auto")

    return {
        "rewritten_query": result.rewritten_query,
        "rewrite_type": result.rewrite_type,
        "confidence": result.confidence,
        "reasons": result.reasons
    }


async def search_with_original_query(query: str, max_results: int = 10) -> Dict[str, Any]:
    """使用原始查询搜索"""
    agent = PaperSearchAgent()
    start_time = time.time()

    result = await agent.execute(query, {"max_results": max_results})

    elapsed = time.time() - start_time

    papers = result.get("papers", [])
    scores = [calculate_relevance_score(p, query) for p in papers]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    return {
        "papers": papers,
        "count": len(papers),
        "avg_score": avg_score,
        "time": elapsed,
        "scores": scores
    }


async def search_with_rewritten_query(query: str, max_results: int = 10) -> Dict[str, Any]:
    """使用改写后的查询搜索"""
    rewriter = QueryRewriter()
    rewrite_result = rewriter.rewrite(query, rewrite_type="auto")
    rewritten_query = rewrite_result.rewritten_query

    # 如果查询未改变，使用原始查询搜索（复用结果）
    if rewritten_query == query:
        agent = PaperSearchAgent()
        start_time = time.time()
        result = await agent.execute(query, {"max_results": max_results})
        elapsed = time.time() - start_time

        papers = result.get("papers", [])
        scores = [calculate_relevance_score(p, query) for p in papers]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        return {
            "papers": papers,
            "count": len(papers),
            "avg_score": avg_score,
            "time": elapsed,
            "scores": scores,
            "rewritten_query": query,
            "unchanged": True
        }

    agent = PaperSearchAgent()
    start_time = time.time()

    result = await agent.execute(rewritten_query, {"max_results": max_results})

    elapsed = time.time() - start_time

    papers = result.get("papers", [])
    scores = [calculate_relevance_score(p, rewritten_query) for p in papers]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    return {
        "papers": papers,
        "count": len(papers),
        "avg_score": avg_score,
        "time": elapsed,
        "scores": scores,
        "rewritten_query": rewritten_query,
        "unchanged": False
    }


def calculate_overlap(original_papers: List[Dict], rewritten_papers: List[Dict]) -> float:
    """计算两个结果集的overlap率"""
    if not original_papers or not rewritten_papers:
        return 0.0

    original_titles = set(p.get("title", "").lower() for p in original_papers)
    rewritten_titles = set(p.get("title", "").lower() for p in rewritten_papers)

    overlap = original_titles & rewritten_titles
    return len(overlap) / min(len(original_titles), len(rewritten_titles)) if min(len(original_titles), len(rewritten_titles)) > 0 else 0.0


def count_new_results(original_papers: List[Dict], rewritten_papers: List[Dict]) -> int:
    """计算改写后新增的结果数量"""
    if not original_papers or not rewritten_papers:
        return len(rewritten_papers)

    original_titles = set(p.get("title", "").lower() for p in original_papers)
    new_count = 0

    for p in rewritten_papers:
        title = p.get("title", "").lower()
        if title not in original_titles:
            new_count += 1

    return new_count


async def run_comparison_test(query: str) -> ComparisonTestResult:
    """运行单个查询的对比测试"""
    result = ComparisonTestResult()
    result.query = query
    result.original_query = query

    # 1. QueryParser分析
    parser_analysis = run_query_parser_analysis(query)

    # 2. QueryRewriter改写
    rewrite_analysis = run_query_rewrite(query)
    result.rewritten_query = rewrite_analysis["rewritten_query"]
    result.rewrite_type = rewrite_analysis["rewrite_type"]
    result.rewrite_confidence = rewrite_analysis["confidence"]
    result.rewrite_reasons = rewrite_analysis["reasons"]

    # 3. 原始查询搜索
    original_search = await search_with_original_query(query)
    result.original_results = original_search["papers"]
    result.original_avg_score = original_search["avg_score"]
    result.original_time = original_search["time"]

    # 4. 改写后查询搜索
    rewritten_search = await search_with_rewritten_query(query)
    result.rewritten_results = rewritten_search["papers"]
    result.rewritten_avg_score = rewritten_search["avg_score"]
    result.rewritten_time = rewritten_search["time"]

    # 5. 计算对比指标
    if result.original_avg_score > 0:
        result.relevance_improvement = (result.rewritten_avg_score - result.original_avg_score) / result.original_avg_score * 100
    else:
        result.relevance_improvement = 0.0

    result.overlap_rate = calculate_overlap(result.original_results, result.rewritten_results)
    result.new_results_count = count_new_results(result.original_results, result.rewritten_results)

    return result


def format_result_for_report(result: ComparisonTestResult) -> str:
    """将测试结果格式化为报告内容"""
    lines = []

    lines.append(f"## 测试查询: \"{result.query}\"")
    lines.append("")

    # 查询改写信息
    lines.append("### 查询改写信息")
    lines.append("")
    lines.append(f"| 项目 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 原始查询 | {result.original_query} |")
    lines.append(f"| 改写后查询 | {result.rewritten_query} |")
    lines.append(f"| 改写类型 | {result.rewrite_type} |")
    lines.append(f"| 置信度 | {result.rewrite_confidence:.2f} |")
    lines.append(f"| 改写原因 | {', '.join(result.rewrite_reasons) if result.rewrite_reasons else '无'} |")
    lines.append("")

    # 搜索结果对比
    lines.append("### 搜索结果对比")
    lines.append("")
    lines.append(f"| 指标 | 原始查询 | 改写后查询 | 变化 |")
    lines.append(f"|------|---------|-----------|------|")
    lines.append(f"| 结果数量 | {len(result.original_results)} | {len(result.rewritten_results)} | {len(result.rewritten_results) - len(result.original_results):+d} |")
    lines.append(f"| 平均相关性得分 | {result.original_avg_score:.2f} | {result.rewritten_avg_score:.2f} | {result.relevance_improvement:+.1f}% |")
    lines.append(f"| 搜索耗时 | {result.original_time:.2f}s | {result.rewritten_time:.2f}s | {result.rewritten_time - result.original_time:+.2f}s |")
    lines.append(f"| 结果重叠率 | - | {result.overlap_rate:.1%} | - |")
    lines.append(f"| 新增结果数 | - | {result.new_results_count} | - |")
    lines.append("")

    # Top 5 结果对比
    lines.append("### Top 5 结果对比")
    lines.append("")
    lines.append("**原始查询结果：**")
    for i, paper in enumerate(result.original_results[:5], 1):
        score = calculate_relevance_score(paper, result.original_query)
        lines.append(f"{i}. {paper.get('title', 'N/A')[:60]}... (得分: {score:.1f})")
    lines.append("")

    if not rewritten_search.get("unchanged", False):
        lines.append("**改写后查询结果：**")
        for i, paper in enumerate(result.rewritten_results[:5], 1):
            score = calculate_relevance_score(paper, result.rewritten_query)
            lines.append(f"{i}. {paper.get('title', 'N/A')[:60]}... (得分: {score:.1f})")
    else:
        lines.append("**改写后查询结果：** 查询未改变，使用相同结果")
        for i, paper in enumerate(result.rewritten_results[:5], 1):
            score = calculate_relevance_score(paper, result.rewritten_query)
            lines.append(f"{i}. {paper.get('title', 'N/A')[:60]}... (得分: {score:.1f})")
    lines.append("")

    return "\n".join(lines)


# 全局变量用于存储上一次搜索结果
rewritten_search = {"unchanged": False}


async def main():
    """主函数"""
    print("=" * 60)
    print("Query Rewrite Comparison Test")
    print("查询改写效果对比测试")
    print("=" * 60)
    print()

    # 测试查询列表
    test_queries = [
        "attention is all you need",
        "BERT pre-training",
        "GPT-3 language model",
        "neural network machine learning",
        "deep learning for computer vision",
    ]

    all_results = []

    for query in test_queries:
        print(f"\n测试查询: \"{query}\"")
        print("-" * 40)

        result = await run_comparison_test(query)
        all_results.append(result)

        # 保存全局引用
        global rewritten_search
        rewritten_search = {"unchanged": result.rewritten_query == result.original_query}

        print(f"  原始查询: {result.original_query}")
        print(f"  改写后查询: {result.rewritten_query}")
        print(f"  改写类型: {result.rewrite_type}")
        print(f"  原始结果: {len(result.original_results)} 篇, 平均得分: {result.original_avg_score:.2f}")
        print(f"  改写后结果: {len(result.rewritten_results)} 篇, 平均得分: {result.rewritten_avg_score:.2f}")
        print(f"  相关性变化: {result.relevance_improvement:+.1f}%")
        print(f"  结果重叠率: {result.overlap_rate:.1%}")
        print(f"  新增结果: {result.new_results_count} 篇")

        await asyncio.sleep(1)  # 避免请求过快

    # 生成报告
    report_lines = []
    report_lines.append("# Query Rewrite Comparison Test Report")
    report_lines.append("")
    report_lines.append(f"**测试日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**测试查询数**: {len(test_queries)}")
    report_lines.append("")

    # 汇总统计
    total_original_score = sum(r.original_avg_score for r in all_results)
    total_rewritten_score = sum(r.rewritten_avg_score for r in all_results)
    total_improvement = ((total_rewritten_score - total_original_score) / total_original_score * 100) if total_original_score > 0 else 0

    report_lines.append("## 汇总统计")
    report_lines.append("")
    report_lines.append(f"| 指标 | 值 |")
    report_lines.append(f"|------|-----|")
    report_lines.append(f"| 总测试查询数 | {len(all_results)} |")
    report_lines.append(f"| 平均原始得分 | {total_original_score / len(all_results):.2f} |")
    report_lines.append(f"| 平均改写后得分 | {total_rewritten_score / len(all_results):.2f} |")
    report_lines.append(f"| 整体相关性变化 | {total_improvement:+.1f}% |")
    report_lines.append(f"| 查询改写启用率 | {sum(1 for r in all_results if r.rewritten_query != r.original_query) / len(all_results):.1%} |")
    report_lines.append("")

    # 详细结果
    report_lines.append("## 详细测试结果")
    report_lines.append("")

    for result in all_results:
        report_lines.append(format_result_for_report(result))
        report_lines.append("---")
        report_lines.append("")

    # 结论
    report_lines.append("## 结论与分析")
    report_lines.append("")

    # 计算各类改写类型分布
    rewrite_types = {}
    for r in all_results:
        rt = r.rewrite_type
        rewrite_types[rt] = rewrite_types.get(rt, 0) + 1

    report_lines.append("### 改写类型分布")
    report_lines.append("")
    for rt, count in rewrite_types.items():
        report_lines.append(f"- {rt}: {count} 次")
    report_lines.append("")

    # 分析
    report_lines.append("### 分析")
    report_lines.append("")
    report_lines.append("1. **查询改写效果**：")
    if total_improvement > 0:
        report_lines.append(f"   - 查询改写后整体相关性提升了 **{total_improvement:.1f}%**")
        report_lines.append("   - 这表明 QueryRewriter 能够有效提升搜索结果的相关性")
    elif total_improvement < 0:
        report_lines.append(f"   - 查询改写后整体相关性下降了 **{abs(total_improvement):.1f}%**")
        report_lines.append("   - 部分改写可能过于激进或方向不正确，需要调整改写策略")
    else:
        report_lines.append("   - 查询改写后整体相关性无明显变化")
        report_lines.append("   - 可能原因：改写类型为 'none' 或 'reformulation' 未大幅改变查询")
    report_lines.append("")

    report_lines.append("2. **结果重叠率分析**：")
    avg_overlap = sum(r.overlap_rate for r in all_results) / len(all_results)
    report_lines.append(f"   - 平均结果重叠率: **{avg_overlap:.1%}**")
    if avg_overlap > 0.7:
        report_lines.append("   - 重叠率较高，说明改写主要影响了排序而非结果集本身")
    elif avg_overlap > 0.3:
        report_lines.append("   - 重叠率适中，改写带来了一部分新结果")
    else:
        report_lines.append("   - 重叠率较低，改写引入了较多新结果")
    report_lines.append("")

    report_lines.append("3. **新增结果分析**：")
    total_new = sum(r.new_results_count for r in all_results)
    report_lines.append(f"   - 总新增结果数: **{total_new}** 篇")
    avg_new = total_new / len(all_results)
    report_lines.append(f"   - 平均每查询新增: **{avg_new:.1f}** 篇")
    report_lines.append("")

    report_lines.append("### 建议")
    report_lines.append("")
    report_lines.append("1. 对于**短查询**（<10字符），建议启用查询扩展以获得更多结果")
    report_lines.append("2. 对于**复杂查询**（多主题），建议启用查询分解")
    report_lines.append("3. 对于**中英混合查询**，建议启用语言统一功能")
    report_lines.append("4. 可以通过环境变量 `ENABLE_QUERY_REWRITE` 控制是否启用查询改写")

    # 保存报告
    report_content = "\n".join(report_lines)

    output_dir = r"D:\pycharmprojects\pythonProject1\docs\test_results"
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "query_rewrite_comparison_report.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print("\n" + "=" * 60)
    print(f"测试完成！报告已保存至: {output_file}")
    print("=" * 60)

    return all_results


if __name__ == "__main__":
    asyncio.run(main())