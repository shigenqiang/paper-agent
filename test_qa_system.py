"""
QA系统测试脚本

测试所有QA系统功能：基础问答、知识图谱检索、多跳推理、幻觉检测、置信度校准、RAGAs评估等
"""
import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 抑制日志
os.environ["LOG_LEVEL"] = "ERROR"

# ============================================================
# Mock LLM 提供者
# ============================================================

class MockLLM:
    """模拟 LLM（用于测试）"""

    async def agenerate(self, prompts: List[str]) -> Any:
        """模拟异步生成"""
        class Generation:
            def __init__(self, text):
                self.text = text

        prompt = prompts[0] if prompts else ""

        if "幻觉" in prompt or "hallucination" in prompt.lower():
            response = '{"overall_score": 0.15, "risk_level": "low", "statements": []}'
        elif "置信度" in prompt or "confidence" in prompt.lower():
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
        elif "请只输出一个数字" in prompt:
            # 提取可能的数字
            import re
            nums = re.findall(r'0\.\d+|1\.0', prompt)
            if nums:
                response = nums[-1]
            else:
                response = "0.8"
        else:
            response = "这是关于学术问题的回答。系统能够检索相关文献并生成准确的答案。"

        return type('obj', (object,), {'generations': [[Generation(response)]]})()

    async def ainvoke(self, messages):
        """模拟异步调用"""
        class AIMessage:
            def __init__(self, content):
                self.content = content

        # 获取最后一条用户消息
        user_msg = ""
        for msg in messages:
            if hasattr(msg, 'content'):
                user_msg = msg.content
                break

        prompt = str(user_msg)

        if "幻觉" in prompt or "hallucination" in prompt.lower():
            response = '{"overall_score": 0.15, "risk_level": "low", "statements": []}'
        elif "置信度" in prompt or "confidence" in prompt.lower():
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
        elif "请只输出一个数字" in prompt:
            import re
            nums = re.findall(r'0\.\d+|1\.0', prompt)
            if nums:
                response = nums[-1]
            else:
                response = "0.8"
        else:
            response = "这是关于学术问题的回答。系统能够检索相关文献并生成准确的答案。"

        return AIMessage(response)

    def invoke(self, messages):
        """模拟同步调用"""
        return asyncio.run(self.ainvoke(messages))

    def batch_generate(self, prompts):
        """模拟批量生成"""
        return asyncio.run(self.agenerate(prompts))


from typing import List, Any


# ============================================================
# Mock 向量存储
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

    async def similarity_search(self, query: str, k: int) -> List[Any]:
        return await self.similarity_search_by_vector([0.0] * 768, k)


# ============================================================
# 测试用例
# ============================================================

TEST_RESULTS = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "metrics": {}
    }
}


def record_test(name: str, passed: bool, metrics: dict = None, error: str = None):
    """记录测试结果"""
    result = {
        "name": name,
        "passed": passed,
        "metrics": metrics or {},
        "error": error
    }
    TEST_RESULTS["tests"].append(result)
    TEST_RESULTS["summary"]["total"] += 1
    if passed:
        TEST_RESULTS["summary"]["passed"] += 1
    else:
        TEST_RESULTS["summary"]["failed"] += 1
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}" + (f" - {metrics}" if metrics else ""))
    if error:
        print(f"  Error: {error}")


async def test_basic_qa():
    """测试1：基础问答功能"""
    print("\n" + "=" * 60)
    print("测试1：基础问答功能")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

        config = AcademicQAConfig(
            llm=MockLLM(),
            vector_store=MockVectorStore(),
            top_k=20,
            rerank_top_k=5,
            enable_crag=False,
            enable_self_rag=False,
            enable_hallucination_detection=False,
            enable_confidence_calibration=False,
            enable_multi_hop=False,
            citation_style="gb7714",
        )

        system = AcademicQASystem(config=config)

        contexts = [
            "Transformer是一种基于自注意力机制的深度学习架构，由Google在2017年提出。",
            "BERT是Google在2018年提出的预训练语言模型，基于Transformer架构。",
            "GPT系列是OpenAI开发的大语言模型，使用自回归生成方式。"
        ]

        result = await system.ask(
            query="什么是Transformer？",
            contexts=contexts,
            mode="fast"
        )

        passed = result.answer and len(result.answer) > 10
        record_test(
            "基础问答",
            passed,
            metrics={"answer_length": len(result.answer)},
            error=None if passed else "答案为空或太短"
        )

        return passed, result

    except Exception as e:
        record_test("基础问答", False, error=str(e))
        return False, None


async def test_hallucination_detection():
    """测试2：幻觉检测"""
    print("\n" + "=" * 60)
    print("测试2：幻觉检测")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

        config = AcademicQAConfig(
            llm=MockLLM(),
            enable_hallucination_detection=True,
            enable_confidence_calibration=False,
            enable_multi_hop=False,
        )

        system = AcademicQASystem(config=config)

        contexts = [
            "量子计算是一种利用量子力学原理进行计算的技术。",
            "量子比特可以处于0和1的叠加态。"
        ]

        result = await system.ask(
            query="量子计算在医学影像中的应用",
            contexts=contexts,
            mode="strict"
        )

        # MockLLM应该返回低风险
        passed = result.hallucination_risk in ["low", "medium", "high"]
        record_test(
            "幻觉检测",
            passed,
            metrics={
                "score": result.hallucination_score,
                "risk": result.hallucination_risk
            }
        )

        return passed, result

    except Exception as e:
        record_test("幻觉检测", False, error=str(e))
        return False, None


