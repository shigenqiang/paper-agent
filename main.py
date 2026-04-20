"""论文Agent主入口"""
import asyncio
import uuid
from typing import Dict, Any
from src.workflows.paper_workflow import PaperWorkflow
from src.core.state_model import State, paperagentstate, SearchAgent
from src.core.config import config_loader
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    logger.info("Starting Paper Agent...")

    # 加载配置
    try:
        config = config_loader.load("config")
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    # 初始化工作流
    workflow = PaperWorkflow()

    # 示例查询
    query = input("请输入研究主题（例如：函数型数据）：").strip()
    if not query:
        query = "请搜索3篇2022-2025年的函数型数据论文"

    logger.info(f"Processing query: {query}")

    # 创建初始状态
    initial_state = State(
        value=paperagentstate(
            current_step="initializing",
            search_state=SearchAgent(query=query)
        )
    )

    # 运行工作流
    try:
        config_dict = {
            "configurable": {
                "thread_id": str(uuid.uuid4())
            }
        }

        result = await workflow.run(initial_state, config_dict)

        # 输出结果
        if result["value"].report_markdown:
            logger.info("\n" + "="*50)
            logger.info("生成的报告：")
            logger.info("="*50)
            print(result["value"].report_markdown)

            # 保存报告
            output_file = "output/reports/latest_report.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result["value"].report_markdown)
            logger.info(f"\n报告已保存到: {output_file}")

        if result["value"].error.error:
            logger.error(f"执行过程中发生错误: {result['value'].error.error}")

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
