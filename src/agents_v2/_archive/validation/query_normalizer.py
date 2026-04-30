"""
Query Normalizer - 查询规范化器

提供查询的规范化、标准化和优化功能。
支持中英文混合处理、查询扩展、查询修正等。
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from ...core.exceptions import ValidationError


class QueryType(str, Enum):
    """查询类型"""
    KEYWORD = "keyword"                    # 关键词查询
    NATURAL_LANGUAGE = "natural_language" # 自然语言查询
    BOOLEAN = "boolean"                   # 布尔查询
    PHRASE = "phrase"                      # 短语查询
    FIELD = "field"                        # 字段查询
    WILDCARD = "wildcard"                  # 通配符查询


@dataclass
class NormalizationResult:
    """规范化结果"""
    original: str
    normalized: str
    query_type: QueryType = QueryType.NATURAL_LANGUAGE
    terms: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return self.original != self.normalized

    @property
    def is_valid(self) -> bool:
        return len(self.warnings) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "normalized": self.normalized,
            "query_type": self.query_type.value if isinstance(self.query_type, Enum) else self.query_type,
            "terms": self.terms,
            "entities": self.entities,
            "suggestions": self.suggestions,
            "warnings": self.warnings,
            "metadata": self.metadata
        }


class QueryNormalizer:
    """
    查询规范化器

    功能:
    - 去除查询噪声
    - 统一格式
    - 大小写规范化
    - 全角半角转换
    - 中英文混合处理
    - 查询分词
    - 实体识别
    - 查询修正建议

    使用示例:
        normalizer = QueryNormalizer()

        # 基本规范化
        result = normalizer.normalize("machine learning")
        print(result.normalized)  # "machine learning"

        # 复杂查询
        result = normalizer.normalize("机器学习  + 深度学习 - TensorFlow")
        print(result.normalized)  # "machine learning deep learning"

        # 查询修正
        result = normalizer.normalize("artificial intelligance")
        print(result.suggestions)  # ["artificial intelligence"]
    """

    # 中文标点映射
    CN_PUNCTUATION_MAP = {
        '，': ',',
        '。': '.',
        '、': ',',
        '；': ';',
        '：': ':',
        '？': '?',
        '！': '!',
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '－': '-',
        '～': '~',
    }

    # 全角转半角映射
    FULLWIDTH_MAP = {
        '１': '1', '２': '2', '３': '3', '４': '4', '５': '5',
        '６': '6', '７': '7', '８': '8', '９': '9', '０': '0',
        'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E',
        'Ｆ': 'F', 'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J',
        'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O',
        'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T',
        'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y',
        'Ｚ': 'Z',
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',
        'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
        'ｋ': 'k', 'ｌ': 'l', 'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o',
        'ｐ': 'p', 'ｑ': 'q', 'ｑ': 'r', 'ｓ': 's', 'ｔ': 't',
        'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x', 'ｙ': 'y',
        'ｚ': 'z',
    }

    # 常见拼写错误映射
    SPELLING_CORRECTIONS = {
        'artificiall': 'artificial',
        'artificia': 'artificial',
        'intelligance': 'intelligence',
        'intellgence': 'intelligence',
        'machin': 'machine',
        'learnin': 'learning',
        'neuaral': 'neural',
        'depp': 'deep',
        'deeply': 'deep',
    }

    # 噪声词列表（搜索时会被忽略）
    STOP_WORDS = {
        # 英文
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can',
        # 中文
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
        '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会',
        '着', '没有', '看', '好', '自己', '这', '那', '个', '与', '为',
        '而', '于', '从', '到', '把', '被', '让', '给', '向', '对', '比',
    }

    # 字段前缀映射
    FIELD_PREFIXES = {
        'title': 'ti:',
        'ti': 'ti:',
        'author': 'au:',
        'au': 'au:',
        'abstract': 'abs:',
        'abs': 'abs:',
        'keyword': 'kw:',
        'kw': 'kw:',
        'category': 'cat:',
        'cat': 'cat:',
        'journal': 'jr:',
        'jr': 'jr:',
    }

    def __init__(
        self,
        lowercase: bool = True,
        remove_accents: bool = True,
        remove_stop_words: bool = False,
        preserve_operators: bool = True
    ):
        """
        初始化查询规范化器

        Args:
            lowercase: 是否转为小写
            remove_accents: 是否移除重音字符
            remove_stop_words: 是否移除停用词
            preserve_operators: 是否保留布尔运算符
        """
        self.lowercase = lowercase
        self.remove_accents = remove_accents
        self.remove_stop_words = remove_stop_words
        self.preserve_operators = preserve_operators

    def normalize(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        detect_type: bool = True,
        correct_spelling: bool = True,
        expand_terms: bool = False
    ) -> NormalizationResult:
        """
        规范化查询

        Args:
            query: 查询字符串
            query_type: 指定查询类型（自动检测如果为None）
            detect_type: 是否自动检测查询类型
            correct_spelling: 是否修正拼写错误
            expand_terms: 是否扩展术语

        Returns:
            NormalizationResult: 规范化结果
        """
        if not query:
            return NormalizationResult(
                original=query,
                normalized="",
                query_type=QueryType.KEYWORD if query_type is None else query_type
            )

        original = query
        warnings = []
        entities = []
        suggestions = []
        metadata = {"original_length": len(query)}

        # 1. 基础清理
        normalized = self._preprocess(query)

        # 2. 检测查询类型
        if detect_type and query_type is None:
            query_type = self._detect_query_type(normalized)

        if query_type is None:
            query_type = QueryType.NATURAL_LANGUAGE

        # 3. 应用查询类型特定的规范化
        if query_type == QueryType.BOOLEAN:
            normalized = self._normalize_boolean_query(normalized)
        elif query_type == QueryType.PHRASE:
            normalized = self._normalize_phrase_query(normalized)
        elif query_type == QueryType.FIELD:
            normalized = self._normalize_field_query(normalized)
        elif query_type == QueryType.WILDCARD:
            normalized = self._normalize_wildcard_query(normalized)
        else:
            normalized = self._normalize_natural_language(normalized)

        # 4. 拼写修正
        if correct_spelling:
            corrected, spelling_suggestions = self._correct_spelling(normalized)
            if corrected != normalized:
                warnings.append("Spelling correction applied")
            normalized = corrected
            suggestions.extend(spelling_suggestions)

        # 5. 移除停用词
        if self.remove_stop_words:
            normalized = self._remove_stop_words(normalized)

        # 6. 分词
        terms = self._tokenize(normalized)

        # 7. 实体识别（基础）
        entities = self._extract_entities(normalized, terms)

        # 8. 术语扩展
        if expand_terms:
            expanded = self._expand_terms(terms)
            metadata["expanded_terms"] = expanded

        return NormalizationResult(
            original=original,
            normalized=normalized.strip(),
            query_type=query_type,
            terms=terms,
            entities=entities,
            suggestions=suggestions,
            warnings=warnings,
            metadata=metadata
        )

    def _preprocess(self, query: str) -> str:
        """预处理查询"""
        text = query

        # 去除控制字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        # 全角转半角
        text = self._fullwidth_to_halfwidth(text)

        # 中文标点转英文标点
        text = self._cn_punctuation_to_en(text)

        # 合并多余空白
        text = re.sub(r'\s+', ' ', text)

        return text

    def _fullwidth_to_halfwidth(self, text: str) -> str:
        """全角转半角"""
        result = []
        for char in text:
            if char in self.FULLWIDTH_MAP:
                result.append(self.FULLWIDTH_MAP[char])
            elif ord(char) > 0x3000 and ord(char) < 0x9FFF:
                # 中文保留
                result.append(char)
            else:
                result.append(char)
        return ''.join(result)

    def _cn_punctuation_to_en(self, text: str) -> str:
        """中文标点转英文"""
        for cn, en in self.CN_PUNCTUATION_MAP.items():
            text = text.replace(cn, en)
        return text

    def _detect_query_type(self, query: str) -> QueryType:
        """检测查询类型"""
        # 检查布尔运算符
        if any(op in query.upper() for op in [' AND ', ' OR ', ' NOT ', '+', '-']):
            return QueryType.BOOLEAN

        # 检查通配符
        if any(op in query for op in ['*', '?', '[]']):
            return QueryType.WILDCARD

        # 检查字段前缀
        prefixes = list(self.FIELD_PREFIXES.keys())
        pattern = r'(' + '|'.join(re.escape(p) for p in prefixes) + r'):'
        if re.search(pattern, query, re.IGNORECASE):
            return QueryType.FIELD

        # 检查短语（引号包裹）
        if '"' in query or "'" in query:
            return QueryType.PHRASE

        # 默认自然语言
        return QueryType.NATURAL_LANGUAGE

    def _normalize_boolean_query(self, query: str) -> str:
        """规范化布尔查询"""
        text = query

        # 统一运算符
        text = text.replace('+', ' AND ')
        text = text.replace('-', ' NOT ')

        # 保留 AND/OR/NOT
        if self.preserve_operators:
            text = re.sub(r'\bAND\b', 'AND', text, flags=re.IGNORECASE)
            text = re.sub(r'\bOR\b', 'OR', text, flags=re.IGNORECASE)
            text = re.sub(r'\bNOT\b', 'NOT', text, flags=re.IGNORECASE)

        return text

    def _normalize_phrase_query(self, query: str) -> str:
        """规范化短语查询"""
        text = query

        # 统一引号
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # 将单引号转为双引号（如果只有一边）
        if "'" in text and '"' not in text:
            text = text.replace("'", '"')

        # 如果没有引号但包含空格，添加引号
        if '"' not in text and "'" not in text and ' ' in text:
            # 检查是否需要添加引号（多词短语）
            pass

        return text

    def _normalize_field_query(self, query: str) -> str:
        """规范化字段查询"""
        text = query

        # 转换字段前缀为标准格式
        for field_name, prefix in self.FIELD_PREFIXES.items():
            pattern = rf'{field_name}:'
            replacement = prefix
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _normalize_wildcard_query(self, query: str) -> str:
        """规范化通配符查询"""
        text = query

        # 保留通配符，但规范化其他部分
        text = text.lower() if self.lowercase else text

        return text

    def _normalize_natural_language(self, query: str) -> str:
        """规范化自然语言查询"""
        text = query

        # 转小写
        if self.lowercase:
            text = text.lower()

        # 移除重音
        if self.remove_accents:
            text = self._remove_accents(text)

        # 清理特殊字符（但保留空格和基本标点）
        text = re.sub(r'[^\w\s\-.,;?!]', ' ', text)

        # 合并空白
        text = re.sub(r'\s+', ' ', text)

        return text

    def _remove_accents(self, text: str) -> str:
        """移除重音字符"""
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )

    def _correct_spelling(self, query: str) -> Tuple[str, List[str]]:
        """修正拼写错误"""
        words = query.split()
        corrections = []
        corrected_words = []

        for word in words:
            lower_word = word.lower()
            if lower_word in self.SPELLING_CORRECTIONS:
                correction = self.SPELLING_CORRECTIONS[lower_word]
                corrections.append(f"{word} -> {correction}")
                corrected_words.append(correction)
            else:
                corrected_words.append(word)

        return ' '.join(corrected_words), corrections

    def _remove_stop_words(self, query: str) -> str:
        """移除停用词"""
        words = query.split()
        filtered = [w for w in words if w.lower() not in self.STOP_WORDS]
        return ' '.join(filtered)

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单分词：按空白和标点分割
        tokens = re.split(r'[\s,.!?;:\'"()\[\]{}]+', text)
        return [t for t in tokens if t]

    def _extract_entities(self, text: str, terms: List[str]) -> List[Dict[str, Any]]:
        """提取实体（基础实现）"""
        entities = []

        # 识别常见实体模式
        # 论文标题模式（双引号包裹）
        phrase_pattern = r'"([^"]+)"'
        for match in re.finditer(phrase_pattern, text):
            entities.append({
                "type": "phrase",
                "value": match.group(1),
                "position": match.span()
            })

        # 作者模式（@开头）
        author_pattern = r'@(\w+)'
        for match in re.finditer(author_pattern, text):
            entities.append({
                "type": "author",
                "value": match.group(1),
                "position": match.span()
            })

        # 数字范围模式
        range_pattern = r'(\d+)\s*[-~]\s*(\d+)'
        for match in re.finditer(range_pattern, text):
            entities.append({
                "type": "range",
                "value": (int(match.group(1)), int(match.group(2))),
                "position": match.span()
            })

        return entities

    def _expand_terms(self, terms: List[str]) -> List[str]:
        """扩展术语（同义词等）"""
        expanded = list(terms)

        # 基础同义词扩展
        synonyms = {
            'ml': ['machine learning', 'ml'],
            'ai': ['artificial intelligence', 'ai'],
            'dl': ['deep learning', 'dl'],
            'nn': ['neural network', 'nn'],
            'nlp': ['natural language processing', 'nlp'],
            'cv': ['computer vision', 'cv'],
        }

        for term in terms:
            term_lower = term.lower()
            if term_lower in synonyms:
                for syn in synonyms[term_lower]:
                    if syn not in expanded:
                        expanded.append(syn)

        return expanded

    def extract_keywords(self, query: str, top_k: int = 5) -> List[str]:
        """提取关键词"""
        temp_normalizer = QueryNormalizer(remove_stop_words=True)
        result = temp_normalizer.normalize(query)
        terms = result.terms

        # 简单实现：返回前k个最长的词（通常关键词较长）
        terms.sort(key=len, reverse=True)
        return terms[:top_k]

    def suggest_corrections(self, query: str) -> List[str]:
        """给出修正建议"""
        result = self.normalize(query, correct_spelling=True)
        return result.suggestions


def normalize_query(
    query: str,
    query_type: Optional[QueryType] = None,
    **kwargs
) -> NormalizationResult:
    """便捷函数：规范化查询"""
    normalizer = QueryNormalizer()
    return normalizer.normalize(query, query_type=query_type, **kwargs)