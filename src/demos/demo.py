"""
论文Agent系统 - 演示脚本

使用方法:
1. 安装依赖: pip install -r requirements.txt
2. 设置环境变量: set OPENAI_API_KEY=your_key
3. 运行脚本: python -m src.agents_v2.demos.demo

功能演示:
- 意图路由 (IntentRouter)
- 论文搜索 (PaperSearchAgent)
- 论文写作流程 (Paper Agents)
- Writing Agent 工具
- 知识图谱 (KnowledgeGraph)
- 定时报告 (Scheduler)
- API Server 调用示例
"""
import asyncio
import logging
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

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

    from src.agents_v2.unified import IntentRouter

    router = IntentRouter()

    test_requests = [
        "我想写一篇关于深度学习优化的论文",
        "帮我搜索一下最新的Transformer论文",
        "生成一个开题报告",
        "润色一下我的摘要",
        "帮我分析这个研究方向的可行性",
    ]

    for req in test_requests:
        print(f"\n请求: {req}")
        result = await router.route(req)
        print(f"  识别意图: {result.get('intent', 'N/A')}")
        print(f"  建议Agent: {result.get('suggested_agents', [])}")
        print(f"  处理模式: {result.get('mode', 'N/A')}")


async def demo_paper_search():
    """演示论文搜索功能"""
    print("\n" + "="*60)
    print("演示2: 论文搜索 (PaperSearchAgent)")
    print("="*60)

    from src.agents_v2.paper_search import PaperSearchAgent

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
        title = paper.get('title', 'N/A')
        print(f"  {i}. {title[:60]}..." if len(title) > 60 else f"  {i}. {title}")

    # 搜索Semantic Scholar论文
    print("\n搜索 Semantic Scholar 论文 (大语言模型)...")
    result = await search_agent.execute(
        "large language model agent",
        {"source": "semantic_scholar", "max_results": 5}
    )

    papers = result.get("papers", [])
    print(f"  找到 {len(papers)} 篇论文")
    for i, paper in enumerate(papers[:3], 1):
        title = paper.get('title', 'N/A')
        print(f"  {i}. {title[:60]}..." if len(title) > 60 else f"  {i}. {title}")


async def demo_paper_agents():
    """演示Paper Agents流程"""
    print("\n" + "="*60)
    print("演示3: Paper Agents - 论文写作流程")
    print("="*60)

    from src.agents_v2.paper_agents import (
        TopicAgent,
        LiteratureAgent,
        ThesisAgent,
        OutlineAgent,
    )
    from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

    # 创建LLM配置
    llm_config = LLMConfig(
        provider="openai",
        model_name="minimax",
        temperature=0.7
    )

    # 1. 选题Agent
    print("\n[步骤1] 选题Agent (TopicAgent)")
    topic_agent = TopicAgent(llm_config)
    result = await topic_agent.execute({
        "user_request": "我想研究深度学习在自然语言处理中的应用"
    })
    print(f"  成功: {result.success}")
    if result.result:
        topics = result.result.get("topics", [])
        print(f"  建议选题: {len(topics)} 个")
        for i, topic in enumerate(topics[:2], 1):
            print(f"    {i}. {topic.get('title', 'N/A')[:50]}...")

    # 2. 文献Agent
    print("\n[步骤2] 文献Agent (LiteratureAgent)")
    literature_agent = LiteratureAgent(llm_config)
    result = await literature_agent.execute({
        "topic": "深度学习模型压缩"
    })
    print(f"  成功: {result.success}")
    if result.result:
        papers = result.result.get("papers", [])
        print(f"  相关文献: {len(papers)} 篇")

    # 3. 大纲Agent
    print("\n[步骤3] 大纲Agent (OutlineAgent)")
    outline_agent = OutlineAgent(llm_config)
    result = await outline_agent.execute({
        "topic": "深度学习模型压缩技术研究",
        "requirements": "包含模型剪枝、量化、知识蒸馏三个方面"
    })
    print(f"  成功: {result.success}")
    if result.result:
        outline = result.result.get("outline", "")
        print(f"  大纲预览: {outline[:100]}..." if len(outline) > 100 else f"  大纲: {outline}")


