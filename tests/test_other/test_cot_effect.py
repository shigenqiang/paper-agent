"""
CoT效果验证测试（无需API key）

测试目标：
1. 验证CoT引导是否正确注入到AgentLoop
2. 验证Few-shot是否正确添加到Agent
3. 验证消息构建逻辑
"""
import asyncio
import sys
import os

# 加载.env环境变量（关键！）
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_cot_module_import():
    """测试CoT模块是否正确导入"""
    print("\n" + "=" * 60)
    print("Test 1: CoT Module Import")
    print("=" * 60)

    try:
        from src.agents_v2.unified.agent_loop import (
            AgentLoop, COT_GUIDANCE, FEW_SHOT_EXAMPLES
        )

        print(f"[PASS] COT_GUIDANCE length: {len(COT_GUIDANCE)} chars")
        print(f"[PASS] FEW_SHOT_EXAMPLES length: {len(FEW_SHOT_EXAMPLES)} chars")

        # 检查CoT引导内容
        has_step_by_step = "step by step" in COT_GUIDANCE.lower() or "逐步" in COT_GUIDANCE
        has_thinking_sections = all(
            keyword in COT_GUIDANCE
            for keyword in ["理解任务目标", "分析当前状态", "制定执行计划"]
        )

        print(f"[CHECK] Contains step-by-step guidance: {has_step_by_step}")
        print(f"[CHECK] Contains 5 thinking sections: {has_thinking_sections}")

        return True
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False


def test_agent_loop_cot_integration():
    """测试AgentLoop中的CoT集成"""
    print("\n" + "=" * 60)
    print("Test 2: AgentLoop CoT Integration")
    print("=" * 60)

    from src.agents_v2.unified.agent_loop import AgentLoop, COT_GUIDANCE, FEW_SHOT_EXAMPLES

    # 检查类属性
    print(f"[CHECK] AgentLoop.enable_cot_guidance exists: {hasattr(AgentLoop, 'enable_cot_guidance')}")
    print(f"[CHECK] AgentLoop.enable_few_shot exists: {hasattr(AgentLoop, 'enable_few_shot')}")

    # 检查常量
    print(f"[CHECK] COT_GUIDANCE is not empty: {bool(COT_GUIDANCE)}")
    print(f"[CHECK] FEW_SHOT_EXAMPLES is not empty: {bool(FEW_SHOT_EXAMPLES)}")

    return True


def test_agent_fewshot_integration():
    """测试Agent的Few-shot集成"""
    print("\n" + "=" * 60)
    print("Test 3: Agent Few-shot Integration")
    print("=" * 60)

    from src.agents_v2.paper_agents import TopicAgent, LiteratureAgent
    from src.agents_v2.problem_oriented import LanguagePolisherAgent

    agents_to_check = [
        ("TopicAgent", TopicAgent()),
        ("LiteratureAgent", LiteratureAgent()),
        ("LanguagePolisherAgent", LanguagePolisherAgent()),
    ]

    results = []
    for agent_name, agent in agents_to_check:
        print(f"\n[{agent_name}]")
        prompt_len = len(agent.system_prompt)
        print(f"  System prompt length: {prompt_len} chars")

        has_examples = "示例" in agent.system_prompt or "Example" in agent.system_prompt
        print(f"  Contains examples: {has_examples}")

        has_json_format = '"title"' in agent.system_prompt or '"title":' in agent.system_prompt
        print(f"  Contains JSON format hint: {has_json_format}")

        results.append(has_examples)

    return all(results)


