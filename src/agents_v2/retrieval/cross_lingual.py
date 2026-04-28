"""
跨语言处理模块

功能:
1. 中英文混合输入处理
2. 跨语言检索（用中文查英文论文）
3. 多语言输出质量保证

设计原则:
- 检测输入语言混合情况
- 提供语言统一的预处理
- 支持跨语言查询扩展
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """语言枚举"""
    CHINESE = "zh"
    ENGLISH = "en"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class LanguageDetectionResult:
    """语言检测结果"""
    primary_language: Language
    mixed_ratio: float  # 混合比例 (0-1)
    chinese_ratio: float
    english_ratio: float
    has_mixed: bool
    detected_scripts: List[str] = field(default_factory=list)


@dataclass
class CrossLingualQuery:
    """跨语言查询"""
    original: str
    expanded: List[str]  # 扩展后的多语言查询
    source_language: Language
    translations: Dict[str, str]  # term -> translation
    retrieval_queries: List[str]  # 用于检索的查询列表


class CrossLingualProcessor:
    """跨语言处理器

    处理中英文混合输入，支持跨语言检索
    """

    # 常见中英文术语对照表
    TERMINOLOGY_MAP = {
        # AI/ML 术语
        "机器学习": "machine learning",
        "深度学习": "deep learning",
        "神经网络": "neural network",
        "人工智能": "artificial intelligence",
        "自然语言处理": "natural language processing",
        "计算机视觉": "computer vision",
        "强化学习": "reinforcement learning",
        "监督学习": "supervised learning",
        "无监督学习": "unsupervised learning",
        "生成模型": "generative model",
        "大语言模型": "large language model",
        "LLM": "large language model",
        "Transformer": "transformer",
        "注意力机制": "attention mechanism",
        "BERT": "BERT",
        "GPT": "GPT",

        # 研究方法术语
        "论文": "paper",
        "研究": "research",
        "方法": "method",
        "模型": "model",
        "算法": "algorithm",
        "实验": "experiment",
        "结果": "results",
        "准确率": "accuracy",
        "召回率": "recall",
        "F1": "F1 score",
        "数据集": "dataset",
        "训练": "training",
        "测试": "testing",
        "验证": "validation",

        # 学术写作术语
        "摘要": "abstract",
        "引言": "introduction",
        "结论": "conclusion",
        "参考文献": "references",
        "文献综述": "literature review",
        "相关工作": "related work",
        "实验结果": "experimental results",
        "贡献": "contribution",
    }

    def __init__(self):
        self._init_cache()

    def _init_cache(self):
        """初始化缓存"""
        self.detection_cache: Dict[str, LanguageDetectionResult] = {}
        self.translation_cache: Dict[str, str] = {}

    def detect_language(self, text: str) -> LanguageDetectionResult:
        """检测文本语言

        Args:
            text: 输入文本

        Returns:
            LanguageDetectionResult
        """
        # 检查缓存
        if text in self.detection_cache:
            return self.detection_cache[text]

        # 统计中英文字符
        chinese_chars = 0
        english_chars = 0
        total_chars = len(text)

        for char in text:
            if '一' <= char <= '鿿':
                chinese_chars += 1
            elif char.isalpha():
                english_chars += 1

        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0

        # 判断主语言
        if chinese_ratio > 0.3 and english_ratio > 0.3:
            primary = Language.MIXED
        elif chinese_ratio > english_ratio:
            primary = Language.CHINESE
        elif english_ratio > chinese_ratio:
            primary = Language.ENGLISH
        else:
            primary = Language.UNKNOWN

        result = LanguageDetectionResult(
            primary_language=primary,
            mixed_ratio=min(chinese_ratio, english_ratio) * 2,
            chinese_ratio=chinese_ratio,
            english_ratio=english_ratio,
            has_mixed=primary == Language.MIXED,
            detected_scripts=["zh" if chinese_ratio > 0 else "", "en" if english_ratio > 0 else ""]
        )

        # 缓存结果
        self.detection_cache[text] = result

        return result

    def translate_term(self, term: str) -> Optional[str]:
        """翻译单个术语

        Args:
            term: 术语

        Returns:
            翻译结果，如果没有找到则返回None
        """
        # 检查缓存
        if term in self.translation_cache:
            return self.translation_cache[term]

        # 精确匹配
        if term in self.TERMINOLOGY_MAP:
            translation = self.TERMINOLOGY_MAP[term]
            self.translation_cache[term] = translation
            return translation

        # 大小写不敏感匹配
        term_lower = term.lower()
        for cn, en in self.TERMINOLOGY_MAP.items():
            if cn.lower() == term_lower or en.lower() == term_lower:
                self.translation_cache[term] = en
                return en

        return None

    def normalize_mixed_query(self, query: str) -> CrossLingualQuery:
        """标准化混合语言查询

        Args:
            query: 混合语言查询

        Returns:
            CrossLingualQuery: 跨语言查询对象
        """
        language_info = self.detect_language(query)

        translations = {}
        expanded_terms = []

        # 提取并翻译术语
        for term, translation in self.TERMINOLOGY_MAP.items():
            if term in query:
                translations[term] = translation
                expanded_terms.append(translation)

        # 生成扩展查询
        retrieval_queries = self._generate_retrieval_queries(
            query, language_info, translations
        )

        return CrossLingualQuery(
            original=query,
            expanded=[query] + list(translations.values()),
            source_language=language_info.primary_language,
            translations=translations,
            retrieval_queries=retrieval_queries
        )

    def _generate_retrieval_queries(
        self,
        query: str,
        language_info: LanguageDetectionResult,
        translations: Dict[str, str]
    ) -> List[str]:
        """生成用于检索的查询列表

        Args:
            query: 原始查询
            language_info: 语言检测结果
            translations: 术语翻译映射

        Returns:
            List[str]: 检索查询列表
        """
        queries = []

        # 原始查询
        queries.append(query)

        # 如果是中文，添加英文翻译版本
        if language_info.primary_language == Language.CHINESE:
            # 替换中文术语为英文
            english_query = query
            for cn, en in translations.items():
                english_query = english_query.replace(cn, en)

            if english_query != query:
                queries.append(english_query)

            # 也添加纯中文查询
            # queries.append(query)  # 已添加

        # 如果是英文，添加中文翻译版本
        elif language_info.primary_language == Language.ENGLISH:
            chinese_query = query
            for en, cn in self._get_reverse_translations().items():
                if en.lower() in query.lower():
                    chinese_query = chinese_query.replace(en, cn)

            if chinese_query != query:
                queries.append(chinese_query)

        # 混合语言：尝试统一到英文（学术论文检索更常用）
        elif language_info.primary_language == Language.MIXED:
            english_version = query
            for cn, en in translations.items():
                english_version = english_version.replace(cn, en)

            queries.append(english_version)

        # 去重
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        return unique_queries

    def _get_reverse_translations(self) -> Dict[str, str]:
        """获取反向翻译映射（英文->中文）"""
        reverse_map = {}
        for cn, en in self.TERMINOLOGY_MAP.items():
            reverse_map[en] = cn
        return reverse_map

    def expand_for_cross_lingual(
        self,
        query: str,
        target_language: Language = Language.ENGLISH
    ) -> List[str]:
        """为跨语言检索扩展查询

        Args:
            query: 原始查询
            target_language: 目标语言（用于检索）

        Returns:
            List[str]: 扩展后的查询列表
        """
        cross_lingual_query = self.normalize_mixed_query(query)
        expanded = [cross_lingual_query.original]

        # 添加翻译版本
        for term, translation in cross_lingual_query.translations.items():
            if target_language == Language.ENGLISH:
                # 添加英文翻译
                if translation not in expanded:
                    expanded.append(translation)
            else:
                # 添加中文翻译
                if term not in expanded:
                    expanded.append(term)

        # 添加组合查询
        if len(cross_lingual_query.translations) > 1:
            # 组合多个翻译
            translations_list = list(cross_lingual_query.translations.values())
            combined = " ".join(translations_list)
            if combined not in expanded:
                expanded.append(combined)

        return expanded[:10]  # 最多10个查询

    def preprocess_for_retrieval(self, query: str) -> Dict[str, Any]:
        """预处理查询用于检索

        Args:
            query: 用户查询

        Returns:
            Dict包含:
                - normalized_query: 标准化后的查询
                - language_info: 语言检测结果
                - retrieval_queries: 用于检索的查询列表
                - terms_to_translate: 需要翻译的术语
        """
        language_info = self.detect_language(query)
        cross_lingual = self.normalize_mixed_query(query)

        # 提取需要翻译的关键术语
        terms_to_translate = []
        for term in self.TERMINOLOGY_MAP.keys():
            if term in query:
                terms_to_translate.append({
                    "original": term,
                    "translation": self.TERMINOLOGY_MAP[term]
                })

        return {
            "normalized_query": cross_lingual.original,
            "language_info": {
                "primary": language_info.primary_language.value,
                "chinese_ratio": language_info.chinese_ratio,
                "english_ratio": language_info.english_ratio,
                "is_mixed": language_info.has_mixed
            },
            "retrieval_queries": cross_lingual.retrieval_queries,
            "terms_to_translate": terms_to_translate,
            "source_language": cross_lingual.source_language.value
        }


class MultiLanguageOutputProcessor:
    """多语言输出处理器

    确保多语言输出的质量
    """

    def __init__(self):
        self.allowed_languages = [Language.CHINESE, Language.ENGLISH]

    def ensure_output_language(
        self,
        text: str,
        target_language: Language
    ) -> str:
        """确保输出指定语言

        Args:
            text: 输出文本
            target_language: 目标语言

        Returns:
            str: 处理后的文本
        """
        if target_language == Language.CHINESE:
            return self._to_chinese(text)
        elif target_language == Language.ENGLISH:
            return self._to_english(text)
        return text

    def _to_chinese(self, text: str) -> str:
        """转换为中文（如果原文是英文）"""
        # 检测是否主要是英文
        english_ratio = sum(1 for c in text if c.isalpha() and ord(c) < 128) / max(len(text), 1)

        if english_ratio > 0.7:
            # 需要翻译（简化处理，实际应该调用翻译API）
            return self._basic_translate(text)
        return text

    def _to_english(self, text: str) -> str:
        """转换为英文（如果原文是中文）"""
        # 检测是否主要是中文
        chinese_ratio = sum(1 for c in text if '一' <= c <= '鿿') / max(len(text), 1)

        if chinese_ratio > 0.5:
            # 需要翻译（简化处理）
            return self._basic_translate(text, target="en")
        return text

    def _basic_translate(self, text: str, target: str = "zh") -> str:
        """基本翻译（使用术语表）

        注意：这是简化版本，实际应该调用翻译API
        """
        translated = text

        if target == "zh":
            # 英中翻译
            reverse_map = {
                v: k for k, v in CrossLingualProcessor.TERMINOLOGY_MAP.items()
            }
            for en, cn in reverse_map.items():
                translated = re.sub(rf'\b{re.escape(en)}\b', cn, translated, flags=re.IGNORECASE)
        else:
            # 中英翻译
            for cn, en in CrossLingualProcessor.TERMINOLOGY_MAP.items():
                translated = re.sub(rf'\b{re.escape(cn)}\b', en, translated)

        return translated

    def mix_output_quality_check(self, text: str) -> Dict[str, Any]:
        """检查混合输出的质量

        Args:
            text: 输出文本

        Returns:
            Dict: 质量检查结果
        """
        issues = []

        # 检查中英文标点混用
        has_mixed_punctuation = bool(
            re.search(r'[一-鿿][.!?]', text) or
            re.search(r'[a-zA-Z][。！？]', text)
        )
        if has_mixed_punctuation:
            issues.append("Mixed Chinese and English punctuation")

        # 检查空格一致性
        has_inconsistent_spaces = bool(
            re.search(r'\w[一-鿿]', text) or
            re.search(r'[一-鿿]\w', text)
        )
        if has_inconsistent_spaces:
            issues.append("Missing spaces between Chinese and English")

        # 检查术语一致性
        terminology_issues = self._check_terminology_consistency(text)
        issues.extend(terminology_issues)

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "suggestion": self._generate_fix_suggestion(issues)
        }

    def _check_terminology_consistency(self, text: str) -> List[str]:
        """检查术语一致性"""
        issues = []

        # 检查同一术语是否有混用
        for cn, en in CrossLingualProcessor.TERMINOLOGY_MAP.items():
            if cn in text and en in text:
                issues.append(f"Term inconsistency: '{cn}' and '{en}' both appear")

        return issues

    def _generate_fix_suggestion(self, issues: List[str]) -> str:
        """生成修复建议"""
        if not issues:
            return "No issues found."

        suggestions = []
        for issue in issues:
            if "punctuation" in issue.lower():
                suggestions.append("Use consistent punctuation marks for each language")
            elif "spaces" in issue.lower():
                suggestions.append("Add spaces between Chinese and English text")
            elif "inconsistency" in issue.lower():
                suggestions.append("Use consistent terminology throughout")

        return " ".join(suggestions)


# 便捷函数
def detect_language(text: str) -> LanguageDetectionResult:
    """检测文本语言"""
    processor = CrossLingualProcessor()
    return processor.detect_language(text)


def normalize_query(query: str) -> CrossLingualQuery:
    """标准化混合语言查询"""
    processor = CrossLingualProcessor()
    return processor.normalize_mixed_query(query)


def expand_for_retrieval(query: str, target: Language = Language.ENGLISH) -> List[str]:
    """为跨语言检索扩展查询"""
    processor = CrossLingualProcessor()
    return processor.expand_for_cross_lingual(query, target)


def preprocess(query: str) -> Dict[str, Any]:
    """预处理查询用于检索"""
    processor = CrossLingualProcessor()
    return processor.preprocess_for_retrieval(query)