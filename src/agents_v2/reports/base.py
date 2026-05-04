"""
报告生成基类 - Base Report Generator

功能：
1. 定义报告生成的通用接口
2. 配置管理
3. 章节结构定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class ReportType(Enum):
    """报告类型枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    PAPER = "paper"
    RESEARCH = "research"
    CUSTOM = "custom"


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str = ""
    level: int = 1                    # 标题级别 (1, 2, 3)
    order: int = 0                    # 显示顺序
    citations: List[str] = field(default_factory=list)  # 引用列表
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    subsections: List["ReportSection"] = field(default_factory=list)

    def add_subsection(self, section: "ReportSection"):
        """添加子章节"""
        section.level = self.level + 1
        self.subsections.append(section)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "level": self.level,
            "order": self.order,
            "citations": self.citations,
            "metadata": self.metadata,
            "subsections": [s.to_dict() for s in self.subsections]
        }


@dataclass
class ReportConfig:
    """报告配置"""
    report_type: ReportType = ReportType.DAILY
    title: str = ""
    topic: str = ""
    style: str = "formal"              # formal/casual/technical
    citation_style: str = "apa"       # apa/mla/chicago/ieee
    include_toc: bool = True         # 是否包含目录
    include_references: bool = True   # 是否包含参考文献
    max_sections: int = 10            # 最大章节数
    max_references: int = 50         # 最大参考文献数
    llm_config: Optional[Dict[str, Any]] = None


@dataclass
class Report:
    """报告结构"""
    title: str
    config: ReportConfig
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    references: List[Dict[str, Any]] = field(default_factory=list)
    raw_content: str = ""             # 原始内容（LLM生成的未解析内容）

    def add_section(self, section: ReportSection):
        """添加章节"""
        section.order = len(self.sections)
        self.sections.append(section)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "report_type": self.config.report_type.value,
            "sections": [s.to_dict() for s in self.sections],
            "metadata": self.metadata,
            "references": self.references,
            "raw_content": self.raw_content,
        }

    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        lines = [f"# {self.title}\n"]

        for section in self.sections:
            lines.append(self._section_to_markdown(section))

        if self.config.include_references and self.references:
            lines.append("\n## 参考文献\n")
            for i, ref in enumerate(self.references):
                lines.append(f"[{i+1}] {ref.get('formatted', str(ref))}")

        return "\n".join(lines)

    def _section_to_markdown(self, section: ReportSection) -> str:
        """章节转Markdown"""
        lines = []

        if section.title:
            prefix = "#" * section.level
            lines.append(f"\n{prefix} {section.title}\n")

        if section.content:
            lines.append(f"{section.content}\n")

        for subsection in section.subsections:
            lines.append(self._section_to_markdown(subsection))

        return "\n".join(lines)


class BaseReportGenerator(ABC):
    """
    报告生成器基类

    定义报告生成的通用接口和功能
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
        self._llm = None

    @abstractmethod
    async def generate(
        self,
        topic: str = "",
        dates: Optional[tuple] = None,
        **kwargs
    ) -> Report:
        """
        生成报告

        Args:
            topic: 报告主题
            dates: 日期范围 (start_date, end_date)
            **kwargs: 其他参数

        Returns:
            Report 对象
        """
        pass

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM（子类可以重写）"""
        from ..core.base_agent import LLMConfig

        if self.config.llm_config:
            llm_cfg = LLMConfig(**self.config.llm_config)
        else:
            llm_cfg = LLMConfig()

        from ..core.base_agent import BaseAgent

        # 简单的LLM调用
        try:
            from langchain_openai import ChatOpenAI
            import os

            api_key = llm_cfg.api_key or os.getenv("OPENAI_API_KEY")
            base_url = llm_cfg.base_url or os.getenv("OPENAI_BASE_URL")

            if "minimax" in llm_cfg.model_name.lower() and not base_url:
                base_url = "https://api.minimax.chat/v1"

            llm = ChatOpenAI(
                model=llm_cfg.model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0.7,
                max_tokens=4096
            )

            from langchain_core.messages import HumanMessage
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return response.content if hasattr(response, 'content') else str(response)

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""

    def _create_section(
        self,
        title: str,
        content: str = "",
        level: int = 1,
        citations: Optional[List[str]] = None
    ) -> ReportSection:
        """创建章节辅助函数"""
        return ReportSection(
            title=title,
            content=content,
            level=level,
            citations=citations or []
        )

    def _extract_citations(self, text: str) -> List[str]:
        """从文本提取引用"""
        import re

        # 提取 [1], [2,3] 等格式
        pattern = r'\[(\d+(?:\s*,\s*\d+)*)\]'
        matches = re.findall(pattern, text)

        citations = []
        for match in matches:
            citations.extend(match.split(','))
        return [c.strip() for c in citations if c.strip()]

    def _build_toc(self, sections: List[ReportSection]) -> str:
        """构建目录"""
        lines = ["## 目录\n"]

        for section in sections:
            indent = "  " * (section.level - 1)
            lines.append(f"{indent}- {section.title}")

            for subsection in section.subsections:
                indent = "  " * (subsection.level - 1)
                lines.append(f"{indent}- {subsection.title}")

        return "\n".join(lines)

    async def _generate_section_with_llm(
        self,
        section_title: str,
        prompt_template: str,
        **kwargs
    ) -> str:
        """使用LLM生成章节内容"""
        prompt = prompt_template.format(**kwargs)
        return await self._call_llm(prompt)

    def parse_raw_to_sections(self, raw_content: str) -> List[ReportSection]:
        """
        解析原始内容为章节结构

        子类可以重写以实现自定义解析逻辑
        """
        sections = []
        current_section = None
        current_content = []

        lines = raw_content.split("\n")

        for line in lines:
            line = line.strip()

            # 检测标题
            if line.startswith("#"):
                # 保存之前的章节
                if current_section and current_content:
                    current_section.content = "\n".join(current_content)
                    sections.append(current_section)

                # 解析新标题
                level = len(line) - len(line.lstrip("#"))
                title = line.lstrip("#").strip()

                current_section = ReportSection(
                    title=title,
                    level=level,
                    content=""
                )
                current_content = []

            elif current_section:
                current_content.append(line)

        # 保存最后一个章节
        if current_section and current_content:
            current_section.content = "\n".join(current_content)
            sections.append(current_section)

        return sections