"""
测试全链路论文生成模块
"""
import asyncio
import sys
import os

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Windows 编码修复
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到 path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def test_single_phase(phase_name: str):
    """测试单个阶段"""
    from demos.full_paper.phases import (
        DiagnosticPhase,
        TopicPhase,
        LiteraturePhase,
        MethodologyPhase,
        WritingPhase,
        PolishPhase,
    )
    from demos.full_paper.utils.config import PhaseConfig

    config = PhaseConfig(phase_name=phase_name)
    topic = "人工智能在教育领域的应用"

    print(f"\n{'='*50}")
    print(f"测试阶段: {phase_name}")
    print(f"{'='*50}")

    phase_map = {
        "diagnostic": DiagnosticPhase,
        "topic": TopicPhase,
        "literature": LiteraturePhase,
        "methodology": MethodologyPhase,
        "writing": WritingPhase,
        "polish": PolishPhase,
    }

    phase_class = phase_map.get(phase_name)
    if not phase_class:
        print(f"未知阶段: {phase_name}")
        return

    phase = phase_class(config)

    if phase_name == "diagnostic":
        output = await phase.run(topic)
    elif phase_name == "topic":
        output = await phase.run(topic)
    elif phase_name == "literature":
        output = await phase.run(topic)
    elif phase_name == "methodology":
        output = await phase.run(topic)
    elif phase_name == "writing":
        output = await phase.run(topic)
    elif phase_name == "polish":
        output = await phase.run("这是一段测试文本用于润色")

    print(f"状态: {output.status}")
    print(f"质量: {output.quality_score:.2f}")
    print(f"质量等级: {output.quality_level}")
    print(f"耗时: {output.execution_time:.2f}s")
    if output.error:
        print(f"错误: {output.error}")
    else:
        print(f"输出文本长度: {len(output.text)}")
        print(f"\n输出文本预览:\n{output.text[:300]}...")

    return output


async def test_full_pipeline():
    """测试完整流程"""
    from demos.full_paper import FullPaperRunner

    print(f"\n{'='*60}")
    print("测试完整流程")
    print(f"{'='*60}")

    runner = FullPaperRunner()
    result = await runner.run("人工智能在教育领域的应用")

    print(f"\n{'='*60}")
    print("最终结果")
    print(f"{'='*60}")
    print(f"成功: {result.get('success', False)}")
    print(f"完成阶段: {result.get('phases_completed', [])}")
    print(f"最终质量: {result.get('final_quality', 0):.2f}")
    print(f"总耗时: {result.get('total_time', 0):.2f}s")

    final_paper = result.get("final_paper", "")
    if final_paper:
        print(f"\n最终论文长度: {len(final_paper)} 字符")
        print(f"\n最终论文预览:\n{final_paper[:500]}...")

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--full":
            asyncio.run(test_full_pipeline())
        else:
            asyncio.run(test_single_phase(sys.argv[1]))
    else:
        print("用法:")
        print("  python test_runner.py [phase_name]  - 测试单个阶段")
        print("  python test_runner.py --full        - 测试完整流程")
        print("\n可用阶段: diagnostic, topic, literature, methodology, writing, polish")
