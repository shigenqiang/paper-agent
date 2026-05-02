"""
章节专门写作策略

功能:
1. 针对论文各章节实现专门的写作策略
2. 摘要：结构化 vs 非结构化
3. 引言：背景→gap→贡献
4. 方法：技术细节可复现性
5. 结果：数据呈现逻辑性
6. 讨论：与已有工作对比

设计原则:
- 每个章节类型有专门的处理逻辑
- 生成时考虑章节间的衔接
- 输出符合学术规范的章节内容
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import json

logger = get_logging_logger(__name__)


class ChapterType(str, Enum):
    """章节类型枚举"""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHOD = "method"
    EXPERIMENT = "experiment"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    OTHER = "other"


@dataclass
class ChapterWritingContext:
    """章节写作上下文"""
    chapter_type: ChapterType
    chapter_title: str
    previous_chapters: List[str]  # 前序章节内容摘要
    next_chapter_hint: str = ""  # 下一章的提示（用于过渡）
    thesis_statement: str = ""
    key_claims: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    figures_expected: int = 0
    tables_expected: int = 0


@dataclass
class ChapterWritingResult:
    """章节写作结果"""
    content: str
    chapter_type: ChapterType
    word_count: int
    section_structure: List[str]  # 子章节结构
    citations_used: List[str]  # 使用的引用编号
    key_points: List[str]  # 关键点
    transitions_used: List[str]  # 使用的过渡词


class AbstractWriter:
    """摘要撰写器"""

    STRUCTURED_TEMPLATE = """
请为以下论文撰写结构化摘要：

研究主题：{topic}
研究论点：{thesis}

主要发现：{findings}

方法：{method}

结论：{conclusion}

要求：
- 使用结构化格式（Background, Objective, Method, Results, Conclusion）
- 简洁明了，200-300字
- 不使用缩写
- 以第3人称撰写

请生成完整的结构化摘要。
"""

    UNSTRUCTURED_TEMPLATE = """
为以下论文撰写摘要：

研究主题：{topic}
研究论点：{thesis}

关键发现：
{findings}

请生成完整的非结构化摘要，要求：
- 简洁明了，200-300字
- 逻辑连贯
- 突出主要贡献
"""

    @staticmethod
    def write(
        topic: str,
        thesis: str,
        findings: List[str],
        method: str = "",
        conclusion: str = "",
        structured: bool = True
    ) -> str:
        """撰写摘要"""
        if structured:
            template = AbstractWriter.STRUCTURED_TEMPLATE
            findings_text = "\n".join(f"- {f}" for f in findings)
            return template.format(
                topic=topic,
                thesis=thesis,
                findings=findings_text,
                method=method or "详见正文",
                conclusion=conclusion or "详见正文"
            )
        else:
            template = AbstractWriter.UNSTRUCTURED_TEMPLATE
            findings_text = "\n".join(f"- {f}" for f in findings)
            return template.format(
                topic=topic,
                thesis=thesis,
                findings=findings_text
            )


class IntroductionWriter:
    """引言撰写器"""

    STRUCTURE_TEMPLATE = """
撰写论文引言，遵循以下结构：

## 1. 研究背景（Background）
{background}

## 2. 研究gap（Gap）
现有研究的不足：
{gap}

## 3. 本文贡献（Contributions）
主要贡献：
{contributions}

## 4. 文章结构（Structure）
{structure}

要求：
- 背景介绍要清晰，提供足够上下文
- Gap分析要准确指出不足
- 贡献要明确、具体、可验证
- 结构概述要简洁

请生成完整的引言章节。
"""

    @staticmethod
    def write(
        topic: str,
        thesis: str,
        background: str,
        gap: List[str],
        contributions: List[str],
        structure: str = ""
    ) -> str:
        """撰写引言"""
        gap_text = "\n".join(f"- {g}" for g in gap)
        contrib_text = "\n".join(f"- {c}" for c in contributions)

        return IntroductionWriter.STRUCTURE_TEMPLATE.format(
            background=background,
            gap=gap_text,
            contributions=contrib_text,
            structure=structure or "本文结构如下：第2节介绍相关工作，第3节描述方法，第4节展示实验结果，第5节总结。"
        )


class RelatedWorkWriter:
    """相关工作撰写器"""

    STRUCTURE_TEMPLATE = """
撰写相关工作章节：

## 分类1：{category1}
相关工作描述：
{desc1}

## 分类2：{category2}
相关工作描述：
{desc2}

## 本文与已有工作的区别
{difference}

要求：
- 按主题或方法分类组织
- 客观描述已有工作
- 突出与本文工作的区别

