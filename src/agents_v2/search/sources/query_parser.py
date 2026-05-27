"""
Query Parser - 查询解析器

解析和理解用户查询。
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set


class QueryIntent(Enum):
    """查询意图"""
    FACTUAL = "factual"           # 事实性问题
    EXPLORATORY = "exploratory"  # 探索性问题
    COMPARATIVE = "comparative"   # 比较性问题
    EXPLANATORY = "explanatory"  # 解释性问题
    ACTION = "action"            # 动作请求


@dataclass
class ParsedQuery:
    """解析后的查询"""
    original: str
    intent: QueryIntent
    keywords: List[str]
    entities: List[str]
    modifiers: List[str]
    is_temporal: bool = False
    is_quantity: bool = False
    language: str = "mixed"  # "en", "zh", "mixed"


class QueryParser:
    """查询解析器

    功能:
    - 意图识别
    - 关键词提取
    - 实体识别
    - 语言检测
    """

    # 时间相关词
    TEMPORAL_WORDS: Set[str] = {
        "最近", "latest", "recent", "今天", "yesterday", "tomorrow",
        "本周", "上周", "下周", "今年", "去年", "明年",
        "2020", "2021", "2022", "2023", "2024", "2025"
    }

    # 数量相关词
    QUANTITY_WORDS: Set[str] = {
        "多少", "how many", "how much", "数量", "总数", "平均",
        "排名", "top", "best", "first", "second"
    }

    # 意图关键词 - 按优先级排序
    INTENT_KEYWORDS = [
        (QueryIntent.EXPLANATORY, {"为什么", "原因", "why", "reason"}),
        (QueryIntent.COMPARATIVE, {"比较", "对比", "差异", "compare", "difference", "vs"}),
        (QueryIntent.FACTUAL, {"谁", "什么", "when", "where", "who", "what", "which"}),
        (QueryIntent.ACTION, {"找", "搜索", "查找", "find", "search", "get"}),
        (QueryIntent.EXPLORATORY, {"了解", "探索", "研究", "explore", "research", "learn"}),
    ]

    def parse(self, query: str) -> ParsedQuery:
        """解析查询

        Args:
            query: 原始查询字符串

        Returns:
            ParsedQuery: 解析后的查询
        """
        query = query.strip()
        intent = self._detect_intent(query)
        keywords = self._extract_keywords(query)
        entities = self._extract_entities(query)
        modifiers = self._extract_modifiers(query)
        is_temporal = self._check_temporal(query)
        is_quantity = self._check_quantity(query)
        language = self._detect_language(query)

        return ParsedQuery(
            original=query,
            intent=intent,
            keywords=keywords,
            entities=entities,
            modifiers=modifiers,
            is_temporal=is_temporal,
            is_quantity=is_quantity,
            language=language
        )

    def _detect_intent(self, query: str) -> QueryIntent:
        """检测查询意图

        按优先级检查，第一个匹配的成功
        """
        query_lower = query.lower()

        # 按优先级顺序检查
        for intent, keywords in self.INTENT_KEYWORDS:
            if any(kw in query_lower for kw in keywords):
                return intent

        # 默认返回探索性
        return QueryIntent.EXPLORATORY

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词

        移除停用词，保留有意义的词
        """
        # 停用词
        stop_words = {
            "的", "是", "在", "和", "了", "有", "我", "你", "他",
            "a", "an", "the", "is", "are", "was", "were",
            "this", "that", "these", "those"
        }

        # 简单分词
        words = re.findall(r'[\w]+', query.lower())

        # 过滤停用词和短词
        keywords = [w for w in words if w not in stop_words and len(w) > 1]

        return keywords

    def _extract_entities(self, query: str) -> List[str]:
        """提取实体（简单实现）

        实际应该使用NER模型
        """
        # 简单策略：大写开头的词、品牌名、技术术语
        entities = []

        # 技术术语模式
        tech_patterns = [
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # CamelCase
            r'\b(?:CNN|RNN|LSTM|GPT|BERT|AI|ML|DL)\b',  # 技术缩写
        ]

        for pattern in tech_patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)

        return list(set(entities))

    def _extract_modifiers(self, query: str) -> List[str]:
        """提取修饰词

        如"最新的"、"最好的"等
        """
        modifiers = []
        modifier_patterns = [
            r'(最新的|最好的|最强的|最火的)',
            r'(latest|best|strongest|popular)',
        ]

        for pattern in modifier_patterns:
            matches = re.findall(pattern, query)
            modifiers.extend(matches)

        return modifiers

    def _check_temporal(self, query: str) -> bool:
        """检查是否包含时间相关"""
        query_lower = query.lower()
        return any(word in query_lower for word in self.TEMPORAL_WORDS)

    def _check_quantity(self, query: str) -> bool:
        """检查是否包含数量相关"""
        query_lower = query.lower()
        return any(word in query_lower for word in self.QUANTITY_WORDS)

    def _detect_language(self, query: str) -> str:
        """检测查询语言"""
        # 统计中英文比例
        chinese_chars = len(re.findall(r'[一-鿿]', query))
        english_chars = len(re.findall(r'[a-zA-Z]', query))

        if chinese_chars > english_chars * 2:
            return "zh"
        elif english_chars > chinese_chars * 2:
            return "en"
        return "mixed"


def parse_query(query: str) -> ParsedQuery:
    """便捷函数：解析查询

    Args:
        query: 原始查询

    Returns:
        ParsedQuery
    """
    return QueryParser().parse(query)
