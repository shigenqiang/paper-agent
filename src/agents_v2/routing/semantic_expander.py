"""
Semantic Keyword Expander - 语义关键词扩展器

扩展用户输入的关键词为同义词、上下位词、相关词，提高检索召回率。
"""
from typing import Any, Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class ExpansionResult:
    """扩展结果"""
    original: str
    expanded: List[str] = field(default_factory=list)
    categories: Dict[str, List[str]] = field(default_factory=dict)
    confidence: float = 1.0

    @property
    def all_terms(self) -> List[str]:
        """获取所有扩展后的术语"""
        return self.expanded

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "expanded": self.expanded,
            "categories": self.categories,
            "confidence": self.confidence
        }


class SemanticKeywordExpander:
    """
    语义关键词扩展器

    扩展策略:
    1. 同义词扩展 (深度学习 -> 机器学习、神经网络)
    2. 上下位词 (ML -> 机器学习、Machine Learning)
    3. 常见变体 (论文 -> 文章、学术论文)
    4. 英文缩写 (NLP -> Natural Language Processing)

    使用示例:
        expander = SemanticKeywordExpander()

        result = expander.expand("深度学习")
        print(result.expanded)  # ['深度学习', '机器学习', '神经网络', 'deep learning', 'DL'...]
    """

    # 同义词映射
    SYNONYMS = {
        "论文": ["文章", "学术论文", "研究论文", "paper", "research paper"],
        "搜索": ["查找", "检索", "寻找", "search", "find", "query"],
        "文献": ["论文", "参考", "参考资料", "literature", "references", "academic papers"],
        "选题": ["主题", "研究方向", "课题", "topic", "research topic", "subject"],
        "润色": ["修改", "完善", "优化", "polish", "refine", "improve"],
        "综述": ["总结", "概述", "survey", "review", "overview"],
        "大纲": ["提纲", "结构", "框架", "outline", "structure", "framework"],
        "初稿": ["草稿", "草案", "draft", "first version", "preliminary"],
        "诊断": ["分析", "检查", "评估", "diagnostic", "analysis", "check"],
        "追踪": ["跟踪", "监测", "track", "monitor", "follow"],
        "对比": ["比较", "对照", "compare", "comparison", "contrast"],
        "总结": ["概括", "归纳", "summary", "summarize", "conclude"],
    }

    # 上下位词映射（上位词 -> 下位词）
    HYPER_HYPONYMS = {
        "AI": ["人工智能", "Artificial Intelligence", "machine intelligence"],
        "ML": ["机器学习", "Machine Learning", "machine learning algorithms"],
        "DL": ["深度学习", "Deep Learning", "deep neural networks"],
        "NLP": ["自然语言处理", "Natural Language Processing", "computational linguistics"],
        "CV": ["计算机视觉", "Computer Vision", "visual recognition"],
        "AI": ["人工智能", "Artificial Intelligence"],
        "机器学习": ["监督学习", "无监督学习", "强化学习", "supervised learning", "unsupervised learning", "reinforcement learning"],
        "深度学习": ["卷积神经网络", "循环神经网络", "Transformer", "CNN", "RNN", "attention mechanism"],
        "神经网络": ["前馈神经网络", "卷积神经网络", "循环神经网络", "feedforward", "CNN", "RNN", "LSTM"],
    }

    # 缩写映射
    ABBREVIATIONS = {
        "NLP": ["Natural Language Processing", "自然语言处理"],
        "CV": ["Computer Vision", "计算机视觉"],
        "ML": ["Machine Learning", "机器学习"],
        "DL": ["Deep Learning", "深度学习"],
        "AI": ["Artificial Intelligence", "人工智能"],
        "LLM": ["Large Language Model", "大型语言模型"],
        "RAG": ["Retrieval Augmented Generation", "检索增强生成"],
        "BERT": ["Bidirectional Encoder Representations", "双向编码器表示"],
        "GPT": ["Generative Pre-trained Transformer", "生成预训练变换器"],
        "CNN": ["Convolutional Neural Network", "卷积神经网络"],
        "RNN": ["Recurrent Neural Network", "循环神经网络"],
        "LSTM": ["Long Short-Term Memory", "长短期记忆网络"],
    }

    # 常见变体模式
    VARIANT_PATTERNS = [
        (r"论文$", lambda w: w.replace("论文", "文章")),
        (r"研究$", lambda w: w.replace("研究", "分析")),
        (r"学习$", lambda w: [w + "方法", w + "算法"]),
        (r"网络$", lambda w: [w + "结构", w + "架构"]),
    ]

    def __init__(
        self,
        include_english: bool = True,
        include_abbreviations: bool = True,
        include_variants: bool = True
    ):
        """
        初始化扩展器

        Args:
            include_english: 是否包含英文扩展
            include_abbreviations: 是否包含缩写扩展
            include_variants: 是否包含变体扩展
        """
        self.include_english = include_english
        self.include_abbreviations = include_abbreviations
        self.include_variants = include_variants

    def expand(self, keyword: str) -> ExpansionResult:
        """
        扩展关键词

        Args:
            keyword: 要扩展的关键词

        Returns:
            ExpansionResult: 扩展结果
        """
        if not keyword or not keyword.strip():
            return ExpansionResult(original=keyword, expanded=[], confidence=1.0)

        expanded: List[str] = [keyword]
        categories: Dict[str, List[str]] = {
            "synonyms": [],
            "hyponyms": [],
            "abbreviations": [],
            "variants": [],
            "english": []
        }

        # 同义词扩展
        synonyms = self._expand_synonyms(keyword)
        if synonyms:
            categories["synonyms"] = synonyms
            expanded.extend(synonyms)

        # 上下位词扩展
        hyponyms = self._expand_hyponyms(keyword)
        if hyponyms:
            categories["hyponyms"] = hyponyms
            expanded.extend(hyponyms)

        # 缩写扩展
        if self.include_abbreviations:
            abbrevs = self._expand_abbreviations(keyword)
            if abbrevs:
                categories["abbreviations"] = abbrevs
                expanded.extend(abbrevs)

        # 变体扩展
        if self.include_variants:
            variants = self._expand_variants(keyword)
            if variants:
                categories["variants"] = variants
                expanded.extend(variants)

        # 英文扩展
        if self.include_english:
            english = self._expand_english(keyword)
            if english:
                categories["english"] = english
                expanded.extend(english)

        # 去重保持顺序
        unique_expanded = list(dict.fromkeys(expanded))

        return ExpansionResult(
            original=keyword,
            expanded=unique_expanded,
            categories=categories,
            confidence=min(1.0, len(unique_expanded) / 10)  # 简单置信度
        )

    def expand_query(self, query: str) -> List[str]:
        """
        扩展完整查询（分词后）

        Args:
            query: 查询字符串

        Returns:
            List[str]: 扩展后的术语列表
        """
        # 简单分词
        words = self._tokenize(query)
        expanded_terms: List[str] = []

        for word in words:
            if len(word) >= 2:  # 忽略单字
                result = self.expand(word)
                expanded_terms.extend(result.all_terms)

        # 去重
        return list(dict.fromkeys(expanded_terms))

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        # 按中英文和特殊字符分割
        tokens = re.split(r'[\s,，;；\.。\-_+()（）]+', text)
        return [t.strip() for t in tokens if t.strip()]

    def _expand_synonyms(self, keyword: str) -> List[str]:
        """扩展同义词"""
        synonyms = []

        # 精确匹配
        if keyword in self.SYNONYMS:
            synonyms.extend(self.SYNONYMS[keyword])

        # 部分匹配
        for key, values in self.SYNONYMS.items():
            if keyword in values:
                synonyms.append(key)
                synonyms.extend([v for v in values if v != keyword])

        # 反向检查（关键词可能在值中）
        for key, values in self.SYNONYMS.items():
            for v in values:
                if keyword.lower() == v.lower():
                    synonyms.append(key)
                    break

        return list(dict.fromkeys(synonyms))

    def _expand_hyponyms(self, keyword: str) -> List[str]:
        """扩展上下位词"""
        hyponyms = []
        keyword_lower = keyword.lower()

        # 检查是否是上位词
        if keyword_lower in self.HYPER_HYPONYMS:
            hyponyms.extend(self.HYPER_HYPONYMS[keyword_lower])

        # 检查是否是下位词
        for hyper, hypos in self.HYPER_HYPONYMS.items():
            if keyword_lower in [h.lower() for h in hypos]:
                hyponyms.append(hyper)
                hyponyms.extend([h for h in hypos if h.lower() != keyword_lower])

        return list(dict.fromkeys(hyponyms))

    def _expand_abbreviations(self, keyword: str) -> List[str]:
        """扩展缩写"""
        abbrevs = []
        keyword_upper = keyword.upper()
        keyword_lower = keyword.lower()

        # 精确匹配缩写
        if keyword_upper in self.ABBREVIATIONS:
            abbrevs.extend(self.ABBREVIATIONS[keyword_upper])

        # 检查关键词是否是全称
        for abbr, full_names in self.ABBREVIATIONS.items():
            if keyword_lower in [fn.lower() for fn in full_names]:
                abbrevs.append(abbr)
                abbrevs.extend([fn for fn in full_names if fn.lower() != keyword_lower])

        return list(dict.fromkeys(abbrevs))

    def _expand_variants(self, keyword: str) -> List[str]:
        """扩展变体"""
        variants = []

        for pattern, transformer in self.VARIANT_PATTERNS:
            if re.search(pattern, keyword):
                try:
                    result = transformer(keyword)
                    if isinstance(result, list):
                        variants.extend(result)
                    else:
                        variants.append(result)
                except Exception:
                    pass

        return variants

    def _expand_english(self, keyword: str) -> List[str]:
        """扩展英文"""
        english = []

        # 中英文互转
        chinese_to_english = {
            "机器学习": ["machine learning", "ML"],
            "深度学习": ["deep learning", "DL"],
            "神经网络": ["neural network", "NN"],
            "自然语言处理": ["NLP", "natural language processing"],
            "计算机视觉": ["CV", "computer vision"],
            "人工智能": ["AI", "artificial intelligence"],
            "论文": ["paper", "research paper"],
            "搜索": ["search", "query"],
            "文献": ["literature", "references"],
            "大纲": ["outline", "structure"],
        }

        keyword_lower = keyword.lower()
        if keyword_lower in chinese_to_english:
            english.extend(chinese_to_english[keyword_lower])

        return english

    def add_synonym(self, word: str, synonyms: List[str]):
        """添加同义词"""
        if word not in self.SYNONYMS:
            self.SYNONYMS[word] = []
        self.SYNONYMS[word].extend(synonyms)

    def add_hyper_hyponym(self, hyper: str, hypos: List[str]):
        """添加上下位词关系"""
        if hyper not in self.HYPER_HYPONYMS:
            self.HYPER_HYPONYMS[hyper] = []
        self.HYPER_HYPONYMS[hyper].extend(hypos)

    def add_abbreviation(self, abbr: str, full_names: List[str]):
        """添加缩写映射"""
        self.ABBREVIATIONS[abbr.upper()] = full_names


def expand_keywords(keyword: str) -> ExpansionResult:
    """便捷函数：扩展关键词"""
    expander = SemanticKeywordExpander()
    return expander.expand(keyword)


def expand_query(keyword: str) -> List[str]:
    """便捷函数：扩展查询"""
    expander = SemanticKeywordExpander()
    return expander.expand_query(keyword)