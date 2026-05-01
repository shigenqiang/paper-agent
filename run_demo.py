"""
快速演示脚本 - 无需交互，直接运行
"""
import asyncio
import sys
import os

# 修复 Windows 控制台中文显示
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# MiniMax API 配置
API_KEY = "sk-cp-i2VAG8ZzV47R9HS1ISYGS8NaDdbGKbxIzYBiR5nIkEJQYj8XCgsyR0FwDMQL6tdYW_4nxR_8E_tx1uF0QYNZAvWk84sa_ezSs6s3kgu0wAT5hi04UeG3ReU"
BASE_URL = "https://api.minimaxi.com/v1"


async def demo_topic():
    """演示选题Agent"""
    from src.agents_v2.paper_agents import TopicAgent
    from src.agents_v2.paper_agents.base_paper_agent import LLMConfig

    config = LLMConfig(
        provider="openai",
        model_name="MiniMax-M2.7",
        api_key=API_KEY,
        base_url=BASE_URL
    )

    print("\n=== 选题Agent演示 ===")
    agent = TopicAgent(config)
    result = await agent.execute({"user_request": "人工智能在教育领域的应用"})
    print(f"成功: {result.success}")
    if result.result:
        import json
        print(json.dumps(result.result, ensure_ascii=False, indent=2)[:1500])


async def main():
    print("=" * 50)
    print("MiniMax Agent 快速演示")
    print("=" * 50)

    await demo_topic()

    print("\n演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