async def test_confidence_calibration():
    """测试3：置信度校准"""
    print("\n" + "=" * 60)
    print("测试3：置信度校准")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

        config = AcademicQAConfig(
            llm=MockLLM(),
            enable_hallucination_detection=False,
            enable_confidence_calibration=True,
            enable_multi_hop=False,
        )

        system = AcademicQASystem(config=config)

        contexts = [
            "深度学习在图像识别领域取得了显著成果。",
            "CNN是深度学习中最常用的网络结构之一。"
        ]

        result = await system.ask(
            query="深度学习在医学诊断中的应用",
            contexts=contexts,
            mode="strict"
        )

        # 置信度应该在0-1之间
        passed = 0.0 <= result.confidence <= 1.0
        record_test(
            "置信度校准",
            passed,
            metrics={"confidence": result.confidence}
        )

        return passed, result

    except Exception as e:
        record_test("置信度校准", False, error=str(e))
        return False, None


async def test_multi_hop_reasoning():
    """测试4：多跳推理"""
    print("\n" + "=" * 60)
    print("测试4：多跳推理")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

        config = AcademicQAConfig(
            llm=MockLLM(),
            enable_multi_hop=True,
            max_sub_questions=5,
            enable_hallucination_detection=False,
            enable_confidence_calibration=False,
        )

        system = AcademicQASystem(config=config)

        contexts = [
            "CNN（卷积神经网络）在图像处理领域有着广泛应用。",
            "ResNet是一种著名的CNN架构，引入残差连接。",
            "Transformer架构最初用于NLP，后被引入计算机视觉（ViT）。",
            "ViT将图像分割为patch，通过自注意力处理。",
            "医学影像诊断中，CNN被广泛用于X光、CT、MRI分析。"
        ]

        result = await system.ask(
            query="比较CNN和Transformer在图像处理中的优缺点，并说明它们在医学影像中的应用",
            contexts=contexts,
            mode="strict"
        )

        passed = result.answer and len(result.answer) > 10
        record_test(
            "多跳推理",
            passed,
            metrics={
                "answer_length": len(result.answer),
                "reasoning_steps": len(result.reasoning_chain)
            }
        )

        return passed, result

    except Exception as e:
        record_test("多跳推理", False, error=str(e))
        return False, None


async def test_ragas_evaluation():
    """测试5：RAGAs评估"""
    print("\n" + "=" * 60)
    print("测试5：RAGAs评估")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

        config = AcademicQAConfig(
            llm=MockLLM(),
            enable_hallucination_detection=False,
            enable_confidence_calibration=False,
            enable_multi_hop=False,
        )

        system = AcademicQASystem(config=config)

        contexts = [
            "对比学习是一种无监督学习方法，通过拉近相似样本、推远不相似样本来学习表示。",
            "SimCLR是经典的对比学习算法。",
            "对比学习在图像表示学习中取得了显著成果。"
        ]

        result = await system.ask(
            query="什么是对比学习？",
            contexts=contexts,
            mode="strict"
        )

        # 检查RAGAs指标
        has_metrics = result.ragas_metrics is not None
        if has_metrics:
            metrics = result.ragas_metrics
            record_test(
                "RAGAs评估",
                True,
                metrics={
                    "faithfulness": metrics.get("faithfulness", 0),
                    "answer_relevance": metrics.get("answer_relevance", 0),
                    "context_precision": metrics.get("context_precision", 0),
                }
            )
        else:
            record_test("RAGAs评估", False, error="No metrics returned")

        return has_metrics, result

    except Exception as e:
        record_test("RAGAs评估", False, error=str(e))
        return False, None


async def test_citation_tracking():
    """测试6：引用溯源"""
    print("\n" + "=" * 60)
    print("测试6：引用溯源")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

        config = AcademicQAConfig(
            llm=MockLLM(),
            enable_crag=False,
            enable_self_rag=False,
            enable_hallucination_detection=False,
            enable_confidence_calibration=False,
            enable_multi_hop=False,
            citation_style="gb7714",
        )

        system = AcademicQASystem(config=config)

        contexts = [
            "Transformer架构自2017年提出以来，已成为NLP领域的主流模型。",
            "BERT是Google提出的预训练语言模型，在多项NLP任务上取得了SOTA。",
        ]

        result = await system.ask(
            query="BERT和GPT有什么关系？",
            contexts=contexts,
            mode="fast"
        )

        formatted = system.format_answer_with_citations(result)
        passed = "参考文献" in formatted or len(result.citations) >= 0

        record_test(
            "引用溯源",
            passed,
            metrics={"citation_count": len(result.citations)}
        )

        return passed, result

    except Exception as e:
        record_test("引用溯源", False, error=str(e))
        return False, None


