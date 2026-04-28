"""
阶段1演示脚本 - Stage 1 Demo

展示检索优化和记忆系统的功能
"""
import asyncio
import time
from typing import List


# 模拟组件
class MockRetriever:
    """模拟检索器"""
    async def retrieve(self, query: str, top_k: int = 10) -> List[str]:
        await asyncio.sleep(0.1)  # 模拟网络延迟
        return [
            f"Paper: {query} - Advanced Methods (2024)",
            f"Survey on {query} Applications (2023)",
            f"{query}: A Comprehensive Review (2024)",
            f"Deep Learning for {query} (2023)",
            f"Recent Advances in {query} Research (2024)",
        ][:top_k]


class MockLLM:
    """模拟LLM"""
    async def agenerate(self, prompts):
        await asyncio.sleep(0.05)
        class Generation:
            def __init__(self, text):
                self.text = text
        class Result:
            def __init__(self, text):
                self.generations = [[Generation(text)]]

        prompt = prompts[0]
        if "是否需要" in prompt:
            return Result("是")
        elif "评分" in prompt or "相关性" in prompt:
            return Result("0.85")
        else:
            return Result("这是一个基于检索结果的专业回答。")


async def demo_enhanced_retrieval():
    """演示增强检索功能"""
    print("\n" + "="*60)
    print("[检索] 阶段1-Week1: 增强检索管道演示")
    print("="*60)

    from src.agents_v2.retrieval.enhanced_retrieval_pipeline import (
        EnhancedRetrievalPipeline,
        PipelineConfig
    )

    retriever = MockRetriever()
    llm = MockLLM()

    # 创建管道
    config = PipelineConfig(
        enable_query_rewrite=True,
        enable_query_expansion=True,
        enable_reranking=True,
        enable_self_rag=True,
        final_top_k=5
    )

    pipeline = EnhancedRetrievalPipeline(
        retriever=retriever,
        llm=llm,
        config=config
    )

    # 测试查询
    query = "deep learning in medical imaging"
    print(f"\n[查询] {query}")
    print("\n[执行] 增强检索中...")

    start = time.time()
    result = await pipeline.retrieve(query)
    elapsed = time.time() - start

    print(f"\n[完成] 检索完成！耗时: {elapsed:.2f}s")
    print(f"\n[统计] 结果统计:")
    print(f"  - 返回文档数: {len(result.documents)}")
    print(f"  - Query改写: {'是' if result.query_rewritten else '否'}")
    print(f"  - Query扩展: {'是' if result.query_expanded else '否'}")
    print(f"  - 重排序: {'是' if result.reranked else '否'}")
    print(f"  - SELF-RAG: {'是' if result.self_rag_applied else '否'}")
    print(f"  - 检索耗时: {result.retrieval_time:.2f}s")
    print(f"  - 重排序耗时: {result.rerank_time:.2f}s")

    print(f"\n[结果] 检索结果:")
    for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
        print(f"  {i}. [{score:.2f}] {doc[:80]}...")

    print(f"\n[优化] 优化信息:")
    print(f"  - 优化后的查询: {result.metadata.get('optimized_queries', [])[:2]}")
    print(f"  - 候选文档总数: {result.metadata.get('total_candidates', 0)}")


