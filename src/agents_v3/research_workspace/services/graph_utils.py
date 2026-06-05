"""知识图谱工具函数和常量"""

from __future__ import annotations

import re

from loguru import logger

from src.agents_v3.research_workspace.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
)


def _levenshtein(s1: str, s2: str) -> int:
    """计算编辑距离"""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """计算余弦相似度"""
    import math
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


# 同义词/缩写映射
_ALIASES: dict[str, str] = {
    # ── LLM / NLP ──
    "llms": "llm",
    "large language model": "llm",
    "large language models": "llm",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
    "rag-based approach": "rag",
    "rag-based approaches": "rag",
    "gpt-3": "gpt",
    "gpt-4": "gpt",
    "gpt-3.5": "gpt",
    "gpt3": "gpt",
    "gpt4": "gpt",
    "chatgpt": "gpt",
    "bert": "bert",
    "bert-base": "bert",
    "roberta": "roberta",
    "xlnet": "xlnet",
    "t5": "t5",
    "transformer": "transformer",
    "transformers": "transformer",
    "attention mechanism": "attention",
    "self-attention": "attention",
    "multi-head attention": "attention",
    "word embedding": "word embedding",
    "word embeddings": "word embedding",
    "word2vec": "word embedding",
    "glove": "word embedding",
    "fasttext": "word embedding",
    "named entity recognition": "ner",
    "ner": "ner",
    "machine translation": "machine translation",
    "mt": "machine translation",
    "natural language inference": "nli",
    "nli": "nli",
    "text classification": "text classification",
    "sentiment analysis": "sentiment analysis",
    "question answering": "question answering",
    "qa": "question answering",
    "summarization": "summarization",
    "text summarization": "summarization",
    "information retrieval": "information retrieval",
    "ir": "information retrieval",
    "knowledge graph": "knowledge graph",
    "knowledge graphs": "knowledge graph",
    "kg": "knowledge graph",
    # ── 机器学习 ──
    "convolutional neural network": "cnn",
    "cnns": "cnn",
    "recurrent neural network": "rnn",
    "rnns": "rnn",
    "long short-term memory": "lstm",
    "lstm": "lstm",
    "generative adversarial network": "gan",
    "gans": "gan",
    "variational autoencoder": "vae",
    "vaes": "vae",
    "graph neural network": "gnn",
    "gnns": "gnn",
    "reinforcement learning": "reinforcement learning",
    "rl": "reinforcement learning",
    "deep learning": "deep learning",
    "dl": "deep learning",
    "transfer learning": "transfer learning",
    "few-shot learning": "few-shot learning",
    "zero-shot learning": "zero-shot learning",
    "contrastive learning": "contrastive learning",
    "self-supervised learning": "self-supervised learning",
    "semi-supervised learning": "semi-supervised learning",
    "active learning": "active learning",
    "meta-learning": "meta-learning",
    "federated learning": "federated learning",
    # ── 评估指标 ──
    "bleu score": "bleu",
    "bleu": "bleu",
    "rouge score": "rouge",
    "rouge": "rouge",
    "f1 score": "f1",
    "f1-score": "f1",
    "accuracy": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "auc": "auc",
    "auc-roc": "auc",
    "mean average precision": "map",
    "map": "map",
    "mean squared error": "mse",
    "mse": "mse",
    "root mean squared error": "rmse",
    "rmse": "rmse",
    # ── 研究方法 ──
    "randomized controlled trial": "rct",
    "randomised controlled trial": "rct",
    "quasi-experiment": "quasi-experimental",
    "quasi experiment": "quasi-experimental",
    "systematic review": "systematic review",
    "meta-analysis": "meta-analysis",
    "meta analysis": "meta-analysis",
    "ablation study": "ablation study",
    "ablation studies": "ablation study",
    "case study": "case study",
    "case studies": "case study",
    "cross-validation": "cross-validation",
    "cross validation": "cross-validation",
    "k-fold cross-validation": "cross-validation",
    "statistical significance": "statistical significance",
    "p-value": "statistical significance",
    "p value": "statistical significance",
    # ── 数据集 ──
    "imagenet": "imagenet",
    "coco": "coco",
    "mnist": "mnist",
    "cifar-10": "cifar",
    "cifar10": "cifar",
    "squad": "squad",
    "glue": "glue",
    "superglue": "superglue",
    "common crawl": "common crawl",
    "wikipedia": "wikipedia",
}


def resolve_alias(normalized: str) -> str:
    """检查同义词映射"""
    return _ALIASES.get(normalized, normalized)


# ── Gap 检测 ──────────────────────────────────────

# Limitation 类型关键词
_LIMITATION_TYPE_KEYWORDS: dict[str, list[str]] = {
    "sample_size": ["sample size", "small sample", "样本量", "样本不足"],
    "single_dataset": ["single dataset", "one dataset", "单数据集", "数据集单一"],
    "short_duration": ["short duration", "short-term", "短期", "时间短"],
    "lack_control_group": ["control group", "lack of control", "缺乏对照"],
    "generalizability": ["generaliz", "外部效度", "推广性", "可推广"],
    "measurement_bias": ["measurement bias", "self-report", "测量偏差"],
    "method_limitation": ["methodology", "method limitation", "方法局限"],
    "domain_limitation": ["domain", "context specific", "领域局限"],
}


def classify_limitation_type(text: str) -> str:
    text_lower = text.lower()
    for ltype, keywords in _LIMITATION_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return ltype
    return "unknown"


def compute_gap_confidence(
    source_types: list[str],
    evidence_strength: str,
    supporting_paper_count: int,
    has_quote: bool,
) -> float:
    base = 0.3
    if "future_work" in source_types:
        base += 0.2
    if "possible_gap" in source_types:
        base += 0.2
    if evidence_strength == "high":
        base += 0.1
    if supporting_paper_count >= 2:
        base += 0.1
    if has_quote:
        base += 0.1
    return min(1.0, base)


def _build_adjacency(graph: KnowledgeGraph) -> dict[str, list[tuple[str, GraphEdge]]]:
    from collections import defaultdict
    adj: dict[str, list[tuple[str, GraphEdge]]] = defaultdict(list)
    for edge in graph.edges:
        adj[edge.source_id].append((edge.target_id, edge))
        adj[edge.target_id].append((edge.source_id, edge))
    return adj


def _save_graph(storage, project_id: str, graph: KnowledgeGraph) -> None:
    """保存到统一 graphs collection"""
    graph_data = graph.model_dump()
    graph_data["graph_id"] = f"kg_{project_id}"
    graph_data["version"] = 1
    storage.upsert_item("graphs", f"kg_{project_id}", graph_data)
    storage.save_collection(f"graph_{project_id}", [graph_data])
