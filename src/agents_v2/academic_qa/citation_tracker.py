"""
引用溯源器 - Citation Tracker

支持生成内容的引用溯源和多种引用格式（GB/T 7714、APA 等）。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agents_v2.logging_config import get_logging_logger

import re

logger = get_logging_logger(__name__)


@dataclass
class Citation:
    """引用信息"""
    source_id: str
    source_title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    page: Optional[str] = None
    relevance: float = 0.0
    quoted_text: str = ""
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TracedContent:
    """带溯源的内容块"""
    sentence: str
    source_citation: Optional[Citation] = None
    confidence: float = 0.0
    is_generated: bool = False  # 是否是纯生成内容（非引用）


class CitationTracker:
    """引用溯源器

    功能：
    1. 追溯生成内容中每个句子的来源
    2. 格式化引用为标准格式（GB/T 7714、APA）
    3. 支持 Tool Calling 结构化输出
    """

    CITATION_STYLES = ["gb7714", "apa", "mla", "plain"]

    # Tool Calling 输出格式
    TOOL_SCHEMA = {
        "name": "generate_academic_answer",
        "description": "生成学术级答案，包含可验证的引用来源",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "答案文本"
                },
                "citations": {
                    "type": "array",
                    "description": "引用列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "string"},
                            "source_title": {"type": "string"},
                            "authors": {"type": "array"},
                            "year": {"type": "integer"},
                            "page": {"type": "string"},
                            "relevance": {"type": "number"},
                            "quoted_text": {"type": "string"}
                        }
                    }
                },
                "confidence": {"type": "number"},
                "hallucination_risk": {"type": "string"}
            },
            "required": ["answer", "citations", "confidence"]
        }
    }

    def __init__(
        self,
        threshold: float = 0.3,
        max_citations: int = 10,
        style: str = "gb7714",
    ):
        """初始化引用溯源器

        Args:
            threshold: 相似度阈值，低于此值视为纯生成内容
            max_citations: 最大引用数量
            style: 引用格式风格 ("gb7714", "apa", "mla", "plain")
        """
        self.threshold = threshold
        self.max_citations = max_citations
        self.style = style

    def trace_content(
        self,
        answer: str,
        source_documents: List[Any],
        calc_similarity_fn: Optional[Any] = None,
    ) -> List[TracedContent]:
        """追溯生成内容的来源

        Args:
            answer: 生成的答案
            source_documents: 源文档列表
            calc_similarity_fn: 相似度计算函数

        Returns:
            List[TracedContent]: 带有溯源信息的内容块列表
        """
        if not answer:
            return []

        # 按句子分割
        sentences = self._split_sentences(answer)

        traced_content = []

        for sentence in sentences:
            if not sentence.strip():
                continue

            # 查找最匹配的源文档
            best_match = None
            best_similarity = 0

            if source_documents and calc_similarity_fn:
                for doc in source_documents:
                    content = doc.get("content", doc.get("page_content", str(doc))) if isinstance(doc, dict) else str(doc)
                    similarity = calc_similarity_fn(sentence, content)

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = doc
            elif source_documents:
                # 简单的关键词匹配
                for doc in source_documents:
                    content = doc.get("content", doc.get("page_content", str(doc))) if isinstance(doc, dict) else str(doc)
                    similarity = self._simple_similarity(sentence, content)

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = doc

            # 判断是否是纯生成内容
            is_generated = best_similarity < self.threshold if best_similarity else True

            # 构建引用
            citation = None
            if best_match and not is_generated:
                citation = self._build_citation(best_match, best_similarity)

            traced_content.append(TracedContent(
                sentence=sentence,
                source_citation=citation,
                confidence=best_similarity if best_match else 0.0,
                is_generated=is_generated,
            ))

        return traced_content

    def format_answer_with_citations(
        self,
        answer: str,
        citations: List[Citation],
    ) -> str:
        """格式化带引用的答案

        Args:
            answer: 答案文本
            citations: 引用列表

        Returns:
            str: 格式化后的答案
        """
        if not citations:
            return answer

        # 为每个引用分配序号
        citation_map = {}
        formatted_citations = []

        for i, citation in enumerate(citations[:self.max_citations]):
            citation_map[citation.source_id] = i + 1

        # 在答案中插入引用标记
        formatted_answer = answer

        # 找到答案中出现的关键信息，尝试匹配引用
        for citation in citations[:self.max_citations]:
            if citation.quoted_text and citation.quoted_text in answer:
                idx = formatted_answer.find(citation.quoted_text)
                if idx >= 0:
                    marker = f"[{citation_map[citation.source_id]}]"
                    formatted_answer = (
                        formatted_answer[:idx] +
                        marker +
                        formatted_answer[idx:]
                    )

        # 添加参考文献列表
        if formatted_citations:
            ref_section = "\n\n参考文献：\n"
            for i, cit in enumerate(citations[:self.max_citations], 1):
                ref_section += f"[{i}] {self.format_citation(cit)}\n"
            formatted_answer += ref_section

        return formatted_answer

    def format_citation(self, citation: Citation, style: Optional[str] = None) -> str:
        """格式化单个引用

        Args:
            citation: 引用信息
            style: 格式风格（覆盖初始化时的设置）

        Returns:
            str: 格式化后的引用字符串
        """
        style = style or self.style

        if style == "gb7714":
            return self._format_gb7714(citation)
        elif style == "apa":
            return self._format_apa(citation)
        elif style == "mla":
            return self._format_mla(citation)
        else:
            return self._format_plain(citation)

    def _format_gb7714(self, citation: Citation) -> str:
        """GB/T 7714-2015 格式

        格式：[作者, 年份] 标题
        """
        authors = citation.authors
        title = citation.source_title or "未知标题"
        year = citation.year or "n.d."
        page = citation.page or ""

        if authors:
            # 只显示前3位作者
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += ", et al."
            result = f"[{author_str}, {year}] {title}"
        else:
            result = f"[{title}, {year}]"

        if page:
            result += f", p. {page}"

        return result

    def _format_apa(self, citation: Citation) -> str:
        """APA 格式

        格式：Author(s). (Year). Title. Source.
        """
        authors = citation.authors
        title = citation.source_title or "Unknown Title"
        year = citation.year or "n.d."
        page = citation.page or ""

        if authors:
            if len(authors) == 1:
                author_str = authors[0]
            elif len(authors) == 2:
                author_str = f"{authors[0]} & {authors[1]}"
            else:
                author_str = f"{authors[0]} et al."
            result = f"{author_str} ({year}). {title}"
        else:
            result = f"({year}). {title}"

        if page:
            result += f" (p. {page})"

        return result

    def _format_mla(self, citation: Citation) -> str:
        """MLA 格式

        格式：Author(s). "Title." Source, Year.
        """
        authors = citation.authors
        title = citation.source_title or "Unknown Title"
        year = citation.year or ""

        if authors:
            if len(authors) == 1:
                author_str = authors[0]
            elif len(authors) == 2:
                author_str = f"{authors[0]} and {authors[1]}"
            else:
                author_str = f"{authors[0]}, et al."
            result = f'{author_str}. "{title}."'
        else:
            result = f'"{title}."'

        if year:
            result += f" {year}."

        return result

    def _format_plain(self, citation: Citation) -> str:
        """简单格式

        格式：Title [Authors, Year]
        """
        title = citation.source_title or "Unknown"
        authors = citation.authors
        year = citation.year or ""

        parts = [title]

        if authors:
            author_str = ", ".join(authors[:2])
            if len(authors) > 2:
                author_str += ", et al."
            parts.append(f"[{author_str}, {year}]")
        elif year:
            parts.append(f"[{year}]")

        return " ".join(parts)

    def _build_citation(self, doc: Any, similarity: float) -> Citation:
        """从文档构建引用信息"""
        metadata = doc.get("metadata", {})

        return Citation(
            source_id=doc.get("id", doc.get("chunk_id", "unknown")),
            source_title=metadata.get("title", doc.get("source_title", "未知标题")),
            authors=self._parse_authors(metadata.get("authors", "")),
            year=metadata.get("year"),
            page=metadata.get("page"),
            relevance=similarity,
            quoted_text=doc.get("content", doc.get("page_content", ""))[:200],
            url=metadata.get("url"),
            metadata=metadata,
        )

    def _parse_authors(self, authors_str: Any) -> List[str]:
        """解析作者字符串"""
        if not authors_str:
            return []

        if isinstance(authors_str, list):
            return authors_str

        authors_str = str(authors_str)

        # 常见分隔符
        separators = [", ", "; ", " and ", " & ", "，", "；"]

        for sep in separators:
            if sep in authors_str:
                authors = [a.strip() for a in authors_str.split(sep) if a.strip()]
                if authors:
                    return authors

        # 只有一个作者
        return [authors_str.strip()] if authors_str.strip() else []

    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割"""
        # 中英文句子结束符
        sentence_endings = r'[。！？.!?]+'

        sentences = re.split(sentence_endings, text)
        # 过滤空句子并保留结束符
        result = []
        for s in sentences:
            s = s.strip()
            if s:
                result.append(s)

        return result if result else [text]

    def _simple_similarity(self, text1: str, text2: str) -> float:
        """简单的相似度计算

        基于词集合重叠度。
        """
        if not text1 or not text2:
            return 0.0

        # 提取词
        words1 = set(re.findall(r"[a-zA-Z]+", text1.lower()))
        words2 = set(re.findall(r"[a-zA-Z]+", text2.lower()))

        # 中文词
        chinese1 = set(re.findall(r"[一-鿿]+", text1))
        chinese2 = set(re.findall(r"[一-鿿]+", text2))

        words1 |= chinese1
        words2 |= chinese2

        if not words1:
            return 0.0

        overlap = len(words1 & words2)
        total = len(words1)

        return overlap / total if total > 0 else 0.0

    def generate_tool_output(
        self,
        answer: str,
        citations: List[Citation],
        confidence: float,
        hallucination_risk: str = "unknown",
    ) -> Dict[str, Any]:
        """生成符合 Tool Calling 格式的输出

        Args:
            answer: 答案文本
            citations: 引用列表
            confidence: 置信度
            hallucination_risk: 幻觉风险等级

        Returns:
            Dict: Tool Calling 格式的输出
        """
        return {
            "answer": answer,
            "citations": [
                {
                    "source_id": c.source_id,
                    "source_title": c.source_title,
                    "authors": c.authors,
                    "year": c.year,
                    "page": c.page,
                    "relevance": c.relevance,
                    "quoted_text": c.quoted_text[:500] if c.quoted_text else "",
                }
                for c in citations[:self.max_citations]
            ],
            "confidence": confidence,
            "hallucination_risk": hallucination_risk,
        }

    def extract_citations_from_text(self, text: str) -> List[int]:
        """从文本中提取引用标记

        Args:
            text: 包含引用标记的文本，如 "[1][2]"

        Returns:
            List[int]: 引用序号列表
        """
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, text)
        return [int(m) for m in matches]


# 便捷函数
def format_citation(citation: Citation, style: str = "gb7714") -> str:
    """格式化引用的便捷函数"""
    tracker = CitationTracker(style=style)
    return tracker.format_citation(citation, style)


def trace_and_format(
    answer: str,
    source_documents: List[Dict],
    style: str = "gb7714",
) -> str:
    """追溯并格式化答案的便捷函数

    Args:
        answer: 答案文本
        source_documents: 源文档列表
        style: 引用格式

    Returns:
        str: 带引用的格式化答案
    """
    tracker = CitationTracker(style=style)

    # 提取引用
    citations = []
    for doc in source_documents:
        citation = tracker._build_citation(doc, 0.8)
        citations.append(citation)

    # 格式化和输出
    return tracker.format_answer_with_citations(answer, citations)