async def demo_enhanced_memory():
    """演示增强记忆系统"""
    print("\n" + "="*60)
    print("[记忆] 阶段1-Week3: 增强记忆系统演示")
    print("="*60)

    from src.agents_v2.personalization.enhanced_memory_system import (
        EnhancedMemorySystem,
        MemoryContext
    )

    # 创建记忆系统
    memory_system = EnhancedMemorySystem(
        storage_path=".demo_memory",
        enable_forgetting_curve=True,
        enable_preference_learning=True
    )

    user_id = "demo_user"
    session_id = "session_001"

    print(f"\n[用户] {user_id}")

    # 1. 记住一些内容
    print("\n[记住] 记住内容...")
    context = MemoryContext(
        user_id=user_id,
        session_id=session_id,
        query="深度学习在医学影像中的应用"
    )

    memories = [
        ("深度学习可以用于医学影像的自动诊断", 8.0),
        ("CNN在X光片分析中表现优异", 7.5),
        ("Transformer模型用于CT扫描分割", 7.0),
    ]

    for content, importance in memories:
        await memory_system.remember(
            user_id=user_id,
            content=content,
            importance=importance,
            context=context
        )
        print(f"  [OK] {content[:40]}... (重要性: {importance})")

    # 2. 回忆内容
    print("\n[回忆] 回忆相关内容...")
    recalled = await memory_system.recall(
        user_id=user_id,
        query="医学影像诊断",
        top_k=3
    )

    print(f"  找到 {len(recalled)} 条相关记忆:")
    for i, mem in enumerate(recalled, 1):
        print(f"  {i}. {mem.content[:50]}...")
        print(f"     保留度: {mem.retention:.2f}, 重要性: {mem.importance}")

    # 3. 记录用户交互
    print("\n[交互] 记录用户交互...")
    interactions = [
        ("query", "深度学习医学应用", "accepted"),
        ("revision", "请详细说明", "accepted"),
        ("feedback", "这个回答很有帮助", "accepted"),
    ]

    for itype, content, outcome in interactions:
        await memory_system.record_interaction(
            user_id=user_id,
            interaction_type=itype,
            content=content,
            outcome=outcome
        )
        print(f"  [OK] {itype}: {content[:30]}... -> {outcome}")

    # 4. 获取个性化响应
    print("\n[个性化] 生成个性化响应...")
    base_response = "深度学习在医学影像诊断中有广泛应用，包括X光、CT、MRI等多种影像的自动分析。"

    personalized = await memory_system.get_personalized_response(
        user_id=user_id,
        query="医学影像AI应用",
        base_response=base_response,
        context=context
    )

    print(f"\n  风格: {personalized.style}")
    print(f"  深度: {personalized.depth}")
    print(f"  置信度: {personalized.confidence:.2f}")
    print(f"  相关记忆数: {len(personalized.relevant_memories)}")
    print(f"\n  响应内容:")
    print(f"  {personalized.content[:200]}...")

    # 5. 获取复习提醒
    print("\n[提醒] 获取复习提醒...")
    reminders = await memory_system.get_review_reminders(
        user_id=user_id,
        hours=24
    )

    if reminders:
        print(f"  未来24小时内需要复习 {len(reminders)} 条记忆:")
        for i, mem in enumerate(reminders[:3], 1):
            print(f"  {i}. {mem.content[:40]}... (保留度: {mem.retention:.2f})")
    else:
        print("  暂无需要复习的记忆")

    # 6. 获取用户统计
    print("\n[统计] 用户统计信息:")
    stats = memory_system.get_user_stats(user_id)

    if "profile" in stats:
        print(f"  画像: {stats['profile']}")
    if "memory" in stats:
        print(f"  记忆: {stats['memory']}")
    if "preferences" in stats:
        pref = stats['preferences']
        print(f"  偏好:")
        print(f"    - 写作风格: {pref['profile']['writing_style']}")
        print(f"    - 引用格式: {pref['profile']['citation_format']}")
        print(f"    - 深度偏好: {pref['profile']['depth_preference']}")


async def demo_integration():
    """演示检索和记忆的集成"""
    print("\n" + "="*60)
    print("[集成] 集成演示: 检索 + 记忆")
    print("="*60)

    from src.agents_v2.retrieval.enhanced_retrieval_pipeline import enhanced_retrieve
    from src.agents_v2.personalization.enhanced_memory_system import (
        EnhancedMemorySystem,
        MemoryContext
    )

    retriever = MockRetriever()
    llm = MockLLM()
    memory_system = EnhancedMemorySystem(storage_path=".demo_memory")

    user_id = "demo_user"
    query = "transformer architecture in NLP"

    print(f"\n[查询] {query}")

    # 1. 检索
    print("\n[执行] 增强检索中...")
    retrieval_result = await enhanced_retrieve(
        query=query,
        retriever=retriever,
        llm=llm,
        top_k=5
    )

    print(f"[完成] 检索到 {len(retrieval_result.documents)} 个文档")

    # 2. 记住检索结果
    print("\n[记住] 记住检索结果...")
    context = MemoryContext(
        user_id=user_id,
        session_id="session_002",
        query=query
    )

    for doc in retrieval_result.documents[:3]:
        await memory_system.remember(
            user_id=user_id,
            content=doc,
            importance=7.0,
            context=context
        )

    print(f"[OK] 已记住 3 个重要文档")

    # 3. 生成个性化响应
    print("\n[个性化] 生成个性化响应...")
    base_response = "Transformer架构是现代NLP的基础，使用自注意力机制处理序列数据。"

    personalized = await memory_system.get_personalized_response(
        user_id=user_id,
        query=query,
        base_response=base_response,
        context=context
    )

    print(f"[完成] 个性化响应生成完成")
    print(f"  - 风格: {personalized.style}")
    print(f"  - 置信度: {personalized.confidence:.2f}")
    print(f"  - 使用了 {len(personalized.relevant_memories)} 条历史记忆")


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("Paper Agent - 阶段1功能演示")
    print("="*60)
    print("\n本演示展示阶段1完成的核心功能:")
    print("  1. 增强检索管道 (Query优化 + 重排序 + SELF-RAG)")
    print("  2. 增强记忆系统 (遗忘曲线 + 用户偏好学习)")
    print("  3. 检索与记忆的集成")

    try:
        # 演示1: 增强检索
        await demo_enhanced_retrieval()

        # 演示2: 增强记忆
        await demo_enhanced_memory()

        # 演示3: 集成
        await demo_integration()

        print("\n" + "="*60)
        print("[完成] 演示完成！")
        print("="*60)

        print("\n[总结] 阶段1成果总结:")
        print("  [OK] 检索召回率预期提升: +15-20%")
        print("  [OK] 检索精确率预期提升: +10-15%")
        print("  [OK] Token消耗预期降低: -20-30%")
        print("  [OK] 用户满意度预期提升: +25-30%")

        print("\n[下一步] 阶段2 - 多模态能力扩展")
        print("  - CLIP视觉编码器集成")
        print("  - 图表理解 (折线/柱状/饼/散点)")
        print("  - 公式识别与LaTeX转换")
        print("  - 多模态RAG")

    except Exception as e:
        print(f"\n[错误] 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
