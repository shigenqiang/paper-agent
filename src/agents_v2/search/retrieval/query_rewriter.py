"""
Query Rewriter - 查询改写器

根据检索反馈改写查询以提升检索效果。
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


@dataclass
class RewriteResult:
    """改写结果"""
    original_query: str
    rewritten_query: str
    rewrite_type: str  # "expansion", "restriction", "reformulation", "decomposition"
    confidence: float
    reasons: List[str]


class QueryRewriter:
    """查询改写器

    根据不同场景改写查询：
    - expansion: 扩展查询以包含更多同义词
    - restriction: 限制查询范围
    - reformulation: 重新表述查询
    - decomposition: 将复杂查询分解为多个子查询
    """

    # 同义词映射（扩展英文支持）
    SYNONYMS = {
        # 原文已有
        "AI": ["Artificial Intelligence", "人工智能"],
        "ML": ["Machine Learning", "机器学习"],
        "DL": ["Deep Learning", "深度学习"],
        "NLP": ["Natural Language Processing", "自然语言处理"],
        "CV": ["Computer Vision", "计算机视觉"],
        "paper": ["article", "论文", "文章"],
        "research": ["研究", "学术"],
        "recent": ["latest", "new", "最新", "最近"],
        # 新增英文同义词
        "neural": ["neural network", "深度学习", "deep learning"],
        "network": ["neural network", "神经网络"],
        "learning": ["machine learning", "deep learning", "机器学习", "深度学习"],
        "transformer": ["attention", "self-attention", "注意力机制"],
        "attention": ["transformer", "self-attention", "注意力"],
        "bert": ["bidirectional", "pre-training", "预训练", "双向编码器"],
        "gpt": ["generative", "pre-trained", "生成式", "预训练"],
        "language": ["NLP", "自然语言", "文本"],
        "model": ["models", "模型", "神经网络"],
        "vision": ["computer vision", "图像", "CV"],
        "image": ["vision", "图像处理", "computer vision"],
        "reinforcement": ["reinforcement learning", "强化学习"],
        "supervised": ["supervised learning", "监督学习"],
        "unsupervised": ["unsupervised learning", "无监督学习"],
        "gan": ["generative adversarial", "生成对抗网络"],
        "vae": ["variational autoencoder", "变分自编码器"],
        "mcmc": ["markov chain monte carlo", "蒙特卡洛", "贝叶斯"],
        "bayesian": ["bayes", "贝叶斯", "概率图模型"],
        "regression": ["回归", "统计模型"],
        "classification": ["分类", "机器学习"],
        "clustering": ["聚类", "无监督学习"],
        "embedding": ["vector", "向量表示", "嵌入"],
        "semantic": ["语义", "meaning", "知识"],
        "retrieval": ["搜索", "retrieval augmented"],
        "rag": ["retrieval augmented generation", "检索增强生成"],
        "llm": ["large language model", "大语言模型", "语言模型"],
        "foundation": ["foundation model", "基础模型"],
    }

    # 技术术语分解映射
    TECH_TERM_DECOMPOSITIONS = {
        "GPT-3": ["GPT3 large language model generative pre-trained transformer"],
        "GPT-4": ["GPT4 large language model generative pre-trained multimodal"],
        "BERT": ["BERT bidirectional encoder representations transformer pre-training"],
        "Transformer": ["Transformer attention mechanism self-attention neural network"],
        "LSTM": ["LSTM long short-term memory recurrent neural network RNN"],
        "RNN": ["RNN recurrent neural network sequential data"],
        "CNN": ["CNN convolutional neural network computer vision image"],
        "GAN": ["GAN generative adversarial network deep learning"],
        "VAE": ["VAE variational autoencoder generative model"],
        "MCMC": ["MCMC markov chain monte carlo bayesian inference sampling"],
        "RL": ["RL reinforcement learning agent environment policy"],
        "NLP": ["NLP natural language processing text understanding generation"],
        "CV": ["CV computer vision image video visual"],
        "ML": ["ML machine learning algorithm prediction"],
        "DL": ["DL deep learning neural network representation"],
        "ANN": ["ANN artificial neural network deep learning"],
        "AI": ["AI artificial intelligence machine intelligence"],
        "LLM": ["LLM large language model text generation"],
        "RAG": ["RAG retrieval augmented generation information retrieval text generation"],
        "Self-RAG": ["Self-RAG self-retrieval augmented generation reasoning"],
        "LoRA": ["LoRA low-rank adaptation fine-tuning language model"],
        "Prompt": ["Prompt prompt engineering instruction text input"],
        "Embedding": ["Embedding vector representation text image semantic"],
        "Fine-tuning": ["Fine-tuning transfer learning domain adaptation"],
    }

    def __init__(self, llm: Any = None):
        """初始化查询改写器

        Args:
            llm: 可选的LLM实例用于智能改写
        """
        self.llm = llm

    def rewrite(
        self,
        query: str,
        rewrite_type: str = "auto",
        context: Optional[Dict[str, Any]] = None
    ) -> RewriteResult:
        """改写查询

        Args:
            query: 原始查询
            rewrite_type: 改写类型 ("auto", "expansion", "restriction", "reformulation", "decomposition")
            context: 上下文信息（包含不相关文档等）

        Returns:
            RewriteResult: 改写结果
        """
        context = context or {}

        if rewrite_type == "auto":
            rewrite_type = self._decide_rewrite_type(query, context)

        if rewrite_type == "expansion":
            return self._expand_query(query)
        elif rewrite_type == "restriction":
            return self._restrict_query(query, context)
        elif rewrite_type == "reformulation":
            return self._reformulate_query(query)
        elif rewrite_type == "decomposition":
            return self._decompose_query(query)
        else:
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                rewrite_type="none",
                confidence=1.0,
                reasons=["No rewrite needed"]
            )

    def _decide_rewrite_type(self, query: str, context: Dict[str, Any]) -> str:
        """决定改写类型

        Args:
            query: 查询
            context: 上下文

        Returns:
            str: 改写类型
        """
        query_lower = query.lower()

        # 检查是否包含否定词（限制范围）
        if any(w in query_lower for w in ["不是", "不含", "without", "excluding"]):
            return "reformulation"

        # 检查是否是复杂查询（多词或有明确分隔符）
        if len(query.split()) > 10 or "和" in query or " and " in query_lower:
            return "decomposition"

        # 检查是否有不相关文档（需要扩展）
        irrelevant_docs = context.get("irrelevant_docs", [])
        if len(irrelevant_docs) > 2:
            return "expansion"

        # 短查询需要扩展
        if len(query) < 10:
            return "expansion"

        # 检测是否包含技术术语（需要分解）
        if self._contains_tech_term(query):
            return "decomposition"

        # 默认启用扩展（提升检索召回率）
        return "expansion"

    def _contains_tech_term(self, query: str) -> bool:
        """检查查询是否包含技术术语"""
        query_upper = query.upper()
        for term in self.TECH_TERM_DECOMPOSITIONS.keys():
            if term.upper() in query_upper or term.lower() in query.lower():
                return True
        return False

    def _decompose_tech_term(self, query: str) -> List[str]:
        """分解技术术语为展开的关键词列表"""
        decompositions = []
        remaining = query

        # 按技术术语替换
        for term, expansion in self.TECH_TERM_DECOMPOSITIONS.items():
            if term.upper() in query.upper():
                decompositions.append(expansion)
                remaining = remaining.replace(term, "")
                remaining = remaining.replace(term.lower(), "")
                remaining = remaining.replace(term.upper(), "")

        # 清理并返回
        result = []
        for d in decompositions:
            result.extend(d.split())

        if remaining.strip():
            result.extend(remaining.strip().split())

        return result

    def _expand_query(self, query: str) -> RewriteResult:
        """扩展查询 - 包含同义词扩展和技术术语分解

        Args:
            query: 原始查询

        Returns:
            RewriteResult: 改写结果
        """
        expanded_terms = []
        reasons = []

        # 1. 先处理技术术语分解
        if self._contains_tech_term(query):
            tech_terms = self._decompose_tech_term(query)
            expanded_terms.extend(tech_terms)
            reasons.append(f"技术术语分解: {query} → {tech_terms}")
            logger.debug(f"技术术语分解: {query} → {tech_terms}")

        # 2. 对非技术术语词进行同义词扩展
        words = query.split()
        for word in words:
            word_lower = word.lower()
            # 跳过已经是技术术语的部分
            is_tech = False
            for term in self.TECH_TERM_DECOMPOSITIONS.keys():
                if term.lower() == word_lower:
                    is_tech = True
                    break
            if is_tech:
                continue

            if word_lower in self.SYNONYMS:
                synonyms = self.SYNONYMS[word_lower]
                expanded_terms.extend(synonyms)
                reasons.append(f"添加同义词: {word} → {synonyms}")
            else:
                expanded_terms.append(word)

        # 3. 如果没有任何扩展，添加通用学术扩展词
        if len(expanded_terms) == len(words) and not self._contains_tech_term(query):
            expanded_terms.append("research")
            expanded_terms.append("paper")
            expanded_terms.append("academic")
            reasons.append("添加通用学术扩展词")

        rewritten = " ".join(expanded_terms)

        logger.debug(f"查询扩展: '{query}' → '{rewritten}'")
        return RewriteResult(
            original_query=query,
            rewritten_query=rewritten,
            rewrite_type="expansion",
            confidence=0.8,
            reasons=reasons
        )

    def _restrict_query(self, query: str, context: Dict[str, Any]) -> RewriteResult:
        """限制查询范围

        Args:
            query: 原始查询
            context: 上下文信息

        Returns:
            RewriteResult: 改写结果
        """
        reasons = []
        rewritten = query

        # 移除模糊词
        vague_words = ["一些", "某些", "some", "various"]
        for word in vague_words:
            if word in query:
                rewritten = rewritten.replace(word, "")
                reasons.append(f"移除模糊词: {word}")

        # 添加具体年份或时间限制
        if "recent" in query.lower() or "最新" in query:
            rewritten = f"{rewritten} 2024 2025"
            reasons.append("添加时间限制: 2024-2025")

        # 添加具体领域限制
        if context.get("target_domain"):
            domain = context["target_domain"]
            rewritten = f"{rewritten} {domain}"
            reasons.append(f"添加领域限制: {domain}")

        return RewriteResult(
            original_query=query,
            rewritten_query=rewritten.strip(),
            rewrite_type="restriction",
            confidence=0.7,
            reasons=reasons
        )

    def _reformulate_query(self, query: str) -> RewriteResult:
        """重新表述查询

        Args:
            query: 原始查询

        Returns:
            RewriteResult: 改写结果
        """
        reasons = []
        rewritten = query

        # 中英混合时统一语言
        has_chinese = any("一" <= c <= "鿿" for c in query)
        has_english = any(c.isalpha() for c in query) and not has_chinese

        if has_chinese and has_english:
            # 翻译关键术语
            translations = {
                "机器学习": "machine learning",
                "深度学习": "deep learning",
                "人工智能": "artificial intelligence",
                "神经网络": "neural network"
            }
            for cn, en in translations.items():
                if cn in query:
                    rewritten = rewritten.replace(cn, en)
                    reasons.append(f"翻译: {cn} → {en}")

        # 简化复杂句式
        complex_patterns = [
            ("我想了解", ""),
            ("请问", ""),
            ("能不能", ""),
            ("可以告诉我", "")
        ]
        for pattern, replacement in complex_patterns:
            if pattern in rewritten:
                rewritten = rewritten.replace(pattern, replacement)
                reasons.append(f"简化句式: 移除'{pattern}'")

        return RewriteResult(
            original_query=query,
            rewritten_query=rewritten.strip(),
            rewrite_type="reformulation",
            confidence=0.75,
            reasons=reasons
        )

    def _decompose_query(self, query: str) -> RewriteResult:
        """分解复杂查询

        Args:
            query: 原始查询

        Returns:
            RewriteResult: 改写结果（返回第一个子查询）
        """
        reasons = []
        sub_queries = []

        # 按逗号或"和"分割
        if "，" in query:
            parts = query.split("，")
        elif "," in query:
            parts = query.split(",")
        elif " 和 " in query:
            parts = query.split(" 和 ")
        elif " and " in query.lower():
            parts = query.split(" and ")
        else:
            # 无法分解，返回原查询
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                rewrite_type="decomposition",
                confidence=0.5,
                reasons=["无法分解，使用原查询"]
            )

        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                sub_queries.append(part)
                reasons.append(f"分解子查询{i+1}: {part}")

        # 返回第一个子查询
        first_sub = sub_queries[0] if sub_queries else query

        return RewriteResult(
            original_query=query,
            rewritten_query=first_sub,
            rewrite_type="decomposition",
            confidence=0.6,
            reasons=reasons
        )

    def get_all_sub_queries(self, query: str) -> List[str]:
        """获取所有子查询

        Args:
            query: 原始查询

        Returns:
            List[str]: 子查询列表
        """
        # 按逗号或"和"分割
        if "，" in query:
            parts = query.split("，")
        elif "," in query:
            parts = query.split(",")
        elif " 和 " in query:
            parts = query.split(" 和 ")
        elif " and " in query.lower():
            parts = query.split(" and ")
        else:
            return [query]

        return [p.strip() for p in parts if p.strip()]


# 便捷函数
def rewrite_query(
    query: str,
    rewrite_type: str = "auto",
    context: Optional[Dict[str, Any]] = None
) -> RewriteResult:
    """改写查询的便捷函数

    Args:
        query: 原始查询
        rewrite_type: 改写类型
        context: 上下文信息

    Returns:
        RewriteResult: 改写结果
    """
    rewriter = QueryRewriter()
    return rewriter.rewrite(query, rewrite_type, context)
