"""
Paper Agent 主入口

使用方法:
    python -m src.main

启动后访问 http://localhost:8000
"""
import sys
import os

# 确保 src 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志系统
from src.agents_v2.logging_config import setup_logging, logger

# 初始化日志系统 - 使用完整 Loguru 特性
setup_logging(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    log_file="paper_agent.log",
    log_dir="logs",
    rotation="100 MB",            # 文件达到 100MB 时轮转
    retention="14 days",          # 保留 14 天
    compression="zip",            # ZIP 压缩旧日志
    enqueue=True,                 # 异步写入（多进程安全）
    backtrace=True,               # 完整异常堆栈
    diagnose=True,                # 变量诊断信息
    error_file="error.log",       # 独立的错误日志文件
)


def main():
    """启动 Paper Agent API 服务"""
    logger.info("=" * 60)
    logger.info("Paper Agent 学术论文写作辅助系统")
    logger.info("=" * 60)
    logger.info("启动 API 服务...")
    logger.info("访问地址: http://localhost:8000")
    logger.info("API文档: http://localhost:8000/docs")
    logger.info("-" * 60)
    logger.info("Loguru 日志特性:")
    logger.info("  - 控制台输出 (带颜色)")
    logger.info("  - 文件轮转 (100MB)")
    logger.info("  - 保留策略 (14 days)")
    logger.info("  - ZIP 压缩")
    logger.info("  - 异步写入 (多进程安全)")
    logger.info("  - 完整异常堆栈追踪")
    logger.info("  - 变量诊断信息")
    logger.info("  - 独立错误日志 (logs/error.log)")
    logger.info("-" * 60)
    logger.info("日志文件: logs/paper_agent.log")
    logger.info("=" * 60)

    # 导入并启动 api_server
    from src.agents_v2.api_server import main as api_main
    api_main()


if __name__ == "__main__":
    main()