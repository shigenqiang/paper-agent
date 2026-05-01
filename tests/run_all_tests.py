"""
Paper Agent - 统一测试入口

运行方式:
    python tests/run_all_tests.py          # 运行所有测试
    python tests/run_all_tests.py api      # 只运行API测试
    python tests/run_all_tests.py e2e      # 只运行端到端测试
    python tests/run_all_tests.py quick    # 快速测试（跳过慢测试）
"""
import sys
import os
import pytest

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all():
    """运行所有测试"""
    return pytest.main([
        'tests/test_api_comprehensive.py',
        'tests/test_e2e_paper_generation.py',
        '-v',
        '--tb=short',
    ])


def run_api_only():
    """只运行API CRUD测试"""
    return pytest.main([
        'tests/test_api_comprehensive.py',
        '-v',
        '--tb=short',
    ])


def run_e2e_only():
    """只运行端到端论文生成测试"""
    return pytest.main([
        'tests/test_e2e_paper_generation.py',
        '-v',
        '-s',
        '--tb=short',
    ])


def run_quick():
    """快速测试（跳过标记为slow的测试）"""
    return pytest.main([
        'tests/test_api_comprehensive.py',
        'tests/test_e2e_paper_generation.py',
        '-v',
        '--tb=short',
        '-x',  # 遇到第一个失败就停止
    ])


def run_with_report():
    """运行测试并生成覆盖率报告"""
    return pytest.main([
        'tests/test_api_comprehensive.py',
        'tests/test_e2e_paper_generation.py',
        '-v',
        '--tb=short',
        '--durations=10',  # 显示最慢的10个测试
    ])


COMMANDS = {
    'all': run_all,
    'api': run_api_only,
    'e2e': run_e2e_only,
    'quick': run_quick,
    'report': run_with_report,
}


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if cmd in COMMANDS:
        print(f"\n{'='*60}")
        print(f"Paper Agent 测试套件 - 模式: {cmd}")
        print(f"{'='*60}\n")
        exit_code = COMMANDS[cmd]()
        sys.exit(exit_code)
    else:
        print(f"未知命令: {cmd}")
        print(f"可用命令: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
