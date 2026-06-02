"""测试运行入口 — 解决 Windows Make 中文路径编码问题

用法:
    python run_tests.py           # 运行全部
    python run_tests.py 01        # 运行模块 01
    python run_tests.py 03 06     # 运行模块 03 和 06
"""

import sys
import pytest
from pathlib import Path

MODULES = {
    "01": "tests/01-核心模型与存储",
    "02": "tests/02-项目服务",
    "03": "tests/03-论文库搜索导入",
    "04": "tests/04-PDF解析与分块",
    "05": "tests/05-论文卡片生成",
    "06": "tests/06-证据表",
    "07": "tests/07-知识图谱",
    "08": "tests/08-RetrievalScope",
    "09": "tests/09-ScopeQA与RAG",
    "10": "tests/10-综述生成",
    "11": "tests/11-创新点报告",
    "12": "tests/12-报告版本与导出",
    "13": "tests/13-LLM提示词与结构化输出",
    "14": "tests/14-API任务与前端联调",
    "15": "tests/15-评估日志监控",
}


def main():
    args = sys.argv[1:]
    if not args:
        # 运行全部
        paths = list(MODULES.values())
    else:
        paths = []
        for arg in args:
            if arg in MODULES:
                paths.append(MODULES[arg])
            else:
                print(f"未知模块: {arg}，可选: {', '.join(MODULES.keys())}")
                sys.exit(1)

    exit_code = pytest.main(["-v", "-s"] + paths)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
