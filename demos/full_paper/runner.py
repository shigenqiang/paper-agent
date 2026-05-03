"""
全链路论文运行器 - 基于 UnifiedWorkflow (LangGraph)

重构自旧的 phases 模式，改为使用 UnifiedWorkflow 处理：
1. 诊断阶段 (diagnostic) - 问题导向 Agent 并行诊断
2. 选题阶段 (topic) - TopicAgent
3. 文献阶段 (literature) - LiteratureAgent
4. 方法阶段 (methodology) - MethodologyAdvisorAgent
5. 写作阶段 (writing) - OutlineAgent + DraftWriterAgent
6. 润色阶段 (polish) - LanguagePolisherAgent + SmartReviserAgent

支持 HITL 人工介入（选题问题严重度 >= 0.7 时触发）
"""
import asyncio
import sys
import os
import time
import json
import logging

from typing import Optional

from src.agents_v2.logging_config import get_logging_logger
from src.agents_v2.langgraph_workflow.unified_workflow import UnifiedWorkflow

logger = get_logging_logger(__name__)


def _suppress_logs():
    """抑制所有日志输出"""
    # 设置所有logger为ERROR级别以上
    for logger_name in [
        "literature_agent", "paper_search", "arxiv", "pubmed",
        "diagnostic", "topic", "literature", "methodology", "writing", "polish",
        "writing_agent", "outline_agent", "draft_writer", "literature_mapper",
        "langgraph_workflow", "unified_workflow",
        "root"  # root logger
    ]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    # 抑制httpx等第三方库的日志
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


