"""
Paper Agent - 统一管理脚本

用法:
    python tests/run_all_tests.py              # 运行所有测试
    python tests/run_all_tests.py test         # 运行所有测试
    python tests/run_all_tests.py test-api     # 只运行API测试
    python tests/run_all_tests.py test-e2e     # 只运行端到端测试
    python tests/run_all_tests.py test-quick   # 快速测试（遇错即停）
    python tests/run_all_tests.py start        # 同时启动前后端
    python tests/run_all_tests.py backend      # 只启动后端
    python tests/run_all_tests.py frontend     # 只启动前端
"""
import sys
import os
import subprocess
import pytest

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


# ============ 测试命令 ============

def test_all():
    """运行所有测试"""
    return pytest.main([
        'tests/test_api_comprehensive.py',
        'tests/test_e2e_paper_generation.py',
        '-v', '--tb=short',
    ])


def test_api():
    """只运行API测试"""
    return pytest.main([
        'tests/test_api_comprehensive.py',
        '-v', '--tb=short',
    ])


def test_e2e():
    """只运行端到端测试"""
    return pytest.main([
        'tests/test_e2e_paper_generation.py',
        '-v', '-s', '--tb=short',
    ])


def test_quick():
    """快速测试（遇错即停）"""
    return pytest.main([
        'tests/test_api_comprehensive.py',
        'tests/test_e2e_paper_generation.py',
        '-v', '--tb=short', '-x',
    ])


# ============ 启动命令 ============

def start_backend():
    """启动后端 API 服务"""
    print("启动后端 API 服务...")
    subprocess.run([sys.executable, '-m', 'src.main'], cwd=ROOT_DIR)


def start_frontend():
    """启动前端开发服务器"""
    print("启动前端开发服务器...")
    frontend_dir = os.path.join(ROOT_DIR, 'frontend')
    subprocess.run(['npm', 'run', 'dev'], cwd=frontend_dir, shell=True)


def start_all():
    """同时启动前后端"""
    import threading

    print("=" * 50)
    print("同时启动前端和后端...")
    print("  后端: http://localhost:8000")
    print("  前端: http://localhost:5173")
    print("=" * 50)

    # 后端线程
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    # 前端（主线程）
    start_frontend()


# ============ 命令注册 ============

COMMANDS = {
    # 测试
    'test': test_all,
    'test-all': test_all,
    'test-api': test_api,
    'test-e2e': test_e2e,
    'test-quick': test_quick,
    # 启动
    'start': start_all,
    'backend': start_backend,
    'frontend': start_frontend,
}


HELP_TEXT = """
可用命令:

  测试:
    test            运行所有测试（默认）
    test-api        只运行 API 测试
    test-e2e        只运行端到端测试
    test-quick      快速测试（遇错即停）

  启动:
    start           同时启动前端和后端
    backend         只启动后端 API 服务
    frontend        只启动前端开发服务器
"""


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'test'

    if cmd in COMMANDS:
        if cmd.startswith('test'):
            print(f"\n{'='*50}")
            print(f"Paper Agent 测试 - {cmd}")
            print(f"{'='*50}\n")
        exit_code = COMMANDS[cmd]()
        if exit_code is not None:
            sys.exit(exit_code)
    elif cmd in ('help', '-h', '--help'):
        print(HELP_TEXT)
    else:
        print(f"未知命令: {cmd}")
        print(HELP_TEXT)
        sys.exit(1)
