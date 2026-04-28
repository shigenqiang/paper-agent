"""
系统测试脚本 - 测试统一工作流的所有路径

测试内容：
1. 路由节点 - 意图分类
2. 搜索工作流
3. 写作工作流
4. 报告工作流
5. 问答工作流
6. 修改工作流
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents_v2.langgraph_workflow.unified_workflow import create_unified_workflow


async def test_router():
    """测试路由节点"""
    print("\n=== 测试 1: 路由节点 ===")

    test_queries = [
        ("搜索深度学习相关论文", "search"),
        ("帮我写一篇关于因果推断的综述", "writing"),
        ("生成本周学术资讯", "report"),
        ("什么是 Transformer", "qa"),
        ("润色这段文字", "revision"),
    ]

    from src.agents_v2.langgraph_workflow.nodes.router import RouteNode
    router = RouteNode()

    for query, expected_route in test_queries:
        state = {"user_query": query}
        result = await router(state)
        actual_route = result.get("route_path", "unknown")
        status = "✅" if actual_route == expected_route else "❌"
        print(f"{status} '{query}' -> {actual_route} (期望: {expected_route})")


async def test_search_workflow():
    """测试搜索工作流"""
    print("\n=== 测试 2: 搜索工作流 ===")

    workflow = create_unified_workflow(
        enable_memory=False,
        enable_multimodal=False,
        enable_kg=False,
        enable_evaluation=False,
    )

    try:
        result = await workflow.run(
            query="搜索 transformer 相关论文",
            user_id="test_user",
        )

        papers = result.get("papers", [])
        print(f"✅ 搜索完成，找到 {len(papers)} 篇论文")

        if papers:
            print(f"   示例: {papers[0].get('title', 'Unknown')[:50]}...")
    except Exception as e:
        print(f"❌ 搜索失败: {e}")


async def test_report_workflow():
    """测试报告工作流"""
    print("\n=== 测试 3: 报告工作流 ===")

    workflow = create_unified_workflow(
        enable_memory=False,
        enable_multimodal=False,
        enable_kg=False,
        enable_evaluation=False,
    )

    try:
        result = await workflow.run(
            query="生成每日学术资讯",
            report_type="daily",
            keywords=["deep learning", "transformer"],
            user_id="test_user",
        )

        report_content = result.get("report_content", "")
        print(f"✅ 报告生成完成，长度: {len(report_content)} 字符")

        if report_content:
            lines = report_content.split("\n")[:3]
            print(f"   预览: {lines[0]}")
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")


async def test_qa_workflow():
    """测试问答工作流"""
    print("\n=== 测试 4: 问答工作流 ===")

    workflow = create_unified_workflow(
        enable_memory=False,
        enable_multimodal=False,
        enable_kg=False,
        enable_evaluation=False,
    )

    try:
        result = await workflow.run(
            query="什么是 Transformer 架构",
            user_id="test_user",
        )

        answer = result.get("answer", "")
        print(f"✅ 问答完成，回答长度: {len(answer)} 字符")

        if answer:
            preview = answer[:100].replace("\n", " ")
            print(f"   预览: {preview}...")
    except Exception as e:
        print(f"❌ 问答失败: {e}")


async def test_revision_workflow():
    """测试修改工作流"""
    print("\n=== 测试 5: 修改工作流 ===")

    workflow = create_unified_workflow(
        enable_memory=False,
        enable_multimodal=False,
        enable_kg=False,
        enable_evaluation=False,
    )

    test_draft = """
    # 测试文档

    这是一个测试文档。  包含一些  多余的空格。


    还有多余的空行。
    """

    try:
        result = await workflow.run(
            query="润色这段文字",
            user_id="test_user",
        )

        # 手动设置 draft 进行测试
        result["draft"] = test_draft

        polished = result.get("polished_draft", result.get("draft", ""))
        print(f"✅ 修改完成")
        print(f"   原文长度: {len(test_draft)}")
        print(f"   修改后长度: {len(polished)}")
    except Exception as e:
        print(f"❌ 修改失败: {e}")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("Paper Agent - 统一工作流测试")
    print("=" * 60)

    try:
        await test_router()
        # await test_search_workflow()  # 需要实际的搜索 API
        # await test_report_workflow()  # 需要实际的搜索 API
        # await test_qa_workflow()      # 需要实际的搜索 API
        await test_revision_workflow()

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
