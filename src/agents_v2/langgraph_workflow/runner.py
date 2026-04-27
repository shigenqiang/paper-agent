"""
LangGraph 工作流运行入口

提供 CLI 和程序化两种运行方式。

CLI 使用:
    python -m src.agents_v2.langgraph_workflow.runner "your query"

程序化使用:
    from agents_v2.langgraph_workflow.runner import run_query
    result = run_query("deep learning in medical imaging")
"""
import logging
import time
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_query(
    query: str,
    llm=None,
    user_id: str = "",
    session_id: str = "",
    max_iterations: int = 3,
    selector_top_k: int = 20,
) -> dict:
    """运行论文调研工作流

    Args:
        query: 用户查询
        llm: LangChain LLM 实例（可选）
        user_id: 用户 ID
        session_id: 会话 ID
        max_iterations: 最大写作迭代次数
        selector_top_k: 筛选论文数量

    Returns:
        包含最终状态的字典
    """
    from .workflow import create_workflow

    workflow = create_workflow(
        llm=llm,
        selector_top_k=selector_top_k,
        max_iterations=max_iterations,
    )

    total_start = time.time()
    logger.info(f"[Runner] 开始查询: {query}")

    result = workflow.run(
        query=query,
        user_id=user_id,
        session_id=session_id,
        max_iterations=max_iterations,
        stream=False,
    )

    total_elapsed = time.time() - total_start
    logger.info(f"[Runner] 工作流完成，总耗时 {total_elapsed:.2f}s")

    return result


def main():
    """CLI 入口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python runner.py <query>")
        print("Example: python runner.py 'deep learning in medical imaging'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"\n[Paper Agent] 查询: {query}")
    print("=" * 60)

    result = run_query(query)

    # 打印结果摘要
    papers = result.get("papers", [])
    selected = result.get("selected_papers", [])
    outline = result.get("outline", {})
    draft = result.get("draft", "")
    feedback = result.get("feedback", [])
    iteration = result.get("iteration", 0)

    print(f"\n[结果摘要]")
    print(f"  搜索到论文: {len(papers)} 篇")
    print(f"  筛选后论文: {len(selected)} 篇")
    print(f"  大纲章节: {len(outline.get('sections', []))} 个")
    print(f"  草稿长度: {len(draft)} 字符")
    print(f"  修改轮次: {iteration}")
    print(f"  反馈数量: {len(feedback)} 条")

    if selected:
        print(f"\n[Top 5 论文]:")
        for i, paper in enumerate(selected[:5], 1):
            print(f"  {i}. [{paper.relevance_score:.2f}] {paper.title}")
            if paper.authors:
                print(f"     {', '.join(paper.authors[:3])} ({paper.year})")

    if outline.get("title"):
        print(f"\n[论文标题]: {outline['title']}")

    print(f"\n{'=' * 60}")
    print("[完成]")


if __name__ == "__main__":
    main()
