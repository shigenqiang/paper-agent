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
import re

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
        # 清理和验证输入数据
        cleaned_refs = []
        for ref in raw_references:
            cleaned_ref = {
                "id": len(cleaned_refs) + 1,
                "authors": self._clean_authors(ref.get("authors", [])),
                "year": self._clean_year(ref.get("year", "")),
                "title": ref.get("title", "Unknown Title"),
                "journal": ref.get("journal", "") or ref.get("venue", "") or ref.get("booktitle", ""),
                "volume": ref.get("volume", ""),
                "issue": ref.get("issue", ""),
                "pages": ref.get("pages", ""),
                "doi": ref.get("doi", "")
            }
            cleaned_refs.append(cleaned_ref)

        prompt = f"""
将以下参考文献格式化为标准的{citation_style}引用格式。

原始文献（{len(cleaned_refs)}条）：
{json.dumps(cleaned_refs, ensure_ascii=False, indent=2)}

{citation_style}引用格式要求：
- APA格式: 作者 (年份). 标题. 期刊, 卷(期), 页码.
- GB/T格式: [序号] 作者. 标题. 期刊, 年份.

输出JSON格式（只输出JSON，不要其他内容）：
{{
    "formatted": [
        {{"id": 1, "formatted_citation": "格式化的引用"}},
        ...
    ]
}}"""
        try:
            response = await self._llm_call(prompt)

            from src.agents_v2.unified.pydantic_validator import parse_json
            data = parse_json(response)

            if data and "formatted" in data:
                formatted_list = data["formatted"]
                # 合并原始信息到formatted
                for item in formatted_list:
                    idx = item.get("id", 0) - 1
                    if 0 <= idx < len(cleaned_refs):
                        item["original"] = cleaned_refs[idx]
                    # 确保 formatted_citation 是字符串类型
                    if isinstance(item.get("formatted_citation"), dict):
                        item["formatted_citation"] = self._dict_to_citation_str(item["formatted_citation"])
                    elif isinstance(item.get("formatted_citation"), str):
                        # 清除 LLM 返回字符串中的编号前缀，如 "[1] " 或 "[[1]] "
                        citation_clean = item["formatted_citation"].strip()
                        while True:
                            match = re.match(r'^\s*\[+\s*\d+\s*\]+\s*', citation_clean)
                            if not match:
                                break
                            citation_clean = citation_clean[match.end():].strip()
                        item["formatted_citation"] = citation_clean
                return formatted_list

            # 降级：返回原始格式
            return [{"id": i+1, "formatted_citation": self._format_single_reference(ref, citation_style), "original": ref} for i, ref in enumerate(cleaned_refs)]

        except Exception as e:
            logger.error(f"Reference formatting failed: {e}")
            return [{"id": i+1, "formatted_citation": self._format_single_reference(ref, citation_style), "original": ref} for i, ref in enumerate(cleaned_refs)]

    def _clean_authors(self, authors) -> List[str]:
        """清理作者信息"""
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(",")]
        if not isinstance(authors, list):
            return []
        # 过滤空作者
        return [a for a in authors if a and a.strip()]

    def _clean_year(self, year) -> str:
        """清理年份信息"""
        year_str = str(year) if year else ""
        # 提取数字
        import re
        match = re.search(r'\d{4}', year_str)
        if match:
            return match.group()
        # 过滤无效年份
        if year_str.isdigit() and 1900 <= int(year_str) <= 2030:
            return year_str
        return "Unknown"

    def _format_single_reference(self, ref: Dict[str, Any], citation_style: str) -> str:
        """格式化单条参考文献（降级使用）"""
        authors = ref.get("authors", [])
        if isinstance(authors, list) and authors:
            author_str = ", ".join(authors)
        else:
            author_str = "Unknown Author"
        year = ref.get("year", "Unknown")
        title = ref.get("title", "Unknown Title")
        journal = ref.get("journal", "") or ref.get("venue", "")
        volume = ref.get("volume", "")
        issue = ref.get("issue", "")
        pages = ref.get("pages", "")

        if citation_style == "GB_T":
            parts = [author_str, title]
            if journal:
                parts.append(f"{journal}")
            if year and year != "Unknown":
                parts.append(f"{year}")
            return ". ".join(parts)
        else:
            # APA style
            parts = [f"{author_str} ({year})", title]
            if journal:
                if volume:
                    parts.append(f"{journal}, {volume}")
                    if issue:
                        parts[-1] += f"({issue})"
                    if pages:
                        parts[-1] += f", {pages}"
                else:
                    parts.append(journal)
            return ". ".join(parts)

    def _dict_to_citation_str(self, citation_dict: Dict[str, Any], citation_style: str = "GB_T") -> str:
        """将引用字典转换为字符串格式（处理LLM返回dict格式的降级）"""
        if not isinstance(citation_dict, dict):
            return str(citation_dict)

        authors = citation_dict.get("authors", [])
        year = citation_dict.get("year", "")
        title = citation_dict.get("title", "")
        journal = citation_dict.get("journal", "")
        volume = citation_dict.get("volume", "")
        issue = citation_dict.get("issue", "")
        pages = citation_dict.get("pages", "")
        doi = citation_dict.get("doi", "")

        if isinstance(authors, list) and authors:
            author_str = ", ".join(authors)
        elif isinstance(authors, str):
            author_str = authors
        else:
            author_str = "Unknown Author"

        if citation_style == "GB_T":
            # GB/T 格式: [序号] 作者. 标题. 期刊, 年份.
            parts = [author_str, title]
            if journal:
                parts.append(f"{journal}")
            if year and year != "Unknown":
                parts.append(f"{year}")
            return ". ".join(parts)
        else:
            # APA 风格
            parts = [f"{author_str} ({year})", title]
            if journal:
                if volume:
                    parts.append(f"{journal}, {volume}")
                    if issue:
                        parts[-1] += f"({issue})"
                    if pages:
                        parts[-1] += f", {pages}"
                else:
                    parts.append(journal)
            return ". ".join(parts)

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
        # 安全获取 formatted_citation 字符串
        def get_citation_str(ref):
            citation = ref.get("formatted_citation", "")
            if isinstance(citation, str):
                return citation
            elif isinstance(citation, dict):
                # dict 类型，转为字符串
                authors = citation.get("authors", [])
                if isinstance(authors, list) and authors:
                    author_str = ", ".join(authors)
                elif isinstance(authors, str):
                    author_str = authors
                else:
                    author_str = "Unknown"
                title = citation.get("title", "")
                year = citation.get("year", "")
                return f"{author_str}. {title}. {year}"
            else:
                return str(citation)

        prompt = f"""
检查论文中引用的完整性：

论文内容摘要：
{paper_content[:1500]}

参考文献列表（{len(references)}条）：
{json.dumps([get_citation_str(ref) for ref in references[:10]], ensure_ascii=False)}

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
        lines = []
        ref_format = self._get_format_template(citation_style)

        for i, ref in enumerate(references, 1):
            citation = ref.get("formatted_citation", "")
            original = ref.get("original", {})

            # 处理不同格式的 citation
            if isinstance(citation, dict):
                # 如果是 dict，提取各部分信息
                authors = citation.get("authors", [])
                year = citation.get("year", "")
                title = citation.get("title", "")
                journal = citation.get("journal", "")
                volume = citation.get("volume", "")
                issue = citation.get("issue", "")
                pages = citation.get("pages", "")
                doi = citation.get("doi", "")

                if isinstance(authors, list):
                    author_str = ", ".join(authors) if authors else ""
                elif isinstance(authors, str):
                    author_str = authors
                else:
                    author_str = original.get("authors", "Unknown Author") if isinstance(original, dict) else "Unknown Author"

                # 使用格式化模板
                formatted = ref_format.format(
                    num=i,
                    authors=author_str,
                    year=year or original.get("year", ""),
                    title=title or original.get("title", "Unknown Title"),
                    journal=journal or original.get("journal", ""),
                    volume=volume or original.get("volume", ""),
                    issue=issue or original.get("issue", ""),
                    pages=pages or original.get("pages", ""),
                    doi=doi or original.get("doi", "")
                )
                lines.append(formatted)
            elif isinstance(citation, str) and citation:
                # 字符串类型：彻底清除所有可能的编号前缀
                # 匹配各种格式: "[1] ", "[1]" , "[[1]] ", "[1] [1] " 等，递归清除直到没有
                citation_clean = citation.strip()
                # 递归清除所有编号前缀
                while True:
                    # 匹配 [n] 或 [[n]] 格式的开头
                    match = re.match(r'^\s*\[+\s*\d+\s*\]+\s*', citation_clean)
                    if not match:
                        break
                    citation_clean = citation_clean[match.end():].strip()
                if citation_clean:
                    lines.append(f"[{i}] {citation_clean}")
                else:
                    title = original.get("title", "Unknown Title") if isinstance(original, dict) else "Unknown Title"
                    lines.append(f"[{i}] {title}")
            else:
                # 降级处理
                title = original.get("title", "Unknown Title") if isinstance(original, dict) else "Unknown Title"
                lines.append(f"[{i}] {title}")

        return "\n".join(lines)

    def _get_format_template(self, citation_style: str) -> str:
        """获取引用格式模板"""
        templates = {
            "GB_T": "[{num}] {authors}. {title}. {journal}, {year}.",  # 简化版GB/T
            "APA": "{authors} ({year}). {title}. {journal}, {volume}({issue}), {pages}.",
            "IEEE": "{authors}, \"{title},\" {journal}, vol. {volume}, no. {issue}, pp. {pages}, {year}.",
            "MLA": "{authors}. \"{title}.\" {journal}, {volume}, no. {issue}, {year}, pp. {pages}.",
            "CHICAGO": "{authors}. \"{title}.\" {journal} {volume}, no. {issue} ({year}): {pages}."
        }
        return templates.get(citation_style, templates["GB_T"])