请生成完整的文献综述。
"""

    @staticmethod
    def write(
        literature_summary: Dict[str, Any],
        categories: List[str] = None
    ) -> str:
        """撰写相关工作"""
        if categories is None:
            categories = ["主要方法", "数据集与基准", "评估指标"]

        category_texts = {}
        for i, cat in enumerate(categories, 1):
            cat_key = f"category{i}"
            cat_desc = literature_summary.get(cat, "相关工作描述...")
            category_texts[f"{cat_key}_content"] = cat_desc

        template = RelatedWorkWriter.STRUCTURE_TEMPLATE

        # 动态构建模板
        sections = []
        for i, cat in enumerate(categories, 1):
            sections.append(f"## 分类{i}：{cat}\n{category_texts.get(f'category{i}_content', '相关工作描述...')}")

        diff = literature_summary.get("difference", "本文工作通过[具体方法]解决了[具体问题]，与已有工作相比具有[优势]")

        return RelatedWorkWriter.STRUCTURE_TEMPLATE.format(
            category1=categories[0] if len(categories) > 0 else "主要方法",
            desc1=literature_summary.get(categories[0] if len(categories) > 0 else "主要方法", "相关工作..."),
            category2=categories[1] if len(categories) > 1 else "数据集与基准",
            desc2=literature_summary.get(categories[1] if len(categories) > 1 else "数据集与基准", "相关工作..."),
            difference=diff
        )


class MethodWriter:
    """方法章节撰写器"""

    STRUCTURE_TEMPLATE = """
撰写方法章节，确保技术细节可复现：

## 问题定义
{problem}

## 方法概述
{method_overview}

## 详细设计
{detail}

### 子模块1
{sub1}

### 子模块2
{sub2}

## 实现细节
{implementation}

要求：
- 问题定义清晰
- 方法概述给出整体架构
- 详细设计包含足够的技术细节
- 实现细节说明关键参数和步骤

请生成完整的方法章节。
"""

    @staticmethod
    def write(
        problem: str,
        method_overview: str,
        details: Dict[str, str],
        implementation: str = ""
    ) -> str:
        """撰写方法章节"""
        sub_modules = []
        for i, (name, desc) in enumerate(details.items(), 1):
            sub_modules.append(f"### 子模块{i}：{name}\n{desc}")

        return MethodWriter.STRUCTURE_TEMPLATE.format(
            problem=problem,
            method_overview=method_overview,
            detail="\n\n".join(sub_modules) if sub_modules else "详细设计内容...",
            sub1=list(details.values())[0] if len(details) > 0 else "子模块1描述...",
            sub2=list(details.values())[1] if len(details) > 1 else "子模块2描述...",
            implementation=implementation or "实现细节见算法流程和参数设置表。"
        )


class ExperimentWriter:
    """实验章节撰写器"""

    STRUCTURE_TEMPLATE = """
撰写实验结果章节：

## 实验设置
{setup}

### 数据集
{datasets}

### 基准方法
{baselines}

### 评估指标
{metrics}

## 实验结果
{results}

### 主要结果
{main_results}

### 消融实验
{ablation}

### 敏感性分析
{sensitivity}

## 结果分析
{analysis}

要求：
- 实验设置要完整可复现
- 结果呈现要清晰（使用表格和图表）
- 分析要有洞察

请生成完整的实验章节。
"""

    @staticmethod
    def write(
        setup: str,
        datasets: List[str],
        baselines: List[str],
        metrics: List[str],
        results: Dict[str, Any],
        main_results: str = "",
        ablation: str = "",
        sensitivity: str = ""
    ) -> str:
        """撰写实验章节"""
        datasets_text = "\n".join(f"- {d}" for d in datasets)
        baselines_text = "\n".join(f"- {b}" for b in baselines)
        metrics_text = "\n".join(f"- {m}" for m in metrics)

        return ExperimentWriter.STRUCTURE_TEMPLATE.format(
            setup=setup,
            datasets=datasets_text,
            baselines=baselines_text,
            metrics=metrics_text,
            results=results.get("summary", "实验结果详见表1..."),
            main_results=main_results or results.get("main", "主要结果..."),
            ablation=ablation or results.get("ablation", "消融实验..."),
            sensitivity=sensitivity or results.get("sensitivity", "敏感性分析...")
        )


class ResultsWriter:
    """结果呈现撰写器"""

    TABLE_TEMPLATE = """
