"""
学术QA系统演示 - Academic QA System Demo

演示如何：
1. 使用基础 AcademicQASystem 进行问答
2. 使用知识图谱增强的 AcademicQAKGIntegration
3. 配置多种严格性模式
4. 查看检索、幻觉检测、置信度等评估结果
"""
import asyncio
from typing import List, Dict, Any

# ============================================================
# 模拟 LLM 提供者（实际使用时替换为真实 LLM）
# ============================================================

class MockLLM:
    """模拟 LLM（用于演示）"""

    async def agenerate(self, prompts: List[str]) -> Any:
        """模拟异步生成"""
        class Generation:
            def __init__(self, text):
                self.text = text

        # 根据提示词返回模拟回答
        prompt = prompts[0] if prompts else ""

        if "幻觉" in prompt.lower() or "hallucination" in prompt.lower():
            response = '{"overall_score": 0.15, "risk_level": "low", "statements": []}'
        elif "置信度" in prompt.lower() or "confidence" in prompt.lower():
            response = '{"overall": 0.82, "retrieval_relevance": 0.85, "groundedness": 0.80}'
        elif "faithfulness" in prompt.lower():
            response = "0.85"
        elif "relevance" in prompt.lower() and "answer" in prompt.lower():
            response = "0.78"
        elif "precision" in prompt.lower() or "context" in prompt.lower():
            response = "0.75"
        elif "多跳" in prompt or "multi" in prompt.lower():
            response = "根据提供的信息，Transformer是一种深度学习架构，BERT是基于Transformer的预训练模型，两者存在依赖关系。"
        elif "比较" in prompt or "compare" in prompt.lower():
            response = "比较分析：CNN在图像处理领域表现优异，而Transformer则在自然语言处理中更为突出。"
        elif "需要检索" in prompt or "判断是否需要" in prompt or "判断标准" in prompt:
            response = "检索"
        else:
            response = "这是关于学术问题的回答。系统能够检索相关文献并生成准确的答案。"

        return type('obj', (object,), {'generations': [[Generation(response)]]})()


# ============================================================
# 模拟向量存储
# ============================================================

class MockVectorStore:
    """模拟向量存储"""

    async def similarity_search_by_vector(self, embedding: List[float], k: int) -> List[Any]:
        """模拟相似度搜索"""
        class MockDoc:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata

        return [
            MockDoc(
                page_content="Transformer架构自2017年提出以来，已成为NLP领域的主流模型。",
                metadata={"source": "paper_1", "title": "Attention Is All You Need"}
            ),
            MockDoc(
                page_content="BERT是Google提出的预训练语言模型，在多项NLP任务上取得了SOTA。",
                metadata={"source": "paper_2", "title": "BERT: Pre-training of Deep Bidirectional"}
            ),
        ]


# ============================================================
# 演示函数
# ============================================================

async def demo_basic_qa():
    """演示1：基础学术QA系统"""
    print("\n" + "=" * 60)
    print("演示1：基础学术QA系统")
    print("=" * 60)

    from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

    # 创建配置 - 使用最小配置以避免复杂评估
    config = AcademicQAConfig(
        llm=MockLLM(),
        vector_store=MockVectorStore(),
        top_k=20,
        rerank_top_k=5,
        enable_crag=False,  # 禁用CRAG
        enable_self_rag=False,  # 禁用Self-RAG
        enable_hallucination_detection=False,  # 禁用幻觉检测
        enable_confidence_calibration=False,  # 禁用置信度校准
        enable_multi_hop=False,  # 禁用多跳推理
        citation_style="gb7714",
    )

    # 创建系统
    system = AcademicQASystem(config=config)

    # 执行问答 - 不提供contexts以避免RAGAs评估
    # contexts = [
    #     "Transformer是一种基于自注意力机制的深度学习架构，由Google在2017年提出。",
    #     "BERT是Google在2018年提出的预训练语言模型，基于Transformer架构。",
    #     "GPT系列是OpenAI开发的大语言模型，使用自回归生成方式。"
    # ]

    result = await system.ask(
        query="Transformer和BERT有什么关系？",
        contexts=None,  # 不提供contexts以避免RAGAs评估
        mode="fast"  # 使用快速模式避免触发严格评估
    )

    # 输出结果
    print(f"\n问题: Transformer和BERT有什么关系？")
    print(f"\n答案:\n{result.answer}")
    print(f"\n置信度: {result.confidence:.2f}")
    print(f"幻觉分数: {result.hallucination_score:.2f}")
    print(f"幻觉风险: {result.hallucination_risk}")
    print(f"引用数量: {len(result.citations)}")

    # 格式化输出
    formatted = system.format_answer_with_citations(result)
    print(f"\n格式化答案:\n{formatted}")


