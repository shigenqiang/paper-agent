"""
使用示例 - 常见使用场景

这些示例展示如何使用论文Agent系统
"""
import asyncio
from src.agents_v2.paper_agents import TopicAgent, LiteratureAgent, ThesisAgent
from src.agents_v2.problem_oriented import DiscussionDeepenerAgent, LanguagePolisherAgent
from src.agents_v2.writing import ProposalGeneratorAgent, DraftGeneratorAgent
from src.agents_v2.unified import MasterSupervisor, IntentRouter


# ============ 示例1: 从选题到初稿 ============

async def full_paper_flow():
    """
    完整论文写作流程示例

    从选题开始，经过文献综述、Thesis凝练，最终生成初稿
    """
    print("=" * 60)
    print("示例1: 完整论文写作流程")
    print("=" * 60)

    supervisor = MasterSupervisor()
    supervisor.register_pipeline_agents()
    supervisor.register_writing_agents()

    result = await supervisor.run("full_paper", {
        "topic": "基于深度学习的医学图像分割算法研究"
    })

    print(f"成功: {result['success']}")
    print(f"完成阶段: {result['phases_completed']}")
    print(f"最终质量: {result.get('final_quality', 0):.2f}")

    return result


# ============ 示例2: 单独使用选题Agent ============

async def topic_selection_example():
    """
    选题示例

    当用户有一个研究想法但不确定如何聚焦时使用
    """
    print("=" * 60)
    print("示例2: 选题")
    print("=" * 60)

    agent = TopicAgent()

    result = await agent.execute({
        "user_request": "我想研究人工智能在教育领域的应用"
    })

    print(f"成功: {result.success}")
    print(f"质量评分: {result.quality_score:.2f}")

    if result.result:
        topic = result.result.get("selected_topic", {})
        print(f"\n选定主题: {topic.get('title', 'N/A')}")
        print(f"描述: {topic.get('description', 'N/A')}")
        print(f"研究范围: {topic.get('scope', 'N/A')}")

    return result


# ============ 示例3: 文献搜索与综述 ============

async def literature_review_example():
    """
    文献综述示例

    搜索并分析相关文献
    """
    print("=" * 60)
    print("示例3: 文献综述")
    print("=" * 60)

    agent = LiteratureAgent()

    result = await agent.execute({
        "topic": "深度学习图像分割",
        "research_question": "U-Net在医学图像分割中的最新进展"
    })

    print(f"成功: {result.success}")
    print(f"找到论文: {result.result.get('total_found', 0)}")
    print(f"深度分析: {result.result.get('total_analyzed', 0)}")

    gaps = result.result.get("research_gaps", [])
    print(f"\n识别研究空白 ({len(gaps)}个):")
    for i, gap in enumerate(gaps[:3], 1):
        print(f"  {i}. {gap.get('description', 'N/A')}")

    return result


# ============ 示例4: 意图路由 ============

async def intent_routing_example():
    """
    意图路由示例

    根据用户输入自动识别意图并路由到合适的Agent
    """
    print("=" * 60)
    print("示例4: 意图路由")
    print("=" * 60)

    router = IntentRouter()

    test_requests = [
        "我想写一篇关于深度学习优化的论文",
        "帮我搜索最新的Transformer论文",
        "润色一下我的摘要",
        "生成一个开题报告",
    ]

    for req in test_requests:
        result = await router.route(req)
        print(f"\n请求: {req}")
        print(f"  识别意图: {result['intent']}")
        print(f"  建议Agent: {result['suggested_agents']}")
        print(f"  处理模式: {result['mode']}")


# ============ 示例5: 论文局部修改 ============

async def paper_revision_example():
    """
    论文局部修改示例

    使用问题导向Agent修复论文的特定部分
    """
    print("=" * 60)
    print("示例5: 论文局部修改")
    print("=" * 60)

    # 讨论深化Agent
    deepener = DiscussionDeepenerAgent()

    discussion_input = """
    我们的方法在准确率上达到了95%，比基线方法高5个百分点。
    实验结果表明，我们的方法在大规模数据集上表现良好。
    """

    result = await deepener.diagnose({
        "results": "准确率95%，比基线高5个百分点",
        "discussion": discussion_input,
        "literature": []
    })

    print(f"诊断成功: {result.success}")
    print(f"建议:")
    for rec in result.result.get("recommendations", [])[:3]:
        print(f"  - {rec}")


# ============ 示例6: 开题报告生成 ============

async def proposal_generation_example():
    """
    开题报告生成示例

    为研究课题生成完整的开题报告
    """
    print("=" * 60)
    print("示例6: 开题报告生成")
    print("=" * 60)

    agent = ProposalGeneratorAgent()

    result = await agent.execute({
        "topic": "基于深度学习的医学影像诊断研究",
        "research_background": """
        医学影像诊断是临床诊断的重要组成部分。
        深度学习技术的发展为医学影像分析带来了新的机遇。
        """,
        "research_significance": """
        提高诊断准确率，减少漏诊和误诊，
        辅助医生做出更准确的诊断决策。
        """
    })

    print(f"成功: {result.success}")
    print(f"质量评分: {result.quality_score:.2f}")

    if result.result:
        proposal = result.result.get("proposal", "")
        print(f"\n开题报告预览:\n{proposal[:500]}...")


# ============ 示例7: 使用缓存优化性能 ============

async def cached_search_example():
    """
    带缓存的搜索示例

    使用缓存减少重复的LLM调用
    """
    print("=" * 60)
    print("示例7: 带缓存的搜索")
    print("=" * 60)

    from src.agents_v2.unified.cache import LLMLCallOptimizer

    optimizer = LLMLCallOptimizer(enable_cache=True)

    # 模拟LLM调用
    async def mock_llm(prompt):
        print(f"  [LLM调用] {prompt[:50]}...")
        await asyncio.sleep(0.1)  # 模拟延迟
        return f"Result for: {prompt[:30]}..."

    prompts = [
        "深度学习优化方法",
        "深度学习优化方法",  # 重复
        "图像分割算法",
        "深度学习优化方法",  # 再重复
    ]

    results = await optimizer.batch_call(mock_llm, prompts)

    print(f"\n生成了 {len(results)} 个结果")
    print(f"缓存统计: {optimizer.get_cache_stats()}")

    return results


# ============ 主函数 ============

async def main():
    """运行所有示例"""
    print("\n" + "#" * 60)
    print("# 论文Agent系统 - 使用示例")
    print("#" * 60)

    try:
        # 运行所有示例
        await full_paper_flow()
        print("\n")

        await topic_selection_example()
        print("\n")

        await literature_review_example()
        print("\n")

        await intent_routing_example()
        print("\n")

        await paper_revision_example()
        print("\n")

        await proposal_generation_example()
        print("\n")

        await cached_search_example()

    except Exception as e:
        print(f"\n示例执行出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "#" * 60)
    print("# 示例完成")
    print("#" * 60)


if __name__ == "__main__":
    asyncio.run(main())
