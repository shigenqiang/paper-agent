"""
启动 QA 持续问答服务

用法:
    python scripts/start_qa_service.py

    # 或带参数
    python scripts/start_qa_service.py --interval 10
"""
import asyncio
import sys
import os
import argparse

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents_v2.qa_service import QAService


async def main():
    parser = argparse.ArgumentParser(description="QA持续问答服务")
    parser.add_argument("--interval", type=float, default=5.0, help="问题间隔（秒）")
    parser.add_argument("--no-memory", action="store_true", help="禁用记忆")
    parser.add_argument("--no-improvement", action="store_true", help="禁用自我改进")
    args = parser.parse_args()

    service = QAService(
        enable_memory=not args.no_memory,
        enable_self_improvement=not args.no_improvement,
        check_interval=args.interval,
    )
    await service.initialize()

    print("QA持续问答服务初始化完成")
    print("输入问题进行问答，输入 'quit' 退出\n")

    await service.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())