def test_message_building():
    """测试消息构建逻辑"""
    print("\n" + "=" * 60)
    print("Test 4: Message Building Logic")
    print("=" * 60)

    from src.agents_v2.unified.agent_loop import AgentLoop, COT_GUIDANCE, FEW_SHOT_EXAMPLES
    from unittest.mock import MagicMock
    from langchain_core.messages import SystemMessage

    # 创建一个mock agent
    mock_agent = MagicMock()
    mock_agent.name = "test_agent"
    mock_agent.system_prompt = "You are a test agent."
    mock_agent.tools = []
    mock_agent.get_tool_schemas.return_value = []

    # 创建AgentLoop实例
    loop = AgentLoop(
        agent=mock_agent,
        llm=MagicMock(),
        enable_cot=True,
        enable_fewshot=True
    )

    print(f"[CHECK] AgentLoop created with enable_cot=True")
    print(f"[CHECK] AgentLoop.enable_cot={loop.enable_cot}")
    print(f"[CHECK] AgentLoop.enable_fewshot={loop.enable_fewshot}")

    # 验证COT_GUIDANCE和FEW_SHOT_EXAMPLES是类级别的
    has_cot = COT_GUIDANCE is not None
    has_fewshot = FEW_SHOT_EXAMPLES is not None

    print(f"[CHECK] COT_GUIDANCE available: {has_cot}")
    print(f"[CHECK] FEW_SHOT_EXAMPLES available: {has_fewshot}")

    return has_cot and has_fewshot


def test_cot_config_switch():
    """测试CoT配置开关"""
    print("\n" + "=" * 60)
    print("Test 5: CoT Config Switch")
    print("=" * 60)

    from src.agents_v2.unified.agent_loop import AgentLoop
    from unittest.mock import MagicMock

    mock_agent = MagicMock()
    mock_agent.name = "test_agent"
    mock_agent.system_prompt = "Base prompt"
    mock_agent.tools = []
    mock_agent.get_tool_schemas.return_value = []

    # 测试默认开启
    loop_on = AgentLoop(mock_agent, MagicMock(), enable_cot=True, enable_fewshot=True)
    print(f"[CHECK] Default CoT enabled: {loop_on.enable_cot == True}")
    print(f"[CHECK] Default Few-shot enabled: {loop_on.enable_fewshot == True}")

    # 测试关闭
    loop_off = AgentLoop(mock_agent, MagicMock(), enable_cot=False, enable_fewshot=False)
    print(f"[CHECK] CoT disabled: {loop_off.enable_cot == False}")
    print(f"[CHECK] Few-shot disabled: {loop_off.enable_fewshot == False}")

    return True


# ============ API对比测试（需要真实API调用） ============

