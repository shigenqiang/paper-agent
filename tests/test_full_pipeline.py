"""
全链路测试脚本
"""
import asyncio
import time
import json
import sys
import os

# 添加项目根目录到 path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test():
    from src.agents_v2.unified.master_supervisor import MasterSupervisor
    from src.agents_v2.paper_agents.base_paper_agent import LLMConfig
    import os

    api_key = os.getenv('OPENAI_API_KEY')
    llm_config = LLMConfig(provider='openai', model_name='MiniMax-M2.7', api_key=api_key, base_url=os.getenv('OPENAI_BASE_URL', 'https://api.minimax.chat/v1'))

    supervisor = MasterSupervisor(llm_config)
    supervisor.register_pipeline_agents()
    supervisor.register_writing_agents()
    supervisor.register_problem_agents()

    print('Starting full_paper flow...')
    start = time.time()
    result = await supervisor.run('full_paper', {'topic': '人工智能在教育领域的应用'})
    elapsed = time.time() - start

    print('='*60)
    print(f'Total time: {elapsed:.1f}s ({elapsed/60:.1f}min)')
    print(f'Success: {result.get("success")}')
    print(f'Final quality: {result.get("final_quality")}')
    print(f'Quality level: {result.get("quality_level")}')
    print(f'Phases: {result.get("phases_completed")}')
    print(f'Problems: {result.get("problems_identified")}')
    print(f'Final paper length: {len(result.get("final_paper", ""))}')
    print('='*60)

    # 保存结果
    with open('test_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result, elapsed

if __name__ == '__main__':
    result, elapsed = asyncio.run(test())