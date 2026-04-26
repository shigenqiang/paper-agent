"""
论文Agent系统 - 演示脚本

使用方法:
1. 安装依赖: pip install -r requirements.txt
2. 设置环境变量: set OPENAI_API_KEY=your_key
3. 运行脚本: python src/agents_v2/demo.py

功能演示:
- 意图路由 (IntentRouter)
- 论文搜索 (PaperSearchAgent)
- 完整论文流程 (MasterSupervisor)
"""
import asyncio
import logging
import os

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_intent_router():
    """演示意图路由功能"""
    print("\n" + "="*60)
    print("演示1: 意图路由 (IntentRouter)")
    print("="*60)

    from unified import IntentRouter

    router = IntentRouter()

    test_requests = [
        "我想写一篇关于深度学习优化的论文",
        "帮我搜索一下最新的Transformer论文",
        "生成一个开题报告",
        "润色一下我的摘要",
    ]

    for req in test_requests:
        print(f"\n请求: {req}")
        result = await router.route(req)
        print(f"  识别意图: {result['intent']}")
        print(f"  建议Agent: {result['suggested_agents']}")
        print(f"  处理模式: {result['mode']}")


async def demo_paper_search():
    """演示论文搜索功能"""
    print("\n" + "="*60)
    print("演示2: 论文搜索 (PaperSearchAgent)")
    print("="*60)

    from qa import PaperSearchAgent

    search_agent = PaperSearchAgent()

    # 搜索arXiv论文
    print("\n搜索 arXiv 论文 (深度学习优化)...")
    result = await search_agent.execute(
        "deep learning optimization",
        {"source": "arxiv", "max_results": 5}
    )

    papers = result.get("papers", [])
    print(f"  找到 {len(papers)} 篇论文")
    for i, paper in enumerate(papers[:3], 1):
        print(f"  {i}. {paper.get('title', 'N/A')[:60]}...")

    # 搜索PubMed论文
    print("\n搜索 PubMed 论文 (机器学习医疗)...")
    result = await search_agent.execute(
        "machine learning healthcare",
        {"source": "pubmed", "max_results": 5}
    )

    papers = result.get("papers", [])
    print(f"  找到 {len(papers)} 篇论文")
    for i, paper in enumerate(papers[:3], 1):
        print(f"  {i}. {paper.get('title', 'N/A')[:60]}...")


async def demo_master_supervisor():
    """演示完整论文流程"""
    print("\n" + "="*60)
    print("演示3: 完整论文流程 (MasterSupervisor)")
    print("="*60)

    from unified import MasterSupervisor

    # 创建Supervisor
    supervisor = MasterSupervisor()

    # 注册所有Agent
    supervisor.register_problem_agents()
    supervisor.register_pipeline_agents()
    supervisor.register_writing_agents()

    print("\n已注册Agent数量:")
    print(f"  问题导向Agent: {len([k for k in supervisor.agents.keys() if '_refiner' in k or '_mapper' in k or '_advisor' in k or '_builder' in k or '_diff' in k or '_deepener' in k or '_formatter' in k or '_polisher' in k or '_checker' in k])}")
    print(f"  Pipeline Agent: {len([k for k in supervisor.agents.keys() if k in ['topic', 'literature', 'thesis', 'outline', 'draft', 'editor', 'reviewer']])}")
    print(f"  Writing Agent: {len([k for k in supervisor.agents.keys() if k in ['literature_review', 'outline_generator', 'draft_generator', 'report_refiner', 'proposal_generator', 'reference_processor', 'smart_reviser', 'language_polisher_writing']])}")

    # 运行选题流程
    print("\n运行选题阶段 (topic)...")
    result = await supervisor.run(
        "full_paper",
        {"topic": "深度学习模型压缩"}
    )

    print(f"\n流程执行完成:")
    print(f"  成功: {result.get('success', False)}")
    print(f"  已完成阶段: {result.get('phases_completed', [])}")
    print(f"  最终质量: {result.get('final_quality', 0):.2f}")


async def demo_writing_agent():
    """演示Writing Agent"""
    print("\n" + "="*60)
    print("演示4: Writing Agent - 开题报告生成")
    print("="*60)

    from unified import MasterSupervisor

    supervisor = MasterSupervisor()
    supervisor.register_writing_agents()

    # 使用ProposalGeneratorAgent生成开题报告
    if "proposal_generator" in supervisor.agents:
        agent = supervisor.agents["proposal_generator"]
        result = await agent.execute({
            "topic": "基于深度学习的图像超分辨率算法研究",
            "research_background": "图像超分辨率在医学影像、卫星遥感等领域有重要应用",
            "research_significance": "提高图像质量对下游任务有显著帮助"
        })

        print(f"\n开题报告生成结果:")
        print(f"  成功: {result.success}")
        print(f"  质量评分: {result.quality_score:.2f}")
        if result.result:
            proposal = result.result.get("proposal", "")
            print(f"  开题报告预览: {proposal[:200]}...")
    else:
        print("  proposal_generator agent 未注册")


async def main():
    """主函数 - 运行所有演示"""
    print("\n" + "#"*60)
    print("# 论文Agent系统 - 功能演示")
    print("#"*60)

    # 检查API Key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n警告: 未设置 OPENAI_API_KEY 环境变量")
        print("  LLM相关功能可能无法正常工作")
        print("  请设置: export OPENAI_API_KEY=your_key")

    try:
        # 演示1: 意图路由 (不需要API key)
        await demo_intent_router()

        # 演示2: 论文搜索 (使用真实API)
        await demo_paper_search()

        # 演示3: MasterSupervisor (需要API key)
        await demo_master_supervisor()

        # 演示4: Writing Agent (需要API key)
        await demo_writing_agent()

        print("\n" + "#"*60)
        print("# 演示完成!")
        print("#"*60)

    except Exception as e:
        logger.error(f"演示过程出错: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