\begin{{table}}
\centering
\caption{{表格标题}}
\label{{tab:results}}
\begin{{tabular}}{{|c|c|c|}}
\hline
方法 & 准确率 & 召回率 \\
\hline
{Baseline1} & 0.85 & 0.82 \\
\hline
{Baseline2} & 0.78 & 0.75 \\
\hline
本文 & 0.91 & 0.89 \\
\hline
\end{{tabular}}
\end{{table}}
"""

    @staticmethod
    def format_table(
        headers: List[str],
        rows: List[List[str]],
        caption: str = ""
    ) -> str:
        """格式化表格"""
        header_line = " | ".join(headers)
        separator = "|".join(["---" for _ in headers])

        row_lines = []
        for row in rows:
            row_lines.append(" | ".join(row))

        return f"{caption}\n{header_line}\n{separator}\n" + "\n".join(row_lines)

    @staticmethod
    def write_results_narrative(
        results: Dict[str, Any],
        figures: List[str] = None
    ) -> str:
        """撰写结果叙述"""
        narratives = []

        # 主结果叙述
        if "main" in results:
            narratives.append(f"**主实验结果**：{results['main']}")

        # 表格引用
        if "tables" in results:
            for i, tab in enumerate(results["tables"], 1):
                narratives.append(f"表 {i} 展示了{tab}的结果。")

        # 图表引用
        if figures:
            for i, fig in enumerate(figures, 1):
                narratives.append(f"图 {i} 展示了{fig}。")

        return "\n\n".join(narratives)


class DiscussionWriter:
    """讨论章节撰写器"""

    STRUCTURE_TEMPLATE = """
撰写讨论章节：

## 与已有工作的对比
{comparison}

## 结果的深层解读
{interpretation}

## 局限性与未来工作
{limitations}

## 实际应用意义
{implications}

要求：
- 对比要有深度，指出具体差异
- 解读要有洞察，不能只描述结果
- 局限性要诚实但不过度
- 应用意义要具体

请生成完整的讨论章节。
"""

    @staticmethod
    def write(
        comparison: str,
        interpretation: str,
        limitations: List[str],
        implications: str = ""
    ) -> str:
        """撰写讨论章节"""
        limitations_text = "\n".join(f"- {l}" for l in limitations)

        return DiscussionWriter.STRUCTURE_TEMPLATE.format(
            comparison=comparison,
            interpretation=interpretation,
            limitations=limitations_text,
            implications=implications or "本文提出的方法可以应用于[具体场景]，具有重要的实际价值。"
        )


class ConclusionWriter:
    """结论撰写器"""

    STRUCTURE_TEMPLATE = """
撰写结论章节：

## 主要工作总结
{summary}

## 核心贡献
{contributions}

## 未来方向
{future}

要求：
- 工作总结要简洁精炼
- 贡献要具体可数
- 未来方向要有意义