async def demo_writing_tools():
    """演示Writing工具"""
    print("\n" + "="*60)
    print("演示4: Writing工具")
    print("="*60)

    from src.agents_v2.writing import (
        LiteratureReviewAgent,
        OutlineGeneratorAgent,
        ProposalGeneratorAgent,
        SmartReviserAgent,
        ReflectionEngine,
        CitationGenerator,
        CitationStyle,
    )

    # 1. 文献综述Agent
    print("\n[工具1] 文献综述Agent (LiteratureReviewAgent)")
    lit_review_agent = LiteratureReviewAgent()
    result = await lit_review_agent.execute({
        "topic": "Transformer模型的发展"
    })
    print(f"  成功: {result.success}")
    if result.result:
        review = result.result.get("review", "")
        print(f"  综述预览: {review[:80]}..." if len(review) > 80 else f"  综述: {review}")

    # 2. 开题报告Agent
    print("\n[工具2] 开题报告Agent (ProposalGeneratorAgent)")
    proposal_agent = ProposalGeneratorAgent()
    result = await proposal_agent.execute({
        "topic": "基于深度学习的图像超分辨率算法研究",
        "research_background": "图像超分辨率在医学影像、卫星遥感等领域有重要应用",
        "research_significance": "提高图像质量对下游任务有显著帮助"
    })
    print(f"  成功: {result.success}")
    if result.result:
        proposal = result.result.get("proposal", "")
        print(f"  开题报告预览: {proposal[:100]}..." if len(proposal) > 100 else f"  开题报告: {proposal}")

    # 3. 引用生成器
    print("\n[工具3] 引用生成器 (CitationGenerator)")
    citation_gen = CitationGenerator()
    citations = citation_gen.generate_citations([
        {"authors": ["Vaswani", "Shazeer"], "title": "Attention is All You Need", "year": 2017, "venue": "NeurIPS"},
        {"authors": ["Devlin"], "title": "BERT: Pre-training of Deep Bidirectional Transformers", "year": 2019, "venue": "NAACL"},
    ], style=CitationStyle.APA)
    print(f"  生成引用: {len(citations)} 条")
    for c in citations:
        print(f"    - {c.formatted[:60]}...")

    # 4. 反思引擎
    print("\n[工具4] 反思引擎 (ReflectionEngine)")
    reflection_engine = ReflectionEngine()
    print(f"  反思引擎已初始化，支持多层级反思")


async def demo_knowledge_graph():
    """演示知识图谱功能"""
    print("\n" + "="*60)
    print("演示5: 知识图谱 (KnowledgeGraph)")
    print("="*60)

    try:
        from src.agents_v2.knowledge_graph import KnowledgeGraphService

        kg = KnowledgeGraphService()

        # 添加实体
        print("\n添加实体...")
        entities = [
            {"name": "Transformer", "type": "model", "properties": {"year": 2017}},
            {"name": "BERT", "type": "model", "properties": {"year": 2019}},
            {"name": "GPT", "type": "model", "properties": {"year": 2018}},
        ]
        for entity in entities:
            await kg.add_entity(entity)
            print(f"  添加: {entity['name']} ({entity['type']})")

        # 添加关系
        print("\n添加关系...")
        relations = [
            {"source": "BERT", "target": "Transformer", "type": "based_on"},
            {"source": "GPT", "target": "Transformer", "type": "based_on"},
        ]
        for rel in relations:
            await kg.add_relation(rel)
            print(f"  添加: {rel['source']} --[{rel['type']}]--> {rel['target']}")

        # 查询
        print("\n查询知识图谱...")
        result = await kg.query("Transformer相关模型")
        print(f"  查询结果: {len(result.get('entities', []))} 个实体")

    except ImportError:
        print("  知识图谱模块未安装或配置")


async def demo_scheduler():
    """演示定时任务调度"""
    print("\n" + "="*60)
    print("演示6: 定时任务调度 (Scheduler)")
    print("="*60)

    try:
        from src.agents_v2.scheduler import get_report_scheduler

        scheduler = get_report_scheduler()

        # 查看现有任务
        tasks = scheduler.list_tasks()
        print(f"\n当前任务数量: {len(tasks)}")
        for task in tasks[:3]:
            print(f"  - {task.get('name', 'N/A')}: {task.get('schedule', 'N/A')}")

        # 创建新任务示例
        print("\n创建每日报告任务示例...")
        new_task = scheduler.create_task(
            name="AI领域每日快报",
            task_type="daily_report",
            schedule="0 9 * * *",  # 每天早上9点
            keywords=["artificial intelligence", "machine learning"],
            schedule_type="cron"
        )
        print(f"  任务创建成功: {new_task.get('task_id', 'N/A')}")

    except ImportError:
        print("  调度器模块未安装或配置")


async def demo_streaming():
    """演示流式生成"""
    print("\n" + "="*60)
    print("演示7: 流式生成 (StreamingGenerator)")
    print("="*60)

    from src.agents_v2.writing import StreamingGenerator, StreamStatus

    generator = StreamingGenerator()

    print("\n流式生成示例...")
    print("  (模拟流式输出)")

    # 模拟流式生成
    chunks = [
        "深度学习",
        "是机器学习",
        "的一个分支",
        "它通过多层神经网络",
        "来学习数据的层次表示",
    ]

    for i, chunk in enumerate(chunks, 1):
        print(f"  [{i}/{len(chunks)}] {chunk}")
        await asyncio.sleep(0.3)  # 模拟生成延迟

    print("  流式生成完成!")


