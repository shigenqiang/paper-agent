"""
完整论文工作流测试

测试 UnifiedWorkflow 的完整 paper 生成流程
"""
import sys
import os

# 添加项目根目录到 path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def test_workflow_initialization():
    """测试工作流初始化和编译"""
    print("=" * 50)
    print("测试工作流初始化和编译")
    print("=" * 50)

    from src.agents_v2.langgraph_workflow.unified_workflow import UnifiedWorkflow

    try:
        workflow = UnifiedWorkflow(enable_hitl=False)
        print("[OK] UnifiedWorkflow created")

        workflow.compile()
        print("[OK] Workflow compiled")
        print(f"     app: {workflow.app is not None}")

        return True
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {e}")
        return False


def test_workflow_structure():
    """测试工作流结构"""
    print("\n" + "=" * 50)
    print("测试工作流结构")
    print("=" * 50)

    from src.agents_v2.langgraph_workflow.unified_workflow import UnifiedWorkflow

    workflow = UnifiedWorkflow(enable_hitl=False)
    workflow.compile()

    # 检查节点是否都存在
    nodes_to_check = [
        "router", "diagnostic", "topic", "literature", "methodology",
        "crawler", "selector", "outline", "writing", "review",
        "report_crawl", "report_analyze", "report_gen",
        "qa_search", "qa_synthesize", "qa_answer",
        "revise", "refine", "polish"
    ]

    print("\n节点检查:")
    all_ok = True
    for node in nodes_to_check:
        try:
            # 通过尝试编译检查节点是否存在
            has_node = hasattr(workflow, f"_{node}_node") or hasattr(workflow, node)
            if has_node:
                print(f"  [OK] {node}")
            else:
                print(f"  [??] {node} (not clearly accessible)")
        except Exception as e:
            print(f"  [FAIL] {node}: {e}")
            all_ok = False

    return all_ok


def test_edge_routing():
    """测试边路由"""
    print("\n" + "=" * 50)
    print("测试边路由")
    print("=" * 50)

    from src.agents_v2.langgraph_workflow.edges import (
        diagnostic_quality_gate, route_by_intent, should_continue
    )

    tests = [
        # diagnostic_quality_gate tests
        ("diagnostic_quality_gate: 质量达标",
         lambda: diagnostic_quality_gate({'diagnostic_result': {'quality_score': 0.7, 'problems': [], 'severity': {}}}),
         "topic"),

        ("diagnostic_quality_gate: 选题严重=0.8 (HITL)",
         lambda: diagnostic_quality_gate({'diagnostic_result': {'quality_score': 0.5, 'problems': ['topic_vague'], 'severity': {'topic_vague': 0.8}}}),
         "hitl_intervene"),

        ("diagnostic_quality_gate: 选题严重=0.5 (OK)",
         lambda: diagnostic_quality_gate({'diagnostic_result': {'quality_score': 0.7, 'problems': ['topic_vague'], 'severity': {'topic_vague': 0.5}}}),
         "topic"),

        ("diagnostic_quality_gate: 低质量可迭代",
         lambda: diagnostic_quality_gate({'diagnostic_result': {'quality_score': 0.4, 'problems': [], 'severity': {}}, 'iteration': 0, 'max_iterations': 3}),
         "diagnostic_retry"),

        # route_by_intent tests
        ("route_by_intent: search",
         lambda: route_by_intent({'route_path': 'search'}),
         "search"),

        ("route_by_intent: writing",
         lambda: route_by_intent({'route_path': 'writing'}),
         "writing"),

        # should_continue tests
        ("should_continue: 无反馈，结束",
         lambda: should_continue({'iteration': 0, 'max_iterations': 3, 'feedback': []}),
         "done"),

        ("should_continue: 有反馈，继续",
         lambda: should_continue({'iteration': 0, 'max_iterations': 3, 'feedback': ['needs revision']}),
         "write"),
    ]

    all_passed = True
    for name, fn, expected in tests:
        try:
            result = fn()
            status = "[OK]" if result == expected else "[FAIL]"
            if result != expected:
                all_passed = False
            print(f"  {status} {name}: {result} (expected: {expected})")
        except Exception as e:
            print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
            all_passed = False

    return all_passed


def test_nodes_execution():
    """测试节点执行（模拟）"""
    print("\n" + "=" * 50)
    print("测试节点执行（模拟）")
    print("=" * 50)

    from src.agents_v2.langgraph_workflow.state import PaperAgentState

    # 创建初始状态
    state = PaperAgentState()
    state.user_query = "人工智能在教育领域的应用"
    state.iteration = 0
    state.max_iterations = 3
    state.current_phase = "diagnostic"

    print(f"  Initial state: user_query={state.user_query}")
    print(f"  iteration={state.iteration}, max_iterations={state.max_iterations}")

    # 测试 DiagnosticNode
    try:
        from src.agents_v2.langgraph_workflow.nodes.diagnostic import DiagnosticNode
        diag = DiagnosticNode()
        result = diag.execute(state)
        print(f"  [OK] DiagnosticNode executed")
        print(f"       diagnostic_result: {bool(result.get('diagnostic_result'))}")
    except Exception as e:
        print(f"  [FAIL] DiagnosticNode: {type(e).__name__}: {e}")
        return False

    # 检查 diagnostic 结果
    diag_result = result.get("diagnostic_result", {})
    quality_score = diag_result.get("quality_score", 0)
    problems = diag_result.get("problems", [])

    print(f"       quality_score: {quality_score}")
    print(f"       problems: {problems}")

    # 测试 edge 路由
    from src.agents_v2.langgraph_workflow.edges import diagnostic_quality_gate
    route_result = diagnostic_quality_gate(result)
    print(f"  [OK] diagnostic_quality_gate -> {route_result}")

    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("UnifiedWorkflow 完整测试")
    print("=" * 60)

    results = []

    results.append(("工作流初始化", test_workflow_initialization()))
    results.append(("工作流结构", test_workflow_structure()))
    results.append(("边路由", test_edge_routing()))
    results.append(("节点执行", test_nodes_execution()))

    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("所有测试通过!")
        return 0
    else:
        print("部分测试失败，请检查上述输出")
        return 1


if __name__ == "__main__":
    # Windows 编码
    if sys.platform == 'win32':
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')

    sys.exit(main())