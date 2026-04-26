"""
Query Expander - 查询扩展器

生成查询的多个扩展版本以提高召回率。
"""
import logging
from typing import Any, Dict, List, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExpansionResult:
    """扩展结果"""
    original_query: str
    expanded_queries: List[str]
    expansion_types: List[str]  # "synonym", "broader", "narrower", "related"
    confidence: float


class QueryExpander:
    """查询扩展器

    通过多种策略扩展查询：
    - 同义词扩展
    - 上位词扩展
    - 下位词扩展
    - 相关词扩展
    """

    # 学术领域同义词库
    SYNONYMS = {
        # AI/ML
        "machine learning": ["ML", "machine learning methods", "learning algorithms"],
        "deep learning": ["DL", "deep neural networks", "deep learning methods"],
        "artificial intelligence": ["AI", "machine intelligence", "computational intelligence"],
        "neural network": ["neural nets", "artificial neural network", "ANN"],
        "transformer": ["attention mechanism", "self-attention", "transformer architecture"],
        "bert": ["bidirectional encoder", "BERT model", "language representation"],
        "gpt": ["generative pre-trained", "GPT model", "language model"],

        # 研究相关
        "research": ["study", "investigation", "survey", "研究"],
        "paper": ["article", "publication", "conference paper", "journal", "论文"],
        "method": ["approach", "technique", "algorithm", "方法"],
        "model": ["framework", "architecture", "system", "模型"],
        "performance": ["accuracy", "efficiency", "effectiveness", "效果"],
        "result": ["finding", "outcome", "conclusion", "结果"],

        # NLP
        "natural language processing": ["NLP", "computational linguistics", "language processing"],
        "text mining": ["text analytics", "text analysis", "文本挖掘"],
        "sentiment analysis": ["opinion mining", "sentiment detection", "情感分析"],
        "machine translation": ["MT", "neural translation", "机器翻译"],

        # CV
        "computer vision": ["CV", "visual recognition", "图像处理"],
        "image recognition": ["object recognition", "image classification", "图像识别"],
        "object detection": ["object localization", "detection", "目标检测"],
    }

    # 上位词（更广义的概念）
    BROADER_TERMS = {
        "machine learning": ["artificial intelligence", "computer science"],
        "deep learning": ["machine learning", "neural networks", "artificial intelligence"],
        "neural network": ["machine learning", "artificial intelligence"],
        "NLP": ["artificial intelligence", "computer science"],
        "computer vision": ["artificial intelligence", "computer science"],
        "transformer": ["deep learning", "neural network architecture"],
    }

    # 下位词（更具体的概念）
    NARROWER_TERMS = {
        "machine learning": ["supervised learning", "unsupervised learning", "reinforcement learning"],
        "deep learning": ["CNN", "RNN", "LSTM", "GAN"],
        "NLP": ["text classification", "named entity recognition", "machine translation"],
        "computer vision": ["image classification", "object detection", "semantic segmentation"],
        "transformer": ["BERT", "GPT", "T5", "ViT"],
    }

    # 相关词（经常一起出现的词）
    RELATED_TERMS = {
        "accuracy": ["precision", "recall", "F1", "performance metrics"],
        "neural network": ["training", "optimization", "gradient descent"],
        "research": ["experiment", "evaluation", "benchmark"],
        "paper": ["arxiv", "conference", "journal", "publication"],
        "model": ["training data", "test data", "validation"],
    }

    def __init__(self):
        """初始化查询扩展器"""
        self.expansion_cache: Dict[str, ExpansionResult] = {}

    def expand(self, query: str, strategies: List[str] = None) -> ExpansionResult:
        """扩展查询

        Args:
            query: 原始查询
            strategies: 扩展策略列表 (["synonym", "broader", "narrower", "related"])

        Returns:
            ExpansionResult: 扩展结果
        """
        if strategies is None:
            strategies = ["synonym", "broader", "narrower", "related"]

        # 检查缓存
        cache_key = f"{query}:{','.join(strategies)}"
        if cache_key in self.expansion_cache:
            return self.expansion_cache[cache_key]

        expanded = []
        types_used = []

        query_lower = query.lower()

        for strategy in strategies:
            if strategy == "synonym":
                synonyms = self._expand_synonym(query_lower)
                expanded.extend(synonyms)
                if synonyms:
                    types_used.append("synonym")

            elif strategy == "broader":
                broader = self._expand_broader(query_lower)
                expanded.extend(broader)
                if broader:
                    types_used.append("broader")

            elif strategy == "narrower":
                narrower = self._expand_narrower(query_lower)
                expanded.extend(narrower)
                if narrower:
                    types_used.append("narrower")

            elif strategy == "related":
                related = self._expand_related(query_lower)
                expanded.extend(related)
                if related:
                    types_used.append("related")

        # 去重但保持顺序
        seen: Set[str] = set()
        unique_expanded = []
        for q in expanded:
            q_lower = q.lower()
            if q_lower not in seen and q_lower != query_lower:
                seen.add(q_lower)
                unique_expanded.append(q)

        result = ExpansionResult(
            original_query=query,
            expanded_queries=unique_expanded[:10],  # 最多10个扩展
            expansion_types=types_used,
            confidence=min(1.0, len(types_used) * 0.25)
        )

        # 缓存结果
        self.expansion_cache[cache_key] = result

        return result

    def _expand_synonym(self, query: str) -> List[str]:
        """同义词扩展

        Args:
            query: 查询

        Returns:
            List[str]: 同义词列表
        """
        synonyms = []

        for term, syn_list in self.SYNONYMS.items():
            if term in query:
                synonyms.extend(syn_list)

        return synonyms

    def _expand_broader(self, query: str) -> List[str]:
        """上位词扩展

        Args:
            query: 查询

        Returns:
            List[str]: 上位词列表
        """
        broader = []

        for term, broader_list in self.BROADER_TERMS.items():
            if term in query:
                broader.extend(broader_list)

        return broader

    def _expand_narrower(self, query: str) -> List[str]:
        """下位词扩展

        Args:
            query: 查询

        Returns:
            List[str]: 下位词列表
        """
        narrower = []

        for term, narrower_list in self.NARROWER_TERMS.items():
            if term in query:
                narrower.extend(narrower_list)

        return narrower

    def _expand_related(self, query: str) -> List[str]:
        """相关词扩展

        Args:
            query: 查询

        Returns:
            List[str]: 相关词列表
        """
        related = []

        for term, related_list in self.RELATED_TERMS.items():
            if term in query:
                related.extend(related_list)

        return related

    def expand_with_combinations(self, query: str) -> List[str]:
        """生成组合扩展查询

        Args:
            query: 原始查询

        Returns:
            List[str]: 组合后的查询列表
        """
        result = self.expand(query)
        queries = [query]  # 包含原查询

        # 添加单个扩展
        queries.extend(result.expanded_queries)

        # 添加组合扩展（前两个扩展词的组合）
        expanded = result.expanded_queries
        for i in range(len(expanded)):
            for j in range(i + 1, len(expanded)):
                combined = f"{expanded[i]} {expanded[j]}"
                if combined.lower() != query.lower():
                    queries.append(combined)

        # 去重
        seen: Set[str] = set()
        unique_queries = []
        for q in queries:
            q_lower = q.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                unique_queries.append(q)

        return unique_queries[:20]  # 最多20个查询


# 便捷函数
def expand_query(query: str, strategies: List[str] = None) -> ExpansionResult:
    """扩展查询的便捷函数

    Args:
        query: 原始查询
        strategies: 扩展策略

    Returns:
        ExpansionResult: 扩展结果
    """
    expander = QueryExpander()
    return expander.expand(query, strategies)


def get_expanded_queries(query: str) -> List[str]:
    """获取扩展后的查询列表

    Args:
        query: 原始查询

    Returns:
        List[str]: 扩展后的查询列表
    """
    expander = QueryExpander()
    return expander.expand_with_combinations(query)