async def demo_api_server():
    """演示API Server调用"""
    print("\n" + "="*60)
    print("演示8: API Server 调用示例")
    print("="*60)

    import aiohttp

    base_url = "http://localhost:8000"
    api_key = os.getenv("API_KEY", "dev-api-key")
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    print(f"\nAPI服务器地址: {base_url}")
    print(f"API密钥: {api_key[:10]}...")

    # 1. 健康检查
    print("\n[API 1] 健康检查")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  状态: {data.get('status')}")
                    print(f"  版本: {data.get('version')}")
                else:
                    print(f"  请求失败: {resp.status}")
    except Exception as e:
        print(f"  连接失败: {e}")
        print("  请确保API服务器已启动: python -m src.agents_v2.api_server")
        return

    # 2. 意图路由
    print("\n[API 2] 意图路由")
    try:
        async with aiohttp.ClientSession() as session:
            data = {"user_request": "帮我搜索关于大语言模型的论文"}
            async with session.post(f"{base_url}/api/route", json=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"  意图: {result.get('intent')}")
                    print(f"  建议: {result.get('suggested_agents')}")
                else:
                    print(f"  请求失败: {resp.status}")
    except Exception as e:
        print(f"  请求错误: {e}")

    # 3. 论文搜索
    print("\n[API 3] 论文搜索")
    try:
        async with aiohttp.ClientSession() as session:
            data = {"query": "large language model", "source": "arxiv", "max_results": 3}
            async with session.post(f"{base_url}/api/search", json=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    papers = result.get("papers", [])
                    print(f"  找到 {len(papers)} 篇论文")
                    for i, paper in enumerate(papers[:2], 1):
                        print(f"    {i}. {paper.get('title', 'N/A')[:50]}...")
                else:
                    print(f"  请求失败: {resp.status}")
    except Exception as e:
        print(f"  请求错误: {e}")


async def demo_full_workflow():
    """演示完整工作流"""
    print("\n" + "="*60)
    print("演示9: 完整论文工作流 (MasterSupervisor)")
    print("="*60)

    from src.agents_v2.unified import MasterSupervisor

    # 创建Supervisor
    supervisor = MasterSupervisor()

    # 注册所有Agent
    supervisor.register_problem_agents()
    supervisor.register_pipeline_agents()
    supervisor.register_writing_agents()

    print("\n已注册Agent:")
    agent_names = list(supervisor.agents.keys())
    print(f"  总数: {len(agent_names)}")
    print(f"  列表: {', '.join(agent_names[:10])}...")

    # 运行选题流程
    print("\n运行选题阶段...")
    result = await supervisor.run(
        "topic_selection",
        {"user_request": "深度学习模型压缩与加速"}
    )

    print(f"\n流程执行结果:")
    print(f"  成功: {result.get('success', False)}")
    if result.get('error'):
        print(f"  错误: {result.get('error')}")


async def main():
    """主函数 - 运行所有演示"""
    print("\n" + "#"*60)
    print("# 论文Agent系统 - 功能演示")
    print("# 版本: 2.0")
    print("#"*60)

    # 检查API Key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n警告: 未设置 OPENAI_API_KEY 环境变量")
        print("  LLM相关功能可能无法正常工作")
        print("  请设置: set OPENAI_API_KEY=your_key")

    demos = [
        ("意图路由", demo_intent_router),
        ("论文搜索", demo_paper_search),
        ("Paper Agents", demo_paper_agents),
        ("Writing工具", demo_writing_tools),
        ("知识图谱", demo_knowledge_graph),
        ("定时任务", demo_scheduler),
        ("流式生成", demo_streaming),
        ("API Server", demo_api_server),
        ("完整工作流", demo_full_workflow),
    ]

    print("\n可用演示:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")

    print("\n输入演示编号运行对应演示 (输入 'all' 运行全部，'q' 退出):")

    try:
        choice = input("> ").strip()

        if choice.lower() == 'q':
            print("退出演示")
            return

        if choice.lower() == 'all':
            for name, demo_func in demos:
                try:
                    await demo_func()
                except Exception as e:
                    logger.error(f"演示 '{name}' 出错: {e}")
                    print(f"\n错误: {e}")
        elif choice.isdigit() and 1 <= int(choice) <= len(demos):
            idx = int(choice) - 1
            name, demo_func = demos[idx]
            await demo_func()
        else:
            print("无效选择")

        print("\n" + "#"*60)
        print("# 演示完成!")
        print("#"*60)

    except KeyboardInterrupt:
        print("\n\n演示被用户中断")
    except Exception as e:
        logger.error(f"演示过程出错: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
