"""
文献阶段 - Pipeline型Agent

职责：
- 多源文献搜索
- 质量筛选
- PDF阅读与信息提取
- 识别研究空白
"""
import time
from typing import Any, Dict, List, Optional

from src.agents_v2.logging_config import get_logging_logger

from ..utils.config import PhaseConfig
from ..utils.output import PhaseOutput

logger = get_logging_logger(__name__)


class LiteraturePhase:
    """
    文献阶段 - 使用LiteratureAgent

    职责：
    - 多源文献搜索
    - 质量筛选
    - 深度阅读分析
    - 识别研究空白
    """

    def __init__(self, config: Optional[PhaseConfig] = None):
        self.config = config or PhaseConfig(phase_name="literature")
        self.agent = None
        self._init_agent()

    def _init_agent(self):
        """初始化LiteratureAgent"""
        try:
            from src.agents_v2.paper_agents import LiteratureAgent
            self.agent = LiteratureAgent(self.config.llm_config)
            logger.debug("LiteratureAgent initialized")
        except ImportError as e:
            logger.warning(f"Could not import LiteratureAgent: {e}")

    async def run(self, topic: str, context: Optional[Dict[str, Any]] = None) -> PhaseOutput:
        """
        运行文献阶段

        Args:
            topic: 研究主题
            context: 上下文

        Returns:
            PhaseOutput: 文献综述结果输出
        """
        start_time = time.time()
        phase_name = "literature"

        logger.info(f"[{phase_name}] Starting literature search for: {topic[:50]}...")

        if not self.agent:
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error="LiteratureAgent not available"
            )

        try:
            input_data = {"topic": topic}
            result = await self.agent.execute(input_data, context)

            # 提取结果
            if hasattr(result, 'success'):
                success = result.success
                result_dict = result.result if hasattr(result, 'result') else {}
                quality_score = result.quality_score if hasattr(result, 'quality_score') else 0.0
                error = result.error if hasattr(result, 'error') else None
            else:
                success = False
                result_dict = {}
                quality_score = 0.0
                error = "Unknown result format"

            if not success:
                return PhaseOutput(
                    phase_name=phase_name,
                    success=False,
                    status="failed",
                    error=error or "LiteratureAgent execution failed",
                    execution_time=time.time() - start_time
                )

            # 生成输出文本
            literature_text = self._format_literature_output(result_dict)

            execution_time = time.time() - start_time

            return PhaseOutput(
                phase_name=phase_name,
                success=True,
                status="completed",
                text=literature_text,
                result=result_dict,
                quality_score=quality_score,
                quality_level=self._get_quality_level(quality_score),
                execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"[{phase_name}] Phase failed: {type(e).__name__}: {e}")
            return PhaseOutput(
                phase_name=phase_name,
                success=False,
                status="failed",
                error=str(e),
                execution_time=time.time() - start_time
            )

    def _format_literature_output(self, result: Dict[str, Any]) -> str:
        """格式化文献综述输出 - 与全链路一致"""
        lines = [
            "# 文献综述报告",
            "",
        ]

        papers = result.get("papers", [])
        paper_analyses = result.get("paper_analyses", [])
        research_gaps = result.get("research_gaps", [])
        total_found = result.get("total_found", len(papers))
        total_analyzed = result.get("total_analyzed", len(paper_analyses))

        lines.append(f"## 文献统计")
        lines.append(f"- 搜索到文献: {total_found} 篇")
        lines.append(f"- 深度分析: {total_analyzed} 篇")
        lines.append("")

        if paper_analyses:
            lines.append("## 主要文献分析")
            for i, paper in enumerate(paper_analyses[:10], 1):
                title = paper.get("title", "未知标题")
                core_problem = paper.get("core_problem", "未知")
                key_methodology = paper.get("key_methodology", "未知")
                key_findings = paper.get("key_findings", "未知")
                limitations = paper.get("limitations", "未知")

                lines.append(f"### {i}. {title}")
                lines.append(f"**核心问题**: {core_problem}")
                lines.append(f"**主要方法**: {key_methodology}")
                lines.append(f"**主要发现**: {key_findings}")
                lines.append(f"**局限性**: {limitations}")
                lines.append("")
        else:
            lines.append("## 主要文献分析")
            lines.append("（暂无详细分析）")
            lines.append("")

        if research_gaps:
            lines.append("## 研究空白")
            for i, gap in enumerate(research_gaps, 1):
                if isinstance(gap, dict):
                    gap_desc = gap.get("description", str(gap))
                    potential_direction = gap.get("potential_direction", "")
                    lines.append(f"{i}. {gap_desc}")
                    if potential_direction:
                        lines.append(f"   潜在方向: {potential_direction}")
                else:
                    lines.append(f"{i}. {gap}")
            lines.append("")
        else:
            lines.append("## 研究空白")
            lines.append("（暂无研究空白分析）")

        return "\n".join(lines)

    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 9.0:
            return "excellent"
        elif score >= 7.0:
            return "good"
        elif score >= 5.0:
            return "acceptable"
        return "poor"
