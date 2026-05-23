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

    @classmethod
    def from_env(cls, overrides: Optional[Dict[str, Any]] = None) -> "ReportConfig":
        """从环境变量加载配置

        Args:
            overrides: 覆盖值，如 {"report_type": ReportType.DAILY}
        """
        import os
        config = cls()

        # 从环境变量加载默认主题
        default_topic = os.getenv("DEFAULT_REPORT_TOPIC", "")
        if default_topic:
            config.topic = default_topic

        # 从环境变量加载语言设置
        language = os.getenv("REPORT_LANGUAGE", "zhCN")
        if language:
            config.style = language

        # 从环境变量加载目录设置
        include_toc = os.getenv("REPORT_INCLUDE_TOC", "true").lower()
        config.include_toc = include_toc in ("true", "1", "yes")

        # 从环境变量加载参考文献设置
        include_refs = os.getenv("REPORT_INCLUDE_REFERENCES", "true").lower()
        config.include_references = include_refs in ("true", "1", "yes")

        # 应用覆盖值
        if overrides:
            for key, value in overrides.items():
                if key == "report_type" and isinstance(value, ReportType):
                    config.report_type = value
                elif hasattr(config, key):
                    setattr(config, key, value)

        return config

    @staticmethod
    def get_local_date(env_var: str = None, days_offset: int = 0) -> str:
        """获取本地日期（基于系统时间）

        Args:
            env_var: 环境变量名，如果有则优先使用环境变量的值
            days_offset: 日期偏移天数（相对于今天）

        Returns:
            格式化的日期字符串 (YYYY-MM-DD)
        """
        import os
        from datetime import datetime, timedelta

        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                return env_value

        now = datetime.now()
        if days_offset:
            now = now + timedelta(days=days_offset)
        return now.strftime("%Y-%m-%d")

    @staticmethod
    def get_local_month(env_var: str = None, month_offset: int = 0) -> str:
        """获取本地月份（基于系统时间）

        Args:
            env_var: 环境变量名，如果有则优先使用环境变量的值
            month_offset: 月份偏移（正数为未来，负数为过去）

        Returns:
            格式化的月份字符串 (YYYY-MM)
        """
        import os
        from datetime import datetime

        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                return env_value

        now = datetime.now()
        if month_offset:
            # 计算偏移后的月份
            total_month = now.year * 12 + now.month + month_offset - 1
            year = total_month // 12
            month = total_month % 12 + 1
            return f"{year:04d}-{month:02d}"

        return now.strftime("%Y-%m")


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
                formatted = ref.get('formatted', str(ref))
                # 确保每条引用单独一行且格式正确
                if not formatted.strip().startswith('['):
                    lines.append(f"[{i+1}] {formatted}")
                else:
                    lines.append(formatted)
                lines.append("")  # 空行分隔每条参考文献

        return "\n".join(lines)

    def save_to_file(self, folder: str = "reports") -> str:
        """
        保存报告到指定文件夹

        Args:
            folder: 输出子文件夹路径（相对于 output/）

        Returns:
            保存的文件路径
        """
        import os

        # 查找项目根目录（向上查找 output 目录或 src 目录）
        current = os.path.dirname(os.path.abspath(__file__))
        # 从 src/agents_v2/reports/base.py 向上两级到项目根
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))

        output_dir = os.path.join(project_root, "output", folder)
        os.makedirs(output_dir, exist_ok=True)

        # 生成文件名
        date_str = self.metadata.get("date", self.metadata.get("month", ""))
        if "start_date" in self.metadata:
            date_str = f"{self.metadata['start_date']}_{self.metadata['end_date']}"

        # 清理文件名
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in self.title[:50])
        filename = f"{safe_title}_{date_str}.md"
        filepath = os.path.join(output_dir, filename)

        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())

        return filepath

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
                max_tokens=8192
            )

            from langchain_core.messages import HumanMessage
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            raw_content = response.content if hasattr(response, 'content') else str(response)

            # 清理思考过程标记 - 使用更精确的清理方式避免误删内容
            import re
            cleaned = raw_content
            # 移除 markdown 中的思考标记块（中英文）- 使用 [\s\S] 匹配所有字符包括换行
            cleaned = re.sub(r'\[think\][\s\S]*?\[/think\]', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned, flags=re.IGNORECASE)
            # 移除独立存在的 <think> 和</think> 标记
            cleaned = re.sub(r'<think>\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s*</think>', '', cleaned, flags=re.IGNORECASE)
            # 移除 ```json ```text 等包裹的思考块内容
            cleaned = re.sub(r'```(?:json|text|python)?\s*\(.*?\)\s*```', '', cleaned, flags=re.DOTALL)
            cleaned = re.sub(r'```(?:json|text|python)?[\s\S]*?```', '', cleaned, flags=re.DOTALL)
            # 移除LLM产生的结构提纲（出现在真正内容之前的规划性文字）
            cleaned = re.sub(r'^让我按照结构来组织内容：.*?(?=## 一、研究背景)', '', cleaned, flags=re.DOTALL | re.MULTILINE)
            cleaned = re.sub(r'^让我开始撰写.*$', '', cleaned, flags=re.MULTILINE)
            # 移除开头的占位符大纲（包含-列表项的结构）
            # 匹配任何 ## 章节标题后紧跟的 bullet list (以-开头的行)
            cleaned = re.sub(r'^## [一二三四五]、[^\\n]*\\n\\s*-.*', '', cleaned, flags=re.MULTILINE)
            # 移除章节标题后面紧跟的"每章至少200字"等提示行
            cleaned = re.sub(r'^每章至少200字[。.]*$', '', cleaned, flags=re.MULTILINE)
            # 移除章节后紧跟的"对比不同论文的方法论"等占位提示
            cleaned = re.sub(r'^对比不同论文的方法论.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^总结研究结论和未来研究方向.*$', '', cleaned, flags=re.MULTILINE)
            # 移除段落开头明显的引导性文字（不包含括号内容的行）
            cleaned = re.sub(r'^现在(开始)?撰写.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^现在开始撰写.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^Write.*?in Chinese.*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r'^Please.*?output.*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r'^Ok\..*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^We need to.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^需要涵盖：.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^让我们.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^首先.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^接下来.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^下面.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^最后.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^以下是.*$', '', cleaned, flags=re.MULTILINE)
            # 移除包含"Write"、"Now generate"、"Should be careful"等的行
            _think_pattern = r'^.*?(Now generate|Write content|Write detailed|Should be careful|Let.*s draft|需要|我们来|现在来|需要涵盖|现在我们).*$'
            cleaned = re.sub(_think_pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            # 移除分析性/规划性英文内容（如"We'll say..."、"Method: ..."等）
            cleaned = re.sub(r"^We'll say.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Method:.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Key results:.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Contribution:.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Limitations:.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^It says.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Maybe we.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Thus the.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Add more.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^But the user.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^The user said.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^However,.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Possibly we can.*$", '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            # 移除类似 "(Discuss why L0 regularization...)" 这样的独立思考行
            cleaned = re.sub(r'^\s*\(Discuss.*\)\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r'^\s*\(First.*\)\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r'^\s*\(.*?Write.*?\)\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r'^\s*\(.*?need.*?\)\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            # 移除 "List with full citation." 等明显不是正文的句子
            cleaned = re.sub(r'^List with full citation\.$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r'^Now we need to ensure.*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
            # 移除中文占位符内容（如"（详细阐述...）"、"（总结...）"等）
            cleaned = re.sub(r'^（[^）]+）$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^【[^】]+】$', '', cleaned, flags=re.MULTILINE)
            # 移除结构框架类说明行
            cleaned = re.sub(r'^#+\s*结构框架.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^\d+\.\s*研究背景.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^\d+\.\s*核心论文.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^\d+\.\s*主要研究.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^\d+\.\s*技术方法.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^\d+\.\s*结论.*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^\d+\.\s*参考文献.*$', '', cleaned, flags=re.MULTILINE)
            # 移除重复的参考文献部分（第二个 ## 参考文献 及其后内容）
            dup_ref_match = re.search(r'\n## 参考文献\n.*?\n(\[.*?Vaswani.*?\])', cleaned, re.DOTALL)
            if dup_ref_match:
                cleaned = cleaned[:dup_ref_match.start()]
            # 清理多余的空行
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

            # 移除开头的重复标题行（如"# 稀疏函数数据研究文献综述"）
            cleaned = re.sub(r'^#\s*稀疏函数数据研究文献综述\s*$', '', cleaned, flags=re.MULTILINE)
            # 只移除纯章节引导行（如"一、研究背景"单独一行，没有内容）
            cleaned = re.sub(r'^一、研究背景\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^二、核心论文分析\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^三、主要研究发现\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^四、技术方法对比\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^五、结论与展望\s*$', '', cleaned, flags=re.MULTILINE)
            # 移除孤立的章节标题行后面没有内容的情况
            cleaned = re.sub(r'\n+(?=#+\s+[一二三四五])', '\n', cleaned)

            # 移除开头的英文请求/指令文本（LLM可能在输出开头重复用户的请求）
            # 匹配以 "The user is asking" 或 "User要求" 等开头的段落
            cleaned = re.sub(r'^The user (?:is asking|said|wanted).*?\n\n', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
            cleaned = re.sub(r'^用户要求.*?\n\n', '', cleaned, flags=re.DOTALL)
            cleaned = re.sub(r'^用户.*?(?=##\s)', '', cleaned, flags=re.DOTALL)
            # 匹配类似 "Let me analyze the requirements:" 这类引导语
            cleaned = re.sub(r'^Let me analyze.*?\n\n', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
            cleaned = re.sub(r'^让我.*?\n\n', '', cleaned, flags=re.DOTALL)

            return cleaned.strip() if cleaned else raw_content

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
            line_stripped = line.strip()

            # 跳过空行
            if not line_stripped:
                continue

            # 检测标题（## 开头）
            if line_stripped.startswith("##"):
                # 保存之前的章节
                if current_section and current_content:
                    current_section.content = "\n".join(current_content)
                    sections.append(current_section)

                # 解析新标题
                level = len(line_stripped) - len(line_stripped.lstrip("#"))
                title = line_stripped.lstrip("#").strip()

                current_section = ReportSection(
                    title=title,
                    level=level,
                    content=""
                )
                current_content = []

            elif current_section:
                # 如果有当前章节，累加内容
                current_content.append(line_stripped)

        # 保存最后一个章节
        if current_section and current_content:
            current_section.content = "\n".join(current_content)
            sections.append(current_section)

        return sections