class FullPaperRunner:
    """
    全链路论文运行器 - 基于 UnifiedWorkflow

    工作流：
    router → diagnostic → topic → literature → methodology → outline → writing → review → polish → evaluation

    支持：
    - HITL 人工介入（选题问题触发）
    - 质量门禁（每阶段质量阈值检查）
    - LangGraph 状态持久化
    """

    def __init__(
        self,
        llm=None,
        enable_hitl: bool = False,
        enable_memory: bool = True,
        enable_evaluation: bool = True
    ):
        self.llm = llm
        self.enable_hitl = enable_hitl
        self.enable_memory = enable_memory
        self.enable_evaluation = enable_evaluation
        self.workflow: Optional[UnifiedWorkflow] = None
        self._init_workflow()

    def _init_workflow(self):
        """初始化 UnifiedWorkflow"""
        self.workflow = UnifiedWorkflow(
            llm=self.llm,
            enable_memory=self.enable_memory,
            enable_multimodal=True,
            enable_kg=True,
            enable_evaluation=self.enable_evaluation,
            enable_hitl=self.enable_hitl,
            hitl_interrupt_after=["diagnostic", "outline", "review", "polish"],
        )
        self.workflow.compile()
        logger.info("UnifiedWorkflow initialized for full_paper")

    async def run(
        self,
        topic: str,
        enable_hitl: bool = None,
        thread_id: str = "",
        paper_only: bool = False
    ) -> dict:
        """
        运行全链路论文生成

        Args:
            topic: 用户请求/研究主题
            enable_hitl: 是否启用 HITL（覆盖初始化设置）
            thread_id: LangGraph 线程 ID（用于恢复）
            paper_only: 是否仅输出论文内容（抑制所有中间输出）

        Returns:
            执行结果字典
        """
        if not paper_only:
            print("=" * 60)
            print("全链路论文生成 (UnifiedWorkflow)")
            print("=" * 60)
            print(f"主题: {topic}")
            print(f"HITL: {enable_hitl if enable_hitl is not None else self.enable_hitl}")
            print()

        start_time = time.time()

        # 使用 route_path="writing" 触发完整写作流程
        result = await self.workflow.run(
            query=topic,
            route_path="writing",
            enable_hitl=enable_hitl,
            thread_id=thread_id,
        )

        execution_time = time.time() - start_time

        # 解析结果
        final_state = result.get("state", {})
        interrupted = result.get("interrupted", False)
        interrupt_node = result.get("interrupt_node", "")

        # 编译结果
        output = {
            "success": not interrupted,
            "interrupted": interrupted,
            "interrupt_node": interrupt_node,
            "thread_id": result.get("thread_id", ""),
            "phases_completed": final_state.get("phase_sequence", []) if final_state else [],
            "final_paper": final_state.get("polished_text") or final_state.get("draft", ""),
            "outline": final_state.get("outline", {}),
            "quality_score": final_state.get("quality_score", 0),
            "execution_time": execution_time,
            "total_time": execution_time,
            "diagnostic_result": final_state.get("diagnostic_result", {}),
            "topic_result": final_state.get("topic_result", {}),
            "literature_result": final_state.get("literature_result", {}),
            "methodology_result": final_state.get("methodology_result", {}),
            "writing_output": {
                "outline_score": final_state.get("outline_quality_score", 0),
                "draft_score": final_state.get("draft_quality_score", 0),
                "draft_length": len(final_state.get("draft", "")),
            },
            "polish_output": {
                "polish_score": final_state.get("polish_quality_score", 0),
                "polished_length": len(final_state.get("polished_text", "")),
            },
        }

        if not paper_only:
            # 打印结果摘要
            print("\n" + "=" * 60)
            print("执行结果")
            print("=" * 60)
            print(f"成功: {output['success']}")
            print(f"完成阶段: {', '.join(output['phases_completed']) if output['phases_completed'] else '无'}")

            if interrupted:
                print(f"中断节点: {interrupt_node}")
                print(f"线程ID: {output['thread_id']}")
                print("提示: 使用 /api/workflow/resume 恢复执行")
            else:
                print(f"最终质量: {output['quality_score']:.2f}")
                print(f"论文长度: {len(output['final_paper'])} 字符")

            print(f"总耗时: {execution_time:.2f}s")

        return output

    def run_sync(self, topic: str, enable_hitl: bool = None, thread_id: str = "") -> dict:
        """同步运行入口"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.run(topic, enable_hitl, thread_id))


async def run_full_paper(topic: str, enable_hitl: bool = False, paper_only: bool = False):
    """运行全链路论文生成 - 便捷函数"""
    runner = FullPaperRunner(enable_hitl=enable_hitl)
    return await runner.run(topic, enable_hitl=enable_hitl, paper_only=paper_only)


def main():
    """主入口 - 仅输出最终论文"""
    import io

    # 解析参数（在导入之前）
    known_flags = {"--hitl", "--paper-only"}
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    topic = args[0] if args else "人工智能在教育领域的应用"
    enable_hitl = "--hitl" in sys.argv
    paper_only = "--paper-only" in sys.argv

    # 如果 topic 是 flag，设置为默认值
    if topic.startswith("--"):
        topic = "人工智能在教育领域的应用"

    # 尽快抑制日志（在导入模块之前）
    if paper_only:
        _suppress_logs()

    # 加载 .env 文件
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Windows 编码修复
    if sys.platform == 'win32':
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
        if sys.stdin.encoding != 'utf-8':
            sys.stdin.reconfigure(encoding='utf-8')

    if enable_hitl:
        print("启用 HITL 模式", file=sys.stderr)

    try:
        result = asyncio.run(run_full_paper(topic, enable_hitl=enable_hitl, paper_only=paper_only))

        # 仅输出最终论文（paper_only模式下不打印任何中间结果）
        final_paper = result.get("final_paper", "")
        if final_paper:
            # stdout 只输出论文内容
            print(final_paper)
        else:
            # 如果没有论文，输出错误信息到 stderr
            print("未能生成论文，请检查错误日志。", file=sys.stderr)
            sys.exit(1)

        # 如果被中断，输出恢复指令到stderr（不是stdout）
        if result.get("interrupted"):
            print(f"\n工作流已中断，请使用以下命令恢复：", file=sys.stderr)
            print(f"  curl -X POST http://localhost:8000/api/workflow/resume \\", file=sys.stderr)
            print(f"    -H 'Content-Type: application/json' \\", file=sys.stderr)
            print(f"    -d '{{\"thread_id\": \"{result.get('thread_id', '')}\", \"decision\": \"approve\"}}'", file=sys.stderr)

    except KeyboardInterrupt:
        print("\n\n已取消执行", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Full paper run failed: {e}")
        print(f"执行失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()