"""
OutlineAgent - 大纲制定Agent

职责：
- 设计论文结构
- 规划各章节内容
- 确定关键论点
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json
import re

from .base_paper_agent import PaperAgentBase, AgentOutput, LLMConfig
from src.agents_v2.workflow.unified.translation import EnglishFirstMixin
from src.agents_v2.workflow.unified.pydantic_validator import (
    parse_with_pydantic, PaperStructure, ChapterOutline, _clean_json_markdown
)

logger = get_logging_logger(__name__)


# Fallback 通用结构
FALLBACK_STRUCTURE = {
    "title": "研究论文",
    "paper_type": "empirical",
    "chapters": [
        {"name": "研究背景与意义", "purpose": "阐述研究背景和意义", "order": 1},
        {"name": "文献综述", "purpose": "梳理相关研究现状", "order": 2},
        {"name": "研究方法", "purpose": "介绍研究方法设计", "order": 3},
        {"name": "研究结果", "purpose": "展示主要发现", "order": 4},
        {"name": "讨论与结论", "purpose": "总结并指出未来方向", "order": 5}
    ],
    "total_chapters": 5,
    "word_count_estimate": 8000
}


class OutlineAgent(EnglishFirstMixin, PaperAgentBase):
    """
    OutlineAgent - 大纲制定

    职责：
    - 设计论文结构
    - 规划各章节内容
    - 确定关键论点
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一位资深的学术论文结构规划专家，擅长根据不同研究领域和主题设计个性化的论文框架。
请遵循以下原则：
1. 根据研究主题的特点选择最合适的论文结构（实证研究、综述、理论分析、系统设计等）
2. 章节设计要紧密结合研究主题，避免通用的空泛标题
3. 各章节之间有严密的逻辑递进关系
4. 关键论点要具有学术深度和创新性
5. 章节名称要具体、有学术感，避免"引言"、"结论"等通用名称