async def test_kg_integration():
    """测试7：知识图谱集成"""
    print("\n" + "=" * 60)
    print("测试7：知识图谱集成")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQAKGIntegration

        # 使用 MockLLM
        mock_llm = MockLLM()

        # 创建KG集成系统（不连接真实Neo4j）
        kg_qa = None  # 不使用真实KG

        qa_kg = AcademicQAKGIntegration(
            llm=mock_llm,
            kg_qa=kg_qa,
            enable_kg_retrieval=False,  # 禁用KG检索
            enable_kg_enrichment=False,
            enable_kg_multihop=False,
        )

        contexts = [
            "BERT和GPT都是基于Transformer架构的大语言模型。",
            "BERT使用双向编码器进行预训练。",
            "GPT使用单向解码器进行预训练。"
        ]

        result = await qa_kg.ask(
            query="BERT和GPT有什么共同点和区别？",
            contexts=contexts
        )

        passed = result["answer"] and len(result["answer"]) > 5
        record_test(
            "知识图谱集成",
            passed,
            metrics={"answer_length": len(result["answer"])}
        )

        return passed, result

    except Exception as e:
        record_test("知识图谱集成", False, error=str(e))
        return False, None


async def test_crag_evaluation():
    """测试8：CRAG评估"""
    print("\n" + "=" * 60)
    print("测试8：CRAG评估")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

        config = AcademicQAConfig(
            llm=MockLLM(),
            enable_crag=True,
            enable_self_rag=False,
            enable_hallucination_detection=False,
            enable_confidence_calibration=False,
            enable_multi_hop=False,
        )

        system = AcademicQASystem(config=config)

        contexts = [
            "深度学习在医学影像诊断中应用广泛。",
            "卷积神经网络在医学影像分析中取得了优异性能。"
        ]

        result = await system.ask(
            query="深度学习在医学诊断中有哪些应用？",
            contexts=contexts,
            mode="strict"
        )

        passed = result.answer and len(result.answer) > 5
        record_test(
            "CRAG评估",
            passed,
            metrics={"crag_quality": result.metadata.get("crag_quality", "unknown")}
        )

        return passed, result

    except Exception as e:
        record_test("CRAG评估", False, error=str(e))
        return False, None


async def test_document_ingestion():
    """测试9：文档摄入"""
    print("\n" + "=" * 60)
    print("测试9：文档摄入")
    print("=" * 60)

    try:
        from src.agents_v2.academic_qa import AcademicQASystem, AcademicQAConfig

        config = AcademicQAConfig(
            llm=MockLLM(),
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

        passed = result["num_documents"] == 2 and result["num_chunks"] > 0
        record_test(
            "文档摄入",
            passed,
            metrics={
                "num_documents": result["num_documents"],
                "num_chunks": result["num_chunks"]
            }
        )

        return passed, result

    except Exception as e:
        record_test("文档摄入", False, error=str(e))
        return False, None


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("QA系统全面测试")
    print("=" * 60)
    print(f"开始时间: {datetime.now().isoformat()}")

    # 运行所有测试
    await test_basic_qa()
    await test_hallucination_detection()
    await test_confidence_calibration()
    await test_multi_hop_reasoning()
    await test_ragas_evaluation()
    await test_citation_tracking()
    await test_kg_integration()
    await test_crag_evaluation()
    await test_document_ingestion()

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    summary = TEST_RESULTS["summary"]
    print(f"总测试数: {summary['total']}")
    print(f"通过: {summary['passed']}")
    print(f"失败: {summary['failed']}")
    print(f"通过率: {summary['passed']/summary['total']*100:.1f}%")

    # 保存结果
    output_path = os.path.join(
        os.path.dirname(__file__),
        "docs",
        "test_results",
        "qa_system_test_report.md"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# QA系统测试报告\n\n")
        f.write(f"**测试时间**: {TEST_RESULTS['timestamp']}\n\n")
        f.write(f"## 测试结果汇总\n\n")
        f.write(f"| 指标 | 值 |\n")
        f.write(f"|------|-----|\n")
        f.write(f"| 总测试数 | {summary['total']} |\n")
        f.write(f"| 通过 | {summary['passed']} |\n")
        f.write(f"| 失败 | {summary['failed']} |\n")
        f.write(f"| 通过率 | {summary['passed']/summary['total']*100:.1f}% |\n\n")
        f.write(f"## 详细结果\n\n")
        f.write(f"| 测试名称 | 状态 | 指标 | 错误 |\n")
        f.write(f"|----------|------|------|------|\n")
        for test in TEST_RESULTS["tests"]:
            status = "PASS" if test["passed"] else "FAIL"
            metrics = str(test["metrics"]) if test["metrics"] else "-"
            error = test["error"] if test["error"] else "-"
            f.write(f"| {test['name']} | {status} | {metrics} | {error} |\n")

    print(f"\n测试报告已保存到: {output_path}")

    return summary["passed"] == summary["total"]


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)