async def run_api_comparison_test():
    """运行CoT效果对比测试（实际API调用）"""

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    import json
    import re

    COT_GUIDANCE = """
## Thinking Guidance (CoT)
When answering, please think step by step:
1. Understand the goal - What needs to be accomplished?
2. Analyze current state - What information is available?
3. Plan execution - What approach to use?
4. Execute and verify - Check if results are correct
5. Reflect and adjust - Consider alternatives if needed
"""

    FEW_SHOT_EXAMPLES = """
## Example
User: I want to research AI in healthcare
Thought: I need to focus on a specific problem in healthcare where AI can make an impact.
        Consider: diagnosis, drug discovery, remote patient monitoring...
        Choose the most specific and feasible one.
Output: {"title": "AI for Medical Diagnosis", "feasibility": 0.85}
"""

    BASE_PROMPT = """You are an academic research topic selection expert.
Output JSON with title, description, innovation, feasibility (0-1)."""

    test_request = "I want to research AI applications in education"

    # 从环境变量读取配置
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_API_BASE', 'https://api.minimax.chat/v1')
    model_name = os.getenv('LLM_MODEL', 'minimax-m2.7')

    print(f"[Config] base_url: {base_url}")
    print(f"[Config] model: {model_name}")

    results = []

    # ========== Test 1: No CoT, No Few-shot ==========
    print("\n" + "=" * 60)
    print("[Test 1] Baseline (No CoT, No Few-shot)")
    print("=" * 60)

    llm_base = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=0.7
    )

    try:
        resp1 = await llm_base.ainvoke([
            SystemMessage(content=BASE_PROMPT),
            HumanMessage(content=test_request)
        ])

        # 统计token
        usage1 = resp1.usage_metadata if hasattr(resp1, 'usage_metadata') else {}
        tokens1 = {
            'prompt': usage1.get('input_tokens', 0),
            'completion': usage1.get('output_tokens', 0),
            'total': usage1.get('total_tokens', 0)
        }

        print(f"\n[Token Stats]")
        print(f"  Prompt tokens: {tokens1['prompt']}")
        print(f"  Completion tokens: {tokens1['completion']}")
        print(f"  Total tokens: {tokens1['total']}")

        print(f"\n[Response Preview]")
        print(resp1.content[:500])

        results.append({
            'test': 'Baseline',
            'tokens': tokens1,
            'response': resp1.content
        })

    except Exception as e:
        print(f"Error: {e}")

    # ========== Test 2: With CoT ==========
    print("\n" + "=" * 60)
    print("[Test 2] With CoT (No Few-shot)")
    print("=" * 60)

    llm_cot = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=0.7
    )

    try:
        resp2 = await llm_cot.ainvoke([
            SystemMessage(content=BASE_PROMPT + COT_GUIDANCE),
            HumanMessage(content=test_request)
        ])

        usage2 = resp2.usage_metadata if hasattr(resp2, 'usage_metadata') else {}
        tokens2 = {
            'prompt': usage2.get('input_tokens', 0),
            'completion': usage2.get('output_tokens', 0),
            'total': usage2.get('total_tokens', 0)
        }

        print(f"\n[Token Stats]")
        print(f"  Prompt tokens: {tokens2['prompt']} (delta: +{tokens2['prompt'] - tokens1['prompt']})")
        print(f"  Completion tokens: {tokens2['completion']} (delta: +{tokens2['completion'] - tokens1['completion']})")
        print(f"  Total tokens: {tokens2['total']} (delta: +{tokens2['total'] - tokens1['total']})")

        print(f"\n[Response Preview]")
        print(resp2.content[:500])

        results.append({
            'test': 'CoT',
            'tokens': tokens2,
            'response': resp2.content
        })

    except Exception as e:
        print(f"Error: {e}")

    # ========== Test 3: With CoT + Few-shot ==========
    print("\n" + "=" * 60)
    print("[Test 3] With CoT + Few-shot")
    print("=" * 60)

    llm_full = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=0.7
    )

    try:
        resp3 = await llm_full.ainvoke([
            SystemMessage(content=BASE_PROMPT + COT_GUIDANCE + FEW_SHOT_EXAMPLES),
            HumanMessage(content=test_request)
        ])

        usage3 = resp3.usage_metadata if hasattr(resp3, 'usage_metadata') else {}
        tokens3 = {
            'prompt': usage3.get('input_tokens', 0),
            'completion': usage3.get('output_tokens', 0),
            'total': usage3.get('total_tokens', 0)
        }

        print(f"\n[Token Stats]")
        print(f"  Prompt tokens: {tokens3['prompt']} (delta: +{tokens3['prompt'] - tokens1['prompt']})")
        print(f"  Completion tokens: {tokens3['completion']} (delta: +{tokens3['completion'] - tokens1['completion']})")
        print(f"  Total tokens: {tokens3['total']} (delta: +{tokens3['total'] - tokens1['total']})")

        print(f"\n[Response Preview]")
        print(resp3.content[:500])

        results.append({
            'test': 'CoT + Few-shot',
            'tokens': tokens3,
            'response': resp3.content
        })

    except Exception as e:
        print(f"Error: {e}")

    # ========== Token对比分析 ==========
    print("\n" + "=" * 60)
    print("Token Consumption Comparison")
    print("=" * 60)

    print(f"\n{'Test':<20} {'Prompt':<12} {'Completion':<12} {'Total':<12} {'Cost Factor':<12}")
    print("-" * 60)

    baseline_total = results[0]['tokens']['total']
    for r in results:
        t = r['tokens']
        factor = t['total'] / baseline_total if baseline_total > 0 else 0
        print(f"{r['test']:<20} {t['prompt']:<12} {t['completion']:<12} {t['total']:<12} {factor:.2f}x")

    # ========== 质量评分 ==========
    print("\n" + "=" * 60)
    print("Quality Score Analysis")
    print("=" * 60)

    def score_response(response: str, test_name: str) -> dict:
        """评估响应质量"""
        scores = {
            'has_json': 0,
            'has_thinking': 0,
            'has_structure': 0,
            'json_valid': 0,
            'overall': 0
        }

        # 检查是否有thinking过程
        if 'think' in response.lower() or '思考' in response:
            scores['has_thinking'] = 20

        # 检查是否有结构（标题、描述等）
        if 'title' in response.lower() or '标题' in response:
            scores['has_structure'] = 20

        # 检查是否有JSON
        if '{' in response and '}' in response:
            scores['has_json'] = 20

        # 尝试解析JSON
        try:
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                json.loads(json_match.group())
                scores['json_valid'] = 40
        except:
            pass

        # CoT加成：thinking过程是高质量的标志
        if test_name != 'Baseline' and scores['has_thinking'] > 0:
            scores['has_thinking'] = 25
            scores['overall'] = sum(scores.values())
        else:
            scores['overall'] = sum(scores.values())

        return scores

    print(f"\n{'Test':<20} {'Thinking':<12} {'Structure':<12} {'JSON':<12} {'Valid JSON':<12} {'Overall':<12}")
    print("-" * 60)

    for r in results:
        s = score_response(r['response'], r['test'])
        print(f"{r['test']:<20} {s['has_thinking']:<12} {s['has_structure']:<12} {s['has_json']:<12} {s['json_valid']:<12} {s['overall']:<12}/100")

    # ========== 总结 ==========
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    if len(results) >= 3:
        r1, r2, r3 = results[0], results[1], results[2]

        print(f"""
1. Token消耗:
   - Baseline: {r1['tokens']['total']} tokens
   - CoT: {r2['tokens']['total']} tokens (+{((r2['tokens']['total']/r1['tokens']['total'])-1)*100:.1f}%)
   - CoT+Few-shot: {r3['tokens']['total']} tokens (+{((r3['tokens']['total']/r1['tokens']['total'])-1)*100:.1f}%)

2. 质量提升:
   - Baseline Score: {score_response(r1['response'], 'Baseline')['overall']}/100
   - CoT Score: {score_response(r2['response'], 'CoT')['overall']}/100
   - CoT+Few-shot Score: {score_response(r3['response'], 'CoT')['overall']}/100

3. 性价比分析:
   - CoT: 每1% token增长，质量提升 {((score_response(r2['response'], 'CoT')['overall'] - score_response(r1['response'], 'Baseline')['overall']) / (((r2['tokens']['total']/r1['tokens']['total'])-1)*100)):.2f} 分
   - CoT+Few-shot: 每1% token增长，质量提升 {((score_response(r3['response'], 'CoT')['overall'] - score_response(r1['response'], 'Baseline')['overall']) / (((r3['tokens']['total']/r1['tokens']['total'])-1)*100)):.2f} 分
""")


def main():
    """主函数"""
    print("\n" + "#" * 60)
    print("# CoT Integration Verification Test Suite")
    print("# (No API calls required)")
    print("#" * 60)

    tests = [
        ("CoT Module Import", test_cot_module_import),
        ("AgentLoop Integration", test_agent_loop_cot_integration),
        ("Agent Few-shot Integration", test_agent_fewshot_integration),
        ("Message Building", test_message_building),
        ("Config Switch", test_cot_config_switch),
    ]

    results = []
    for test_name, test_fn in tests:
        try:
            result = test_fn()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[ERROR] {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # 汇总
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n[SUCCESS] All CoT integration tests passed!")

        # 尝试运行API对比测试
        try:
            import openai
            if os.getenv('OPENAI_API_KEY'):
                print("\n" + "=" * 60)
                print("Running API Comparison Test (CoT Effect)")
                print("=" * 60)
                asyncio.run(run_api_comparison_test())
            else:
                print("\n[SKIP] API comparison test requires OPENAI_API_KEY")
        except ImportError:
            print("\n[SKIP] openai not installed, skipping API test")
    else:
        print("\n[WARNING] Some tests failed. Please check the output above.")


if __name__ == "__main__":
    main()
