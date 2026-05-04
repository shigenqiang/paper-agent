"""
论文写作流程测试

测试完整的论文生成流程：
- 诊断 → 选题 → 文献 → 方法 → 大纲 → 写作 → 审阅 → 润色（含引用）
"""
import asyncio
import sys
import time

sys.path.insert(0, ".")

from src.main import setup_logging, logger


def test_paper_generation():
    """测试论文生成完整流程"""
    from demos.full_paper.runner import FullPaperRunner

    topic = "深度学习在医学影像诊断中的应用"

    print("=" * 60)
    print("论文写作流程测试")
    print("=" * 60)
    print(f"主题: {topic}")
    print()

    runner = FullPaperRunner(enable_hitl=False)

    start = time.time()
    result = asyncio.run(runner.run(topic, paper_only=False))
    elapsed = time.time() - start

    print()
    print("=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"成功: {result['success']}")
    print(f"完成阶段: {', '.join(result['phases_completed']) if result['phases_completed'] else '无'}")
    print(f"论文长度: {len(result['final_paper'])} 字符")
    print(f"质量评分: {result['quality_score']:.2f}")
    print(f"引用数量: {result['polish_output'].get('citation_count', 0)}")

    polish = result.get('polish_output', {})
    if polish.get('reference_list'):
        ref_list = polish['reference_list']
        print(f"参考文献预览 (前500字):\n{ref_list[:500]}...")

    print(f"\n总耗时: {elapsed:.2f}秒")

    return result


def test_citation_only():
    """测试润色阶段的引用功能"""
    from src.agents_v2.langgraph_workflow.nodes.polish import PolishNode

    print()
    print("=" * 60)
    print("引用功能测试 (单独测试润色节点)")
    print("=" * 60)

    node = PolishNode()

    # 模拟状态
    state = {
        "draft": """
深度学习在医学影像诊断中取得了显著进展。卷积神经网络（CNN）已被广泛应用于图像分类和分割任务。

研究表明，ResNet和Transformer等架构在医学影像分析中表现优异。2020年以来的研究显示，深度学习模型在某些任务上已达到或超过人类专家水平。

然而，当前方法仍面临数据标注成本高、模型可解释性差等挑战。未来研究应关注小样本学习和可解释AI等方向。
""".strip(),
        "papers": [
            {
                "id": "1",
                "title": "Deep Learning for Medical Image Analysis",
                "authors": ["Zhang, Wei", "Li, Hong"],
                "year": "2023",
                "journal": "Medical Image Analysis",
                "doi": "10.1016/j.media.2023.01.001"
            },
            {
                "id": "2",
                "title": "ResNet in Medical Imaging: A Survey",
                "authors": ["Chen, Ming", "Wang, Fang"],
                "year": "2022",
                "journal": "IEEE Transactions on Medical Imaging",
                "doi": "10.1109/TMI.2022.3154210"
            },
            {
                "id": "3",
                "title": "Transformer for Medical Image Segmentation",
                "authors": ["Liu, Jia", "Yang, Min"],
                "year": "2024",
                "journal": "Medical Image Computing and Computer Assisted Intervention",
                "doi": "10.1007/9783-030-12345-6_1"
            },
        ],
        "language": "zh"
    }

    print(f"输入论文长度: {len(state['draft'])} 字符")
    print(f"参考文献数量: {len(state['papers'])}")
    print()

    result = asyncio.run(node(state))

    print(f"输出论文长度: {len(result.get('polished_text', ''))} 字符")
    print(f"引用数量: {result.get('citation_count', 0)}")
    print(f"参考文献列表: {result.get('reference_list', '无')[:500]}...")

    return result


def main():
    # 设置日志
    setup_logging(level="INFO")

    # 测试1: 完整流程（需要较长时间）
    test_paper_generation()

    # 测试2: 单独测试引用功能
    # test_citation_only()


if __name__ == "__main__":
    main()