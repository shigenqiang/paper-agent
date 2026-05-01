"""
SectionDifferentiatorAgent - 差异化写作Agent

针对问题：摘要与结论重复

职责：
- 检查摘要与结论差异
- 指导各章节差异化写作
- 确保内容不重复
"""
from typing import Any, Dict, List, Optional
import json
import logging

from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig

logger = logging.getLogger(__name__)


class SectionDifferentiatorAgent(ProblemAgentBase):
    """
    SectionDifferentiatorAgent - 差异化写作

    针对问题：
    - 摘要与结论内容重复
    - 各章节内容缺乏差异化
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个学术写作规范专家。
你的职责是：
1. 检查各章节的差异化
2. 确保摘要与结论不重复
3. 指导各章节独特贡献

请确保各章节内容差异化、各有重点。"""
        super().__init__(
            name="section_differentiator",
            target_problem="摘要与结论重复/内容缺乏差异化",
            llm_config=llm_config,
            description="章节差异化检查",
            system_prompt=system_prompt
        )

    async def diagnose(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        检查章节差异化

        输入：
        - sections: 各章节内容字典
          {
            "abstract": "摘要内容",
            "introduction": "引言内容",
            "method": "方法内容",
            "results": "结果内容",
            "discussion": "讨论内容",
            "conclusion": "结论内容"
          }
        """
        sections = input_data.get("sections", {})

        if not sections:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["章节内容为空"],
                recommendations=["请提供论文各章节内容"],
                quality_score=0.0,
                error="Empty sections"
            )

        try:
            # 1. 检查摘要vs结论重复
            abstract_conclusion = await self._check_abstract_vs_conclusion(
                sections.get("abstract", ""),
                sections.get("conclusion", "")
            )

            # 2. 检查各章节差异化
            section_diffs = await self._check_section_differentiation(sections)

            # 3. 识别重复内容
            duplications = await self._identify_duplications(sections)

            # 4. 生成各章节定位
            section_purposes = await self._define_section_purposes(sections)

            # 5. 生成改进建议
            recommendations = await self._generate_recommendations(
                abstract_conclusion, section_diffs, duplications
            )

            # 质量评分
            unique_score = 1.0 - (duplications.get("duplication_rate", 0) / 100)
            quality_score = round(unique_score * 0.7 + abstract_conclusion.get("differentiation", 0.5) * 0.3, 2)

            return AgentOutput(
                success=True,
                result={
                    "abstract_conclusion_check": abstract_conclusion,
                    "section_differentiation": section_diffs,
                    "duplications": duplications,
                    "section_purposes": section_purposes
                },
                agent_name=self.name,
                diagnosed_issues=duplications.get("duplicated_contents", []),
                recommendations=recommendations,
                quality_score=quality_score
            )

        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:117] Section differentiation check failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                diagnosed_issues=["差异化检查失败"],
                recommendations=["请检查章节内容格式"],
                quality_score=0.0,
                error=str(e)
            )

    async def _check_abstract_vs_conclusion(
        self,
        abstract: str,
        conclusion: str
    ) -> Dict[str, Any]:
        """检查摘要与结论的差异"""
        prompt = f"""
比较以下摘要和结论内容的差异：

摘要：
{self._truncate(abstract, 500)}

结论：
{self._truncate(conclusion, 500)}

请评估：
1. 内容重复程度 (0-100%)
2. 各自侧重点
3. 差异是否明显
4. 是否符合学术规范

输出JSON格式：
{{
    "duplication_rate": 35,
    "differentiation": 0.65,
    "abstract_focus": "摘要侧重点",
    "conclusion_focus": "结论侧重点",
    "is_acceptable": true/false,
    "issues": ["问题1", "问题2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:164] Abstract vs conclusion check failed: {e}")
            return {"duplication_rate": 50, "differentiation": 0.5, "is_acceptable": False}

    async def _check_section_differentiation(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """检查各章节差异化"""
        prompt = f"""
分析以下各章节的内容差异：

章节内容：
{json.dumps({k: self._truncate(v, 300) for k, v in sections.items()}, ensure_ascii=False)}

请检查：
1. 各章节是否有明确的独特贡献？
2. 内容是否有重叠？
3. 逻辑顺序是否清晰？
4. 每章的侧重点

输出JSON格式：
{{
    "differentiation_score": 7.5,
    "overlaps": [
        {{"section1": "章节1", "section2": "章节2", "overlap_content": "重叠内容"}}
    ],
    "section_focus": {{
        "abstract": "侧重点",
        "introduction": "侧重点",
        ...
    }},
    "issues": ["问题1", "问题2"]
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:200] Section differentiation check failed: {e}")
            return {"differentiation_score": 5.0, "overlaps": []}

    async def _identify_duplications(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """识别重复内容"""
        duplications = []
        section_names = list(sections.keys())

        for i, name1 in enumerate(section_names):
            for name2 in section_names[i+1:]:
                content1 = sections.get(name1, "")
                content2 = sections.get(name2, "")

                # 简单的重叠检测
                if content1 and content2:
                    # 检查是否有相同的关键句
                    sentences1 = set(content1.split(".")[:5])
                    sentences2 = set(content2.split(".")[:5])
                    overlap = sentences1.intersection(sentences2)

                    if overlap:
                        duplications.append({
                            "section1": name1,
                            "section2": name2,
                            "duplicated_contents": list(overlap)[:3]
                        })

        duplication_rate = len(duplications) * 15  # 简化计算

        return {
            "duplications": duplications,
            "duplication_rate": min(100, duplication_rate),
            "duplicated_contents": [d.get("duplicated_contents", []) for d in duplications]
        }

    async def _define_section_purposes(self, sections: Dict[str, str]) -> Dict[str, str]:
        """定义各章节的独特定位"""
        prompt = f"""
为以下论文章节定义独特的写作目的：

章节：{json.dumps(list(sections.keys()), ensure_ascii=False)}

请为每个章节定义：
1. 核心目的（应该只做一件事）
2. 应避免的内容（不应与其他章节重复）
3. 与其他章节的关键区别

输出JSON格式：
{{
    "purposes": {{
        "章节名": {{
            "core_purpose": "核心目的",
            "avoid": "应避免的内容",
            "key_difference": "与其他章节的区别"
        }}
    }}
}}
"""
        try:
            response = await self._llm_call(prompt)
            data = json.loads(response)
            return data.get("purposes", {})
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}:263] Purpose definition failed: {e}")
            return {}

    async def _generate_recommendations(
        self,
        abstract_conclusion: Dict,
        section_diffs: Dict,
        duplications: Dict
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 摘要vs结论问题
        if abstract_conclusion.get("duplication_rate", 0) > 30:
            recommendations.append(f"摘要与结论重复率过高({abstract_conclusion['duplication_rate']}%)，请差异化：")
            recommendations.append(f"  - 摘要：侧重研究概述、方法、发现")
            recommendations.append(f"  - 结论：侧重研究发现的意义、局限、未来方向")

        # 重叠问题
        for overlap in section_diffs.get("overlaps", []):
            recommendations.append(f"注意{overlap['section1']}与{overlap['section2']}的内容重叠")

        # 各章节定位
        purposes = abstract_conclusion  # 简化
        if not recommendations:
            recommendations.append("各章节差异化基本合格，可继续完善")

        return recommendations[:5]

    def _truncate(self, text: str, max_length: int) -> str:
        """截断文本"""
        if not text:
            return ""
        return text[:max_length] + "..." if len(text) > max_length else text
