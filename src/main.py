"""
Paper Agent 主入口

使用方法:
    python -m src.main

启动后访问 http://localhost:8000
"""
import logging
import sys
import os

# 确保 src 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """启动 Paper Agent API 服务"""
    logger.info("=" * 60)
    logger.info("Paper Agent 学术论文写作辅助系统")
    logger.info("=" * 60)
    logger.info("启动 API 服务...")
    logger.info("访问地址: http://localhost:8000")
    logger.info("API文档: http://localhost:8000/docs")
    logger.info("=" * 60)

    # 导入并启动 api_server
    from src.agents_v2.api_server import main as api_main
    api_main()


if __name__ == "__main__":
    main()