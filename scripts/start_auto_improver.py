"""
启动监控与自动改进系统

用法:
    python scripts/start_auto_improver.py

    # 或带参数
    python scripts/start_auto_improver.py --interval 60 --auto-fix
"""
import asyncio
import sys
import os
import argparse

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents_v2.monitoring.auto_improver import AutoImprover


async def main():
    parser = argparse.ArgumentParser(description="监控与自动改进系统")
    parser.add_argument("--interval", type=float, default=60.0, help="检查间隔（秒）")
    parser.add_argument("--auto-fix", action="store_true", help="启用自动修复（谨慎）")
    parser.add_argument("--no-diagnose", action="store_true", help="禁用自动诊断")
    args = parser.parse_args()

    improver = AutoImprover(
        check_interval=args.interval,
        auto_diagnose=not args.no_diagnose,
        enable_auto_fix=args.auto_fix,
    )
    await improver.start()


if __name__ == "__main__":
    asyncio.run(main())