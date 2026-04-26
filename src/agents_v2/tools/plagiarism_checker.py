"""
Plagiarism Checker - 查重检测器

检测论文的原创性和重复率。
"""
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class PlagiarismResult:
    """查重结果"""
    similarity_score: float  # 0.0 - 1.0，1.0表示完全重复
    flagged_segments: List["FlaggedSegment"]
    overall_assessment: str  # "original", "minor_similarities", "potential_concerns", "high_similarity"
    checked_at: str


@dataclass
class FlaggedSegment:
    """标记的重复片段"""
    text: str
    source: Optional[str]  # 可能来源
    similarity_type: str  # "exact", "paraphrased", "structural"
    start_pos: int
    end_pos: int
    similarity_score: float


class PlagiarismChecker:
    """查重检测器

    检测文本重复、改写和结构相似性。
    """

    # 停用词（不参与相似度计算）
    STOP_WORDS = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
        "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
        "自己", "这", "那", "它", "他", "她", "们", "这个", "那个", "什么", "怎么",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "to", "of",
        "in", "for", "on", "with", "at", "by", "from", "as", "into", "through"
    }

    # 最小片段长度
    MIN_SEGMENT_LENGTH = 50

    def __init__(self, threshold: float = 0.8):
        """初始化查重检测器

        Args:
            threshold: 相似度阈值，高于此值则标记为重复
        """
        self.threshold = threshold
        self._reference_texts: List[str] = []

    def add_reference(self, text: str) -> None:
        """添加参考文本

        Args:
            text: 参考文本
        """
        self._reference_texts.append(text)

    def check(self, text: str, references: Optional[List[str]] = None) -> PlagiarismResult:
        """检查文本重复

        Args:
            text: 待检查文本
            references: 参考文本列表（可选）

        Returns:
            PlagiarismResult: 查重结果
        """
        if references:
            self._reference_texts.extend(references)

        # 分割成句子/段落
        segments = self._split_into_segments(text)

        # 检查每个片段
        flagged_segments = []
        total_flagged_length = 0

        for segment in segments:
            if len(segment) < self.MIN_SEGMENT_LENGTH:
                continue

            # 检查与参考文本的相似度
            matches = self._check_segment(segment)

            for match in matches:
                if match["score"] >= self.threshold:
                    flagged_segments.append(FlaggedSegment(
                        text=segment,
                        source=match.get("source"),
                        similarity_type=match.get("type", "exact"),
                        start_pos=match.get("pos", 0),
                        end_pos=match.get("pos", 0) + len(segment),
                        similarity_score=match["score"]
                    ))
                    total_flagged_length += len(segment)

        # 计算总体相似度
        total_length = sum(len(s) for s in segments)
        similarity_score = total_flagged_length / total_length if total_length > 0 else 0.0

        # 评估
        assessment = self._assess_plagiarism(similarity_score, len(flagged_segments))

        return PlagiarismResult(
            similarity_score=similarity_score,
            flagged_segments=flagged_segments,
            overall_assessment=assessment,
            checked_at="2026-08-27"  # 简化
        )

    def _split_into_segments(self, text: str) -> List[str]:
        """分割成段落

        Args:
            text: 文本

        Returns:
            List[str]: 段落列表
        """
        # 按段落分割
        paragraphs = text.split("\n\n")

        # 过滤空段落
        return [p.strip() for p in paragraphs if p.strip()]

    def _check_segment(self, segment: str) -> List[Dict[str, Any]]:
        """检查片段

        Args:
            segment: 文本片段

        Returns:
            List[Dict]: 匹配结果列表
        """
        matches = []

        # 清理片段
        cleaned = self._clean_text(segment)

        for ref_text in self._reference_texts:
            ref_cleaned = self._clean_text(ref_text)

            # 检查完全匹配
            if cleaned in ref_cleaned:
                matches.append({
                    "score": 1.0,
                    "type": "exact",
                    "source": ref_text[:100]
                })
                continue

            # 检查改写相似度
            similarity = self._calculate_similarity(cleaned, ref_cleaned)
            if similarity >= self.threshold:
                matches.append({
                    "score": similarity,
                    "type": "paraphrased",
                    "source": ref_text[:100]
                })

        return matches

    def _clean_text(self, text: str) -> str:
        """清理文本

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        # 转小写
        text = text.lower()

        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)

        # 移除多余空格
        text = ' '.join(text.split())

        return text

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            float: 相似度分数
        """
        # 分词
        words1 = self._tokenize(text1)
        words2 = self._tokenize(text2)

        # 计算Jaccard相似度
        set1 = set(words1)
        set2 = set(words2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _tokenize(self, text: str) -> List[str]:
        """分词

        Args:
            text: 文本

        Returns:
            List[str]: 词列表
        """
        words = text.split()

        # 过滤停用词
        words = [w for w in words if w not in self.STOP_WORDS and len(w) > 2]

        return words

    def _assess_plagiarism(self, similarity_score: float, flagged_count: int) -> str:
        """评估重复程度

        Args:
            similarity_score: 相似度分数
            flagged_count: 标记片段数量

        Returns:
            str: 评估结果
        """
        if similarity_score < 0.1:
            return "original"
        elif similarity_score < 0.3:
            return "minor_similarities"
        elif similarity_score < 0.5:
            return "potential_concerns"
        else:
            return "high_similarity"


class StructuralAnalyzer:
    """结构分析器 - 检测结构抄袭"""

    def analyze_structure(self, text: str) -> Dict[str, Any]:
        """分析文本结构

        Args:
            text: 文本

        Returns:
            Dict[str, Any]: 结构分析结果
        """
        # 句子长度分布
        sentences = self._split_sentences(text)
        sentence_lengths = [len(s) for s in sentences]

        # 段落结构
        paragraphs = text.split("\n\n")
        paragraph_lengths = [len(p) for p in paragraphs]

        # 词汇多样性
        words = text.split()
        word_freq = Counter(words)
        unique_ratio = len(word_freq) / len(words) if words else 0

        return {
            "sentence_count": len(sentences),
            "avg_sentence_length": sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0,
            "paragraph_count": len(paragraphs),
            "avg_paragraph_length": sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0,
            "vocabulary_diversity": unique_ratio,
            "long_sentence_count": sum(1 for l in sentence_lengths if l > 50),
            "short_sentence_count": sum(1 for l in sentence_lengths if l < 10)
        }

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子

        Args:
            text: 文本

        Returns:
            List[str]: 句子列表
        """
        # 简单按句号/问号/感叹号分割
        sentences = re.split(r'[。！？.?!]', text)
        return [s.strip() for s in sentences if s.strip()]


# 便捷函数
def check_plagiarism(text: str, references: Optional[List[str]] = None) -> PlagiarismResult:
    """查重的便捷函数

    Args:
        text: 待检查文本
        references: 参考文本列表

    Returns:
        PlagiarismResult: 查重结果
    """
    checker = PlagiarismChecker()
    return checker.check(text, references)
