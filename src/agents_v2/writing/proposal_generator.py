"""
ProposalGeneratorAgent - 开题报告Agent

职责：
- 生成任务书
- 生成开题报告
- 生成文献综述
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig

logger = logging.getLogger(__name__)


class ProposalGeneratorAgent(WritingAgentBase):
    """
    ProposalGeneratorAgent - 开题报告生成

    职责：
    - 生成任务书
    - 生成开题报告
    - 整合文献综述
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的学术开题报告专家。
你的职责是：
1. 生成规范的任务书
2. 生成完整的开题报告
3. 整合文献综述

请确保：
- 格式规范
- 内容完整
- 符合学校要求"""
        super().__init__(
            name="proposal_generator",
            llm_config=llm_config,
            description="开题报告生成",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        生成开题报告

        Args:
            input_data: 包含以下字段的字典：
                - topic: 研究主题
                - student_info: 学生信息
                - supervisor: 导师 (可选)
                - deadline: 截止日期 (可选)
                - literature_review: 文献综述结果 (可选)
        """
        topic = input_data.get("topic", "")
        student_info = input_data.get("student_info", {})
        supervisor = input_data.get("supervisor", "")
        deadline = input_data.get("deadline", "")
        literature_review = input_data.get("literature_review", {})

        if not topic:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="Empty topic"
            )

        try:
            # 1. 生成任务书
            task_book = await self._generate_task_book(
                topic, student_info, supervisor, deadline
            )

            # 2. 生成开题报告
            proposal = await self._generate_proposal(
                topic, student_info, literature_review
            )

            return WritingOutput(
                success=True,
                result={
                    "topic": topic,
                    "task_book": task_book,
                    "proposal": proposal,
                    "student_info": student_info,
                    "supervisor": supervisor
                },
                agent_name=self.name,
                reasoning="Generated task book and proposal",
                quality_score=0.8
            )

        except Exception as e:
            self.logger.error(f"ProposalGeneratorAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _generate_task_book(
        self,
        topic: str,
        student_info: Dict[str, Any],
        supervisor: str,
        deadline: str
    ) -> str:
        """生成任务书"""
        student_name = student_info.get("name", "学生姓名")
        student_id = student_info.get("id", "学号")
        major = student_info.get("major", "专业")

        prompt = f"""
生成规范的任务书：

基本信息：
- 学生姓名：{student_name}
- 学号：{student_id}
- 专业：{major}
- 导师：{supervisor}
- 截止日期：{deadline}
- 研究主题：{topic}

请生成符合学校规范的任务书，包含：
1. 论文题目
2. 毕业论文的目的和意义
3. 论文的主要内容
4. 论文的方法和要求
5. 时间安排
6. 主要参考文献

以markdown格式输出。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Task book generation failed: {e}")
            return f"# 任务书\n\n研究主题：{topic}"

    async def _generate_proposal(
        self,
        topic: str,
        student_info: Dict[str, Any],
        literature_review: Dict[str, Any]
    ) -> str:
        """生成开题报告"""
        student_name = student_info.get("name", "学生")
        major = student_info.get("major", "专业")

        prompt = f"""
生成完整的开题报告：

学生：{student_name}
专业：{major}
研究主题：{topic}

文献综述摘要：
{json.dumps(literature_review, ensure_ascii=False)[:1000]}

开题报告应包含：
1. 选题背景与依据
2. 国内外研究现状
3. 研究内容与目标
4. 研究方法与技术路线
5. 预期创新点
6. 研究进度安排
7. 参考文献

以markdown格式输出。
"""
        try:
            response = await self._llm_call(prompt)
            return response
        except Exception as e:
            logger.error(f"Proposal generation failed: {e}")
            return f"# 开题报告\n\n研究主题：{topic}"