输出要求：只返回JSON，不要包含其他解释文字。"""
        super().__init__(
            name="outline_agent",
            llm_config=llm_config,
            description="论文大纲制定",
            system_prompt=system_prompt
        )

    async def _process_text_english(self, text: str) -> str:
        """EnglishFirstMixin实现：用LLM处理英文文本"""
        return await self._llm_call(text)

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        执行大纲制定

        Args:
            input_data: 包含topic的字典
            context: 执行上下文（包含thesis和literature）
        """
        thesis = ""
        literature = {}

        if context:
            thesis = context.get("thesis_statement", "")
            literature = context.get("literature_result", {})

        if not thesis:
            thesis = input_data.get("task_description", "Research topic")

        try:
            # 1. 设计章节结构
            structure = await self._design_structure(thesis)

            # 2. 规划各章节内容
            chapter_plans = await self._plan_chapters(structure, literature)

            # 3. 确定关键论点
            key_arguments = await self._identify_key_arguments(thesis, literature)

            # 4. 整合大纲
            outline = {
                "structure": structure,
                "chapters": chapter_plans,
                "key_arguments": key_arguments
            }

            return AgentOutput(
                success=True,
                result={"outline": outline},
                agent_name=self.name,
                reasoning=f"Created outline with {len(chapter_plans)} chapters",
                quality_score=0.8
            )

        except Exception as e:
            cls_name = self.__class__.__name__
            self.logger.error(f"[{cls_name}:98] OutlineAgent execution failed: {e}")
            # 根据 CLAUDE.md 要求：禁止使用模板回退，必须使用 LLM
            # LLM 失败时抛出明确错误
            raise ValueError(f"OutlineAgent LLM 调用失败: {e}. 不支持模板回退.") from None

    async def _design_structure(self, thesis: str) -> Dict[str, Any]:
        """设计章节结构（英文优先模式）"""
        # 英文优先：翻译研究主题为英文，提升LLM理解质量
        if self._english_mode:
            translator = self._get_translator()
            thesis_en = await translator.to_english(thesis)
            logger.info(f"Translated thesis: {thesis[:50]}... → {thesis_en[:50]}...")
        else:
            thesis_en = thesis

        prompt = f"""## 角色
你是一位专业的学术论文结构设计专家，擅长根据研究主题设计最合适的论文框架。

## 能力边界
- 能够判断论文类型（实证研究/文献综述/理论分析/系统设计/对比实验）
- 能够设计紧扣研究主题的具体化章节标题
- 能够估算字数和章节数量

## 行为准则
处理任务时应当：
1. 根据主题特征选择最匹配的论文类型
2. 确保章节标题学术化、具体化，不使用通用标题
3. 每章必须有明确的学术目的

## 约束限制
- 总章节数5-8章
- 禁止使用"引言"、"文献综述"、"结论"等通用标题
- 章节标题必须与研究主题紧密相关

## 输出格式（严格JSON）
直接输出JSON，不要包含任何解释或思考过程：

{{"structure": {{
    "title": "结合主题的论文标题建议",
    "paper_type": "empirical|review|theoretical|system|comparison",
    "chapters": [
        {{
            "name": "具体化的章节名称（紧扣主题）",
            "purpose": "该章节在本研究中的具体目的",
            "order": 1
        }}
    ],
    "total_chapters": 5,
    "word_count_estimate": 8000
}}}}

## 研究主题
{thesis_en}

请立即输出JSON格式的论文结构："""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                raise ValueError(f"[{cls_name}] LLM返回空响应")

            # 使用 Pydantic 校验 JSON（如果解析失败，parse_with_pydantic 会返回 PaperStructure() 默认值）
            parsed = parse_with_pydantic(response, PaperStructure, PaperStructure())

            # 转换为字典返回
            structure = parsed.model_dump()

            # 确保 title 不为空
            if not structure.get("title"):
                structure["title"] = f"{thesis_en}研究"

            return structure

        except Exception as e:
            self.logger.error(f"[{cls_name}] Structure design failed: {type(e).__name__}: {e}")
            # 根据 CLAUDE.md 要求：禁止使用模板回退
            # LLM 失败时应重试一次，如果仍然失败则抛出错误
            raise ValueError(f"OutlineAgent._design_structure LLM 调用失败: {e}. 不支持规则后备.") from None

    async def _plan_chapters(
        self,
        structure: Dict[str, Any],
        literature: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """规划各章节内容"""
        chapters = structure.get("chapters", [])
        paper_type = structure.get("paper_type", "empirical")
        paper_analyses = literature.get("paper_analyses", [])[:10] if literature else []

        lit_context = f"""相关文献参考：
{json.dumps(paper_analyses, ensure_ascii=False, indent=2)}""" if paper_analyses else "（暂无相关文献，请根据学术常识规划内容）"

        # 英文优先：翻译章节信息
        if self._english_mode:
            translator = self._get_translator()
            chapters_en = []
            for ch in chapters:
                ch_en = await translator.to_english(ch.get("name", ""))
                purpose_en = await translator.to_english(ch.get("purpose", ""))
                chapters_en.append({
                    "name": ch_en,
                    "purpose": purpose_en,
                    "order": ch.get("order", 0)
                })
            chapters_display = json.dumps(chapters_en, ensure_ascii=False, indent=2)
        else:
            chapters_display = json.dumps(chapters, ensure_ascii=False, indent=2)

        prompt = f"""## 角色
你是一位专业的学术论文大纲规划专家，擅长为研究论文设计详细的章节内容。

## 能力边界
- 能够根据论文类型设计最合适的章节结构
- 能够为每个章节规划具体的学术内容要点
- 能够识别需要引用的研究方向和技术点

## 行为准则
处理任务时应当：
1. 确保每个章节的内容要点具体、有实质
2. 提供紧扣论文章节的具体写作指导
3. 列出准确的研究方向引用需求

## 约束限制
- 必须为每个输入章节都规划内容
- main_points必须具体，禁止泛泛的描述
- content_guidance必须说明"写什么、为什么写、如何组织"

## 输出格式（严格JSON）
直接输出JSON，不要包含任何解释或思考过程：

{{"chapter_plans": [
    {{
        "name": "章节名称（与输入一致）",
        "main_points": ["具体学术要点1", "具体学术要点2", "具体学术要点3"],
        "citations_needed": ["需要引用的研究方向或技术"],
        "key_arguments": ["核心论据1", "核心论据2"],
        "content_guidance": "本章节的具体写作指导（写什么、为什么写、如何组织）"
    }}
]}}

## 输入信息
论文类型：{paper_type}
章节列表：
{chapters_display}

{lit_context}

请立即输出JSON格式的章节规划："""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                self.logger.error(f"[{cls_name}] LLM返回空响应")
                return chapters
            content = _clean_json_markdown(response)
            if not content or not content.strip():
                self.logger.warning(f"[{cls_name}] LLM返回空内容")
                return chapters
            try:
                data = json.loads(content)
                return data.get("chapter_plans", chapters)
            except json.JSONDecodeError as e:
                self.logger.warning(f"[{cls_name}] JSON parse failed: {e}, trying regex extraction")
                # 尝试正则提取 JSON 数组
                import re
                # 查找 "chapter_plans": [ 开始的位置
                match = re.search(r'"chapter_plans"\s*:\s*\[', response)
                if match:
                    start = match.start()
                    # 找到对应的结束 ]
                    bracket_count = 0
                    end_pos = -1
                    for i, c in enumerate(response[start:], start):
                        if c == '[':
                            bracket_count += 1
                        elif c == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                end_pos = i + 1
                                break
                    if end_pos > start:
                        json_str = response[start:end_pos]
                        try:
                            data = json.loads(json_str)
                            return data.get("chapter_plans", chapters)
                        except Exception:
                            pass
                self.logger.warning(f"[{cls_name}] Regex extraction failed, returning empty chapters")
                return chapters
        except ValueError as e:
            self.logger.error(f"[{cls_name}] Chapter planning failed: {e}")
            return chapters
        except Exception as e:
            self.logger.error(f"[{cls_name}] Chapter planning failed: {e}")
            return chapters

    async def _identify_key_arguments(
        self,
        thesis: str,
        literature: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """确定关键论点"""
        paper_analyses = literature.get("paper_analyses", []) if literature else []
        lit_context = f"""相关文献分析：
{json.dumps(paper_analyses[:10], ensure_ascii=False)}""" if paper_analyses else "（暂无相关文献，请基于学术常识确定论点）"

        # 英文优先：翻译研究主题
        if self._english_mode:
            translator = self._get_translator()
            thesis_display = await translator.to_english(thesis)
        else:
            thesis_display = thesis

        prompt = f"""## 角色
你是一位资深的学术研究顾问，专注于识别论文中的核心学术论点。

## 能力边界
- 能够从研究主题中提炼出具有学术价值的论点
- 能够分析论点的支持证据、潜在质疑和反驳策略
- 能够区分核心论点和次要论点

## 行为准则
处理任务时应当：
1. 深入分析研究主题的学术内涵
2. 确保每个论点都有可论证的基础
3. 平衡支持证据与质疑声音
4. 维护学术中立性

## 约束限制
- 论点必须与研究主题紧密相关，禁止偏离主题
- 每个论点必须有具体的支持证据，不能是空泛陈述
- counter_arguments必须真实反映领域内的合理质疑

## 输出格式（严格JSON）
必须直接输出JSON，不要包含任何解释或思考过程：

{{"key_arguments": [
    {{
        "id": 1,
        "argument": "具体的学术论点描述（1-2句话）",
        "supporting_evidence": ["证据1", "证据2"],
        "counter_arguments": ["质疑1", "质疑2"],
        "rebuttal": "有理有据的反驳（1-2句话）"
    }}
]}}

## 输出要求
- 识别3-5个关键论点
- 每个论点包含上述4个字段
- 仅输出JSON，不要输出其他内容

## 研究主题
{thesis_display}

## 相关文献
{lit_context}

请立即输出JSON格式的论点列表："""
        cls_name = self.__class__.__name__
        try:
            response = await self._llm_call(prompt)
            if not response or not response.strip():
                self.logger.warning(f"[{cls_name}] LLM返回空响应")
                return []
            content = _clean_json_markdown(response)
            if not content or not content.strip():
                self.logger.warning(f"[{cls_name}] LLM返回空内容")
                return []
            try:
                data = json.loads(content)
                return data.get("key_arguments", [])
            except json.JSONDecodeError:
                # 尝试从内容中提取JSON
                match = re.search(r'\{[\s\S]*\}', content)
                if match:
                    try:
                        data = json.loads(match.group())
                        return data.get("key_arguments", [])
                    except json.JSONDecodeError:
                        pass
                self.logger.warning(f"[{cls_name}] JSON解析失败，原始输出: {response[:300]}")
                return []
        except ValueError as e:
            self.logger.error(f"[{cls_name}] Key arguments identification failed: {e}")
            return []
        except Exception as e:
            self.logger.error(f"[{cls_name}] Key arguments identification failed: {e}")
            return []
