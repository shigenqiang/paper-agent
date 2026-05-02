"""
全链路论文生成 - 一次运行获取完整结果
"""
import asyncio
import sys
import os
import json

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Windows 编码修复
if sys.platform == 'win32':
    # 设置标准输出为 UTF-8
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
    # 设置标准输入为 UTF-8（用于读取命令行参数）
    if sys.stdin.encoding != 'utf-8':
        sys.stdin.reconfigure(encoding='utf-8')

# 添加项目根目录到 path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def run_full_paper(topic: str):
    """运行全链路论文生成"""
    from src.agents_v2.unified import MasterSupervisor
    from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

    # LLM 配置 - 从环境变量读取
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
    model_name = os.getenv("LLM_MODEL", "MiniMax-M2.7")

    if not api_key:
        print("错误: OPENAI_API_KEY 环境变量未设置")
        print("请确保 .env 文件存在且包含正确的 API Key")
        return

    llm_config = LLMConfig(
        provider="openai",
        model_name=model_name,
        api_key=api_key,
        base_url=base_url
    )

    print("=" * 60)
    print("全链路论文生成")
    print("=" * 60)
    print(f"主题: {topic}")
    print(f"模型: {model_name}")
    print(f"API Base URL: {base_url}")
    print()

    # 创建 Supervisor
    supervisor = MasterSupervisor(llm_config)
    supervisor.register_pipeline_agents()
    supervisor.register_writing_agents()
    supervisor.register_problem_agents()

    # 运行全链路
    print("开始执行全链路流程...")
    print("阶段: 诊断 -> 选题 -> 文献 -> 方法 -> 写作 -> 润色")
    print()

    result = await supervisor.run("full_paper", {"topic": topic})

    print("=" * 60)
    print("执行结果")
    print("=" * 60)
    print(f"成功: {result.get('success', False)}")
    print(f"最终质量: {result.get('final_quality', 'N/A'):.2f}" if isinstance(result.get('final_quality'), (int, float)) else f"最终质量: {result.get('final_quality', 'N/A')}")
    print()

    # 打印各阶段结果
    if 'phases' in result:
        print("各阶段结果:")
        for phase_name, phase_result in result.get('phases', {}).items():
            status = phase_result.get('status', 'N/A')
            quality = phase_result.get('quality', 'N/A')
            print(f"  - {phase_name}: {status} (质量: {quality})")

    print()
    print("详细结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:3000])

    return result


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "人工智能在教育领域的应用"
    try:
        asyncio.run(run_full_paper(topic))
    except KeyboardInterrupt:
        print("\n\n已取消执行")
        sys.exit(0)
