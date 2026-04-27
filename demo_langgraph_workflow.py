"""
LangGraph 工作流演示脚本

演示如何使用新的 LangGraph 工作流进行论文调研。
"""
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def demo_basic_workflow():
    """演示基础工作流（无 LLM）"""
    print("\n" + "=" * 60)
    print("[演示] LangGraph 工作流 - 基础模式（无 LLM）")
    print("=" * 60)

    from agents_v2.langgraph_workflow import create_workflow

    # 创建工作流（不使用 LLM，使用规则生成）
    workflow = create_workflow(
        llm=None,
        sources=["arxiv"],  # 仅使用 arXiv 以加快速度
        top_k=10,
        max_iterations=1,
    )

    # 运行工作流
    query = "attention mechanism in neural networks"
    print(f"\n[查询]: {query}")
    print("-" * 60)

    try:
        result = workflow.run(
            query=query,
            user_id="demo_user",
            session_id="demo_session",
            max_iterations=1,
            stream=True,
        )

        # 打印结果
        print("\n[结果摘要]")
        print(f"  搜索到论文: {len(result.get('papers', []))} 篇")
        print(f"  筛选后论文: {len(result.get('selected_papers', []))} 篇")

        selected = result.get("selected_papers", [])
        if selected:
            print(f"\n[Top 5 论文]:")
            for i, paper in enumerate(selected[:5], 1):
                print(f"  {i}. [{paper.relevance_score:.2f}] {paper.title}")
                if paper.authors:
                    authors_str = ", ".join(paper.authors[:2])
                    if len(paper.authors) > 2:
                        authors_str += " et al."
                    print(f"     {authors_str} ({paper.year})")

        outline = result.get("outline", {})
        if outline.get("title"):
            print(f"\n[论文标题]: {outline['title']}")
            sections = outline.get("sections", [])
            if sections:
                print(f"[章节数量]: {len(sections)}")
                for i, section in enumerate(sections[:3], 1):
                    print(f"  {i}. {section.get('title', 'Untitled')}")

        draft = result.get("draft", "")
        if draft:
            print(f"\n[草稿长度]: {len(draft)} 字符")
            print(f"[草稿预览]:")
            print(draft[:500] + "..." if len(draft) > 500 else draft)

        print("\n[完成] 基础工作流演示")

    except Exception as e:
        logger.error(f"工��流执行失败: {e}", exc_info=True)
        print(f"\n[错误] {e}")


def demo_state_management():
    """演示状态管理"""
    print("\n" + "=" * 60)
    print("[演示] 状态管理")
    print("=" * 60)

    from agents_v2.langgraph_workflow import PaperAgentState, Paper, create_initial_state

    # 创建初始状态
    state = create_initial_state(
        user_query="deep learning",
        user_id="test_user",
        session_id="test_session",
        max_iterations=3,
    )

    print(f"\n[初始状态]")
    print(f"  查询: {state.user_query}")
    print(f"  用户ID: {state.user_id}")
    print(f"  会话ID: {state.session_id}")
    print(f"  最大迭代: {state.max_iterations}")
    print(f"  当前阶段: {state.current_phase}")

    # 添加论文
    paper1 = Paper(
        id="arxiv:2301.12345",
        title="Attention Is All You Need",
        authors=["Vaswani", "Shazeer", "Parmar"],
        abstract="We propose a new architecture...",
        url="https://arxiv.org/abs/2301.12345",
        year=2017,
        citations=50000,
    )

    state.papers = [paper1]
    state.selected_papers = [paper1]

    print(f"\n[更新后状态]")
    print(f"  论文数量: {len(state.papers)}")
    print(f"  选中论文: {len(state.selected_papers)}")
    print(f"  第一篇论文: {state.papers[0].title}")

    print("\n[完成] 状态管理演示")


def demo_individual_agents():
    """演示单个 Agent 节点"""
    print("\n" + "=" * 60)
    print("[演示] 单个 Agent 节点")
    print("=" * 60)

    from agents_v2.langgraph_workflow import (
        CrawlerAgent,
        SelectorAgent,
        create_initial_state,
    )

    # 创建初始状态
    state = create_initial_state(
        user_query="transformer architecture",
        max_iterations=1,
    )

    # 测试 Crawler
    print("\n[测试] CrawlerAgent")
    crawler = CrawlerAgent(sources=["arxiv"], max_per_source=5)
    try:
        state = crawler.execute(state)
        print(f"  找到论文: {len(state.papers)} 篇")
        if state.papers:
            print(f"  第一篇: {state.papers[0].title}")
    except Exception as e:
        print(f"  错误: {e}")

    # 测试 Selector
    if state.papers:
        print("\n[测试] SelectorAgent")
        selector = SelectorAgent(top_k=3, enable_reranking=False)
        try:
            state = selector.execute(state)
            print(f"  筛选后: {len(state.selected_papers)} 篇")
            for i, paper in enumerate(state.selected_papers, 1):
                print(f"  {i}. [{paper.relevance_score:.2f}] {paper.title[:60]}...")
        except Exception as e:
            print(f"  错误: {e}")

    print("\n[完成] 单个 Agent 演示")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print(" LangGraph 工作流演示 - Paper Agent v11.0")
    print("=" * 80)

    demos = [
        ("1", "状态管理", demo_state_management),
        ("2", "单个 Agent 节点", demo_individual_agents),
        ("3", "完整工作流（基础模式）", demo_basic_workflow),
    ]

    print("\n可用演示:")
    for num, name, _ in demos:
        print(f"  {num}. {name}")
    print("  0. 运行所有演示")

    choice = input("\n请选择演示 (0-3): ").strip()

    if choice == "0":
        for _, _, demo_func in demos:
            try:
                demo_func()
            except Exception as e:
                logger.error(f"演示失败: {e}", exc_info=True)
    else:
        for num, _, demo_func in demos:
            if choice == num:
                try:
                    demo_func()
                except Exception as e:
                    logger.error(f"演示失败: {e}", exc_info=True)
                break
        else:
            print(f"无效选择: {choice}")

    print("\n" + "=" * 80)
    print("[结束] 演示完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