请生成完整的结论章节。
"""

    @staticmethod
    def write(
        summary: str,
        contributions: List[str],
        future: List[str] = None
    ) -> str:
        """撰写结论"""
        contrib_text = "\n".join(f"- {c}" for c in contributions)
        future_text = "\n".join(f"- {f}" for f in (future or ["探索更高效的模型架构", "扩展到更多应用场景"]))

        return ConclusionWriter.STRUCTURE_TEMPLATE.format(
            summary=summary,
            contributions=contrib_text,
            future=future_text
        )


class ChapterWritingStrategy:
    """章节写作策略管理器

    根据章节类型选择合适的写作策略
    """

    WRITER_MAP = {
        ChapterType.ABSTRACT: AbstractWriter,
        ChapterType.INTRODUCTION: IntroductionWriter,
        ChapterType.RELATED_WORK: RelatedWorkWriter,
        ChapterType.METHOD: MethodWriter,
        ChapterType.EXPERIMENT: ExperimentWriter,
        ChapterType.RESULTS: ResultsWriter,
        ChapterType.DISCUSSION: DiscussionWriter,
        ChapterType.CONCLUSION: ConclusionWriter,
    }

    # 章节标题关键词映射
    TITLE_KEYWORD_MAP = {
        "abstract": ChapterType.ABSTRACT,
        "摘要": ChapterType.ABSTRACT,
        "introduction": ChapterType.INTRODUCTION,
        "引言": ChapterType.INTRODUCTION,
        "related work": ChapterType.RELATED_WORK,
        "相关工作": ChapterType.RELATED_WORK,
        "literature review": ChapterType.RELATED_WORK,
        "文献综述": ChapterType.RELATED_WORK,
        "method": ChapterType.METHOD,
        "方法": ChapterType.METHOD,
        "methodology": ChapterType.METHOD,
        "approach": ChapterType.METHOD,
        "experiment": ChapterType.EXPERIMENT,
        "实验": ChapterType.EXPERIMENT,
        "results": ChapterType.RESULTS,
        "结果": ChapterType.RESULTS,
        "discussion": ChapterType.DISCUSSION,
        "讨论": ChapterType.DISCUSSION,
        "conclusion": ChapterType.CONCLUSION,
        "总结": ChapterType.CONCLUSION,
        "conclusion": ChapterType.CONCLUSION,
    }

    @classmethod
    def detect_chapter_type(cls, title: str) -> ChapterType:
        """根据标题检测章节类型"""
        title_lower = title.lower()

        for keyword, chapter_type in cls.TITLE_KEYWORD_MAP.items():
            if keyword in title_lower:
                return chapter_type

        return ChapterType.OTHER

    @classmethod
    def get_writer(cls, chapter_type: ChapterType):
        """获取对应类型的撰写器"""
        return cls.WRITER_MAP.get(chapter_type)

    @classmethod
    def write_chapter(
        cls,
        chapter_type: ChapterType,
        context: ChapterWritingContext,
        **kwargs
    ) -> ChapterWritingResult:
        """根据章节类型执行撰写"""
        writer = cls.get_writer(chapter_type)

        if writer is None:
            return ChapterWritingResult(
                content=f"Unsupported chapter type: {chapter_type.value}",
                chapter_type=chapter_type,
                word_count=0,
                section_structure=[],
                citations_used=[],
                key_points=[],
                transitions_used=[]
            )

        try:
            # 根据章节类型调用对应的撰写方法
            if chapter_type == ChapterType.ABSTRACT:
                content = writer.write(
                    topic=context.thesis_statement,
                    thesis=context.thesis_statement,
                    findings=context.key_claims,
                    method=kwargs.get("method", ""),
                    conclusion=kwargs.get("conclusion", "")
                )

            elif chapter_type == ChapterType.INTRODUCTION:
                content = writer.write(
                    topic=context.chapter_title,
                    thesis=context.thesis_statement,
                    background=kwargs.get("background", ""),
                    gap=context.key_claims,
                    contributions=kwargs.get("contributions", []),
                    structure=kwargs.get("structure", "")
                )

            elif chapter_type == ChapterType.METHOD:
                content = writer.write(
                    problem=kwargs.get("problem", ""),
                    method_overview=kwargs.get("method_overview", ""),
                    details=kwargs.get("details", {}),
                    implementation=kwargs.get("implementation", "")
                )

            elif chapter_type == ChapterType.EXPERIMENT:
                content = writer.write(
                    setup=kwargs.get("setup", ""),
                    datasets=kwargs.get("datasets", []),
                    baselines=kwargs.get("baselines", []),
                    metrics=kwargs.get("metrics", []),
                    results=kwargs.get("results", {})
                )

            elif chapter_type == ChapterType.DISCUSSION:
                content = writer.write(
                    comparison=kwargs.get("comparison", ""),
                    interpretation=kwargs.get("interpretation", ""),
                    limitations=context.key_claims,
                    implications=kwargs.get("implications", "")
                )

            elif chapter_type == ChapterType.CONCLUSION:
                content = writer.write(
                    summary=kwargs.get("summary", ""),
                    contributions=context.key_claims,
                    future=kwargs.get("future", [])
                )

            else:
                content = kwargs.get("content", "章节内容...")

            return ChapterWritingResult(
                content=content,
                chapter_type=chapter_type,
                word_count=len(content.split()),
                section_structure=cls._extract_sections(content),
                citations_used=cls._extract_citations(content),
                key_points=context.key_claims,
                transitions_used=cls._extract_transitions(content)
            )

        except Exception as e:
            logger.error(f"Chapter writing failed for {chapter_type}: {e}")
            return ChapterWritingResult(
                content=f"Error writing chapter: {str(e)}",
                chapter_type=chapter_type,
                word_count=0,
                section_structure=[],
                citations_used=[],
                key_points=[],
                transitions_used=[]
            )

    @staticmethod
    def _extract_sections(content: str) -> List[str]:
        """提取子章节结构"""
        import re
        sections = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
        return sections

    @staticmethod
    def _extract_citations(content: str) -> List[str]:
        """提取使用的引用"""
        import re
        citations = re.findall(r'\[(\d+)\]', content)
        return list(set(citations))

    @staticmethod
    def _extract_transitions(content: str) -> List[str]:
        """提取使用的过渡词"""
        transition_words = [
            "however", "therefore", "furthermore", "moreover",
            "additionally", "consequently", "meanwhile",
            "另一方面", "因此", "此外", "同时"
        ]

        found = []
        content_lower = content.lower()
        for tw in transition_words:
            if tw.lower() in content_lower:
                found.append(tw)

        return found


# 便捷函数
def detect_chapter(title: str) -> ChapterType:
    """检测章节类型"""
    return ChapterWritingStrategy.detect_chapter_type(title)


def write_chapter(
    chapter_type: ChapterType,
    context: ChapterWritingContext,
    **kwargs
) -> ChapterWritingResult:
    """撰写章节"""
    return ChapterWritingStrategy.write_chapter(chapter_type, context, **kwargs)