async def demo_multi_hop_qa():
    """演示2：多跳推理问答"""
    print("\n" + "=" * 60)
    print("演示2：多跳推理问答")
    print("=" * 60)

    from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

    config = AcademicQAConfig(
        llm=MockLLM(),
        enable_multi_hop=True,
        max_sub_questions=5,
    )

    system = AcademicQASystem(config=config)

    # 多跳问题
    result = await system.ask(
        query="比较CNN和Transformer在图像处理中的优缺点，并说明它们在医学影像中的应用",
        contexts=[
            "CNN（卷积神经网络）在图像处理领域有着广泛应用，通过卷积层提取局部特征。",
            "ResNet是一种著名的CNN架构，引入残差连接解决了深层网络训练困难的问题。",
            "Transformer架构最初用于NLP，后被引入计算机视觉领域（ViT）。",
            "ViT（Vision Transformer）将图像分割为patch，通过自注意力机制处理。",
            "医学影像诊断中，CNN被广泛用于X光、CT、MRI等影像分析。"
        ],
        mode="strict"
    )

    print(f"\n问题: 比较CNN和Transformer在图像处理中的优缺点，并说明它们在医学影像中的应用")
    print(f"\n答案:\n{result.answer}")
    print(f"\n置信度: {result.confidence:.2f}")
    print(f"推理链长度: {len(result.reasoning_chain)}")

    for i, step in enumerate(result.reasoning_chain):
        print(f"  步骤{i+1}: {step}")


async def demo_with_kg_integration():
    """演示3：知识图谱增强的学术QA"""
    print("\n" + "=" * 60)
    print("演示3：知识图谱增强的学术QA")
    print("=" * 60)

    from src.agents_v2.academic_qa import AcademicQAKGIntegration
    from src.agents_v2.knowledge_graph import GraphRAGQA

    # 创建知识图谱
    kg_qa = GraphRAGQA()

    # 构建知识图谱索引
    kg_qa.build_index(
        entities=[
            ("transformer", "Model", "Transformer是一种基于自注意力机制的序列到序列模型"),
            ("bert", "Model", "BERT是基于Transformer的双向预训练语言模型"),
            ("gpt", "Model", "GPT是基于Transformer的单向自回归语言模型"),
            ("attention", "Mechanism", "注意力机制是Transformer的核心组件"),
            ("nlp", "Domain", "自然语言处理是人工智能的重要分支"),
        ],
        relations=[
            ("bert", "based_on", "transformer"),
            ("gpt", "based_on", "transformer"),
            ("transformer", "uses", "attention"),
            ("bert", "applied_to", "nlp"),
        ]
    )

    # 创建集成系统
    qa_kg = AcademicQAKGIntegration(
        llm=MockLLM(),
        kg_qa=kg_qa,
        enable_kg_retrieval=True,
        enable_kg_enrichment=True,
        enable_kg_multihop=True,
        vector_weight=0.3,
        graph_weight=0.4,
        keyword_weight=0.3,
    )

    # 执行问答
    result = await qa_kg.ask(
        query="BERT和GPT有什么共同点和区别？",
        contexts=[
            "BERT和GPT都是基于Transformer架构的大语言模型。",
            "BERT使用双向编码器进行预训练，适合理解任务。",
            "GPT使用单向解码器进行预训练，适合生成任务。"
        ]
    )

    print(f"\n问题: BERT和GPT有什么共同点和区别？")
    print(f"\n答案:\n{result['answer']}")
    print(f"\n置信度: {result['confidence']:.2f}")
    print(f"幻觉风险: {result['hallucination_risk']}")

    if result.get("kg_context"):
        kg_ctx = result["kg_context"]
        print(f"\n知识图谱上下文:")
        print(f"  实体数量: {kg_ctx['num_entities']}")
        print(f"  子图摘要: {kg_ctx['subgraph_summary'][:100]}...")
        if kg_ctx.get("entity_map"):
            print(f"  实体映射: {list(kg_ctx['entity_map'].items())[:3]}")

    # 格式化输出
    formatted = qa_kg.format_answer_with_citations(result)
    print(f"\n格式化答案:\n{formatted}")


