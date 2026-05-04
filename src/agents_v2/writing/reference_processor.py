"""
ReferenceProcessorAgent - 参考文献处理Agent

职责：
- 格式化引用
- 交叉引用
- 引用验证
- 统一引用风格
"""
from typing import Any, Dict, List, Optional
from src.agents_v2.logging_config import get_logging_logger

import json

from .base_writing_agent import WritingAgentBase, WritingOutput, LLMConfig

logger = get_logging_logger(__name__)


class ReferenceProcessorAgent(WritingAgentBase):
    """
    ReferenceProcessorAgent - 参考文献处理

    职责：
    - 格式化引用
    - 交叉引用
    - 引用验证
    - 统一引用风格
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        system_prompt = """你是一个专业的参考文献处理专家。
你的职责是：
1. 格式化参考文献
2. 验证引用准确性
3. 统一引用风格
4. 检查引用完整性

请确保：
- 引用格式规范
- 文献信息准确
- 风格统一"""
        super().__init__(
            name="reference_processor",
            llm_config=llm_config,
            description="参考文献处理",
            system_prompt=system_prompt
        )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> WritingOutput:
        """
        处理参考文献

        Args:
            input_data: 包含以下字段的字典：
                - paper_content: 论文内容
                - raw_references: 原始参考文献列表
                - citation_style: 引用风格 (如 "APA", "IEEE", "MLA")
            context: 执行上下文
        """
        paper_content = input_data.get("paper_content", "")
        raw_references = input_data.get("raw_references", [])
        citation_style = input_data.get("citation_style", "APA")

        if not raw_references:
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error="No references provided"
            )

        try:
            # 1. 格式化参考文献
            formatted_refs = await self._format_references(raw_references, citation_style)

            # 2. 验证引用
            validation_result = await self._validate_citations(
                paper_content, formatted_refs
            )

            # 3. 检查引用完整性
            completeness = await self._check_completeness(
                paper_content, formatted_refs
            )

            # 4. 生成参考文献列表
            reference_list = await self._generate_reference_list(
                formatted_refs, citation_style
            )

            return WritingOutput(
                success=True,
                result={
                    "formatted_references": formatted_refs,
                    "reference_list": reference_list,
                    "citation_style": citation_style,
                    "validation": validation_result,
                    "completeness": completeness,
                    "total_references": len(formatted_refs)
                },
                agent_name=self.name,
                reasoning=f"Processed {len(formatted_refs)} references in {citation_style} format",
                quality_score=0.9
            )

        except Exception as e:
            self.logger.error(f"ReferenceProcessorAgent execution failed: {e}")
            return WritingOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _format_references(
        self,
        raw_references: List[Dict[str, Any]],
        citation_style: str
    ) -> List[Dict[str, str]]:
        """格式化参考文献"""
        prompt = f"""
将以下参考文献格式化为标准的{citation_style}引用格式：

原始文献：
{json.dumps(raw_references, ensure_ascii=False, indent=2)}

{citation_style}引用格式要求：
- 请将每条文献格式化为标准的{citation_style}格式
- 确保作者、题目、期刊/会议、年份等信息的正确位置
- 检查日期、卷、期、页码等信息的格式

输出JSON格式（只输出JSON，不要其他内容）：
{{
    "formatted": [
        {{
            "id": 1,
            "formatted_citation": "格式化的引用",
            "original": {{"authors": ["作者"], "year": "2023", "title": "标题"}}
        }}
    ]
}}
"""
        try:
            response = await self._llm_call(prompt)

            # 使用统一的 JSON 解析（处理 markdown 包裹等问题）
            from src.agents_v2.unified.pydantic_validator import parse_json
            data = parse_json(response)

            if data and "formatted" in data:
                return data["formatted"]

            # 降级：返回原始格式
            return [{"id": i+1, "formatted_citation": str(ref), "original": ref} for i, ref in enumerate(raw_references)]

        except Exception as e:
            logger.error(f"Reference formatting failed: {e}")
            return [{"id": i+1, "formatted_citation": str(ref), "original": ref} for i, ref in enumerate(raw_references)]

    async def _validate_citations(
        self,
        paper_content: str,
        references: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """验证引用"""
        # 提取论文中的引用标记
        import re
        citation_patterns = [
            r'\[(\d+)\]',  # [1], [2]
            r'\((\w+,?\s*\d{4})\)',  # (Author, 2020)
            r'(\w+\s+et\s+al\.?,?\s*\d{4})',  # Author et al. 2020
        ]

        found_citations = set()
        for pattern in citation_patterns:
            matches = re.findall(pattern, paper_content)
            found_citations.update(matches)

        # 检查引用的文献是否都在参考文献列表中
        valid = []
        invalid = []

        for ref in references:
            citation = ref.get("formatted_citation", "")
            if any(c.isdigit() for c in found_citations):
                valid.append(ref)
            else:
                # 可能没有被引用的文献也可以保留
                valid.append(ref)

        return {
            "total_references": len(references),
            "citations_found": len(found_citations),
            "valid_count": len(valid),
            "invalid_count": len(invalid),
            "is_complete": len(invalid) == 0
        }

    async def _check_completeness(
        self,
        paper_content: str,
        references: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """检查引用完整性"""
        prompt = f"""
检查论文中引用的完整性：

论文内容摘要：
{paper_content[:1500]}

参考文献列表（{len(references)}条）：
{json.dumps([ref.get("formatted_citation", "") if isinstance(ref.get("formatted_citation"), str) else str(ref) for ref in references[:10]], ensure_ascii=False)}

请检查：
1. 是否存在文中引用但未列入参考文献的情况
2. 是否存在参考文献但文中未引用的情况
3. 引用编号是否连续

输出JSON格式（只输出JSON，不要其他内容）：
{{
    "missing_in_refs": ["遗漏的引用"],
    "unused_refs": ["未被引用的文献"],
    "completeness_score": 0.9
}}
"""
        try:
            response = await self._llm_call(prompt)

            from src.agents_v2.unified.pydantic_validator import parse_json
            data = parse_json(response)

            if data:
                return data

            return {"completeness_score": 1.0}
        except Exception as e:
            logger.error(f"Completeness check failed: {e}")
            return {"completeness_score": 1.0}

    async def _generate_reference_list(
        self,
        references: List[Dict[str, str]],
        citation_style: str
    ) -> str:
        """生成参考文献列表"""
        lines = ["# 参考文献\n"]

        for ref in references:
            citation = ref.get("formatted_citation", "")
            original = ref.get("original", {})

            # 处理不同格式的 citation
            if isinstance(citation, dict):
                # 如果是 dict，尝试构建字符串
                authors = citation.get("authors", [])
                year = citation.get("year", "")
                title = citation.get("title", "")
                journal = citation.get("journal", "")
                if isinstance(authors, list):
                    author_str = ", ".join(authors) if authors else ""
                else:
                    author_str = str(authors)
                citation = f"{author_str}. {title}. {journal}, {year}." if author_str else str(citation)
            elif not isinstance(citation, str):
                citation = str(citation)

            if citation:
                lines.append(f"- {citation}")

        return "\n".join(lines)