async def demo_crag_evaluation():
    """演示4：CRAG检索质量评估"""
    print("\n" + "=" * 60)
    print("演示4：CRAG检索质量评估")
    print("=" * 60)

    from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

    config = AcademicQAConfig(
        llm=MockLLM(),
        enable_crag=True,
    )

    system = AcademicQASystem(config=config)

    result = await system.ask(
        query="深度学习在医学诊断中有哪些应用？",
        contexts=[
            "深度学习在医学影像诊断中应用广泛，包括X光、CT、MRI等。",
            "卷积神经网络在医学影像分析中取得了优异性能。",
            "深度学习还被用于疾病预测、药物发现等方向。"
        ],
        mode="strict"
    )

    print(f"\n问题: 深度学习在医学诊断中有哪些应用？")
    print(f"\n答案:\n{result.answer}")
    print(f"\nCRAG质量评估: {result.metadata.get('crag_quality', 'N/A')}")


async def demo_hallucination_detection():
    """演示5：幻觉检测"""
    print("\n" + "=" * 60)
    print("演示5：幻觉检测")
    print("=" * 60)

    from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

    config = AcademicQAConfig(
        llm=MockLLM(),
        enable_hallucination_detection=True,
    )

    system = AcademicQASystem(config=config)

    result = await system.ask(
        query="Transformer架构的注意力机制是如何工作的？",
        contexts=[
            "注意力机制允许模型在生成每个词时关注输入序列的不同部分。",
            "自注意力通过计算Query、Key、Value矩阵来捕捉序列内部关系。",
        ]
    )

    print(f"\n问题: Transformer架构的注意力机制是如何工作的？")
    print(f"\n答案:\n{result.answer}")
    print(f"\n幻觉检测:")
    print(f"  幻觉分数: {result.hallucination_score:.2f}")
    print(f"  幻觉风险: {result.hallucination_risk}")


async def demo_ragas_evaluation():
    """演示6：RAGAs评估"""
    print("\n" + "=" * 60)
    print("演示6：RAGAs评估")
    print("=" * 60)

    from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

    config = AcademicQAConfig(
        llm=MockLLM(),
    )

    system = AcademicQASystem(config=config)

    result = await system.ask(
        query="什么是对比学习？",
        contexts=[
            "对比学习是一种无监督学习方法，通过拉近相似样本、推远不相似样本来学习表示。",
            "SimCLR是经典的对比学习算法。",
            "对比学习在图像表示学习中取得了显著成果。"
        ]
    )

    print(f"\n问题: 什么是对比学习？")
    print(f"\n答案:\n{result.answer}")

    if result.ragas_metrics:
        print(f"\nRAGAs评估指标:")
        print(f"  Faithfulness (忠实度): {result.ragas_metrics.get('faithfulness', 0):.2f}")
        print(f"  Answer Relevance (答案相关性): {result.ragas_metrics.get('answer_relevance', 0):.2f}")
        print(f"  Context Precision (上下文精确度): {result.ragas_metrics.get('context_precision', 0):.2f}")
        print(f"  平均分: {result.ragas_metrics.get('avg_score', 0):.2f}")


async def demo_document_ingestion():
    """演示7：文档摄入"""
    print("\n" + "=" * 60)
    print("演示7：文档摄入")
    print("=" * 60)

    from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

    config = AcademicQAConfig(
        llm=MockLLM(),
        chunk_size=512,
    )

    system = AcademicQASystem(config=config)

    documents = [
        {
            "content": """
            深度学习在医学影像诊断中的应用越来越广泛。
            卷积神经网络（CNN）已被成功用于X光胸片分析。
            研究表明，深度学习模型在某些任务上已达到人类专家水平。
            """,
            "metadata": {"title": "深度学习医学应用综述", "source": "paper_1"}
        },
        {
            "content": """
            Transformer架构最初用于自然语言处理任务。
            注意力机制允许模型捕捉长距离依赖关系。
            Vision Transformer (ViT) 将Transformer扩展到图像领域。
            """,
            "metadata": {"title": "Transformer综述", "source": "paper_2"}
        }
    ]

    result = await system.ingest_documents(documents, chunk_size=200)

    print(f"\n文档摄入结果:")
    print(f"  文档数量: {result['num_documents']}")
    print(f"  分块数量: {result['num_chunks']}")
    print(f"  分块详情: {result['chunks'][:2]}")


async def run_all_demos():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("学术QA系统演示")
    print("=" * 60)

    await demo_basic_qa()
    await demo_multi_hop_qa()
    await demo_with_kg_integration()
    await demo_crag_evaluation()
    await demo_hallucination_detection()
    await demo_ragas_evaluation()
    await demo_document_ingestion()

    print("\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_demos())
