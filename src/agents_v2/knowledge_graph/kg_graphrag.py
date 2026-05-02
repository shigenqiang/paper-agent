"""
知识图谱GraphRAG问答模块

功能:
1. 查询理解与实体提取
2. 混合检索 (向量+图)
3. 子图上下文构建
4. 答案生成支持
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class QueryType(str, Enum):
    """查询类型"""
    FACTUAL = "factual"           # 事实查询 "谁写了X论文"
    COMPARATIVE = "comparative"   # 比较查询 "A和B哪个更好"
    EXPLORATORY = "exploratory"   # 探索查询 "关于X的研究趋势"
    CAUSAL = "causal"             # 因果查询 "为什么X导致Y"
    SUMMARY = "summary"           # 摘要查询 "总结X领域"


@dataclass
class Query:
    """查询"""
    text: str
    query_type: QueryType
    entities: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


@dataclass
class RetrievalItem:
    """检索项"""
    entity_id: str
    entity_type: str
    score: float
    method: str  # "vector", "graph", "keyword"
    content: str  # 文本内容


@dataclass
class GraphRAGContext:
    """GraphRAG上下文"""
    query: Query
    retrieved_items: List[RetrievalItem]
    subgraph_summary: str
    entity_map: Dict[str, str]  # entity_id -> name
    evidence: List[str] = field(default_factory=list)  # 支持证据

    def to_prompt_context(self) -> str:
        """转换为prompt上下文"""
        parts = [f"查询类型: {self.query.query_type.value}\n"]

        if self.entity_map:
            parts.append("相关实体:")
            for eid, name in self.entity_map.items():
                parts.append(f"  - {name}")
            parts.append("")

        if self.subgraph_summary:
            parts.append(f"上下文摘要:\n{self.subgraph_summary}\n")

        if self.evidence:
            parts.append("支持证据:")
            for i, ev in enumerate(self.evidence, 1):
                parts.append(f"  {i}. {ev}")

        return "\n".join(parts)


class QueryClassifier:
    """
    查询分类器

    识别查询类型并提取关键信息
    """

    def __init__(self):
        self.type_keywords = {
            QueryType.FACTUAL: ["谁", "什么", "哪个", "多少", "who", "what", "which"],
            QueryType.COMPARATIVE: ["比较", "哪个更好", "区别", "差异", "compare", "better", "difference"],
            QueryType.EXPLORATORY: ["关于", "趋势", "研究", "领域", "about", "trend", "research"],
            QueryType.CAUSAL: ["为什么", "因为", "导致", "原因", "why", "because", "cause"],
            QueryType.SUMMARY: ["总结", "概括", "描述", "介绍", "summarize", "describe", "introduction"]
        }

    def classify(self, query_text: str) -> QueryType:
        """分类查询"""
        query_lower = query_text.lower()

        scores = {}
        for qtype, keywords in self.type_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[qtype] = score

        if max(scores.values()) == 0:
            return QueryType.FACTUAL

        return max(scores, key=scores.get)

    def extract_entities(self, query_text: str) -> List[str]:
        """提取实体提及"""
        entities = []

        # 提取带引号的实体
        import re
        quoted = re.findall(r'["\"](.+?)["\"]', query_text)
        entities.extend(quoted)

        # 提取#数字引用
        refs = re.findall(r'#(\d+)', query_text)
        entities.extend([f"paper_{r}" for r in refs])

        return entities

    def extract_keywords(self, query_text: str) -> List[str]:
        """提取关键词"""
        # 停用词
        stopwords = {"的", "是", "在", "了", "和", "与", "或", "以及", "the", "a", "an", "is", "are", "and", "or"}

        import re
        words = re.findall(r'[\w]+', query_text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 1]

        return list(set(keywords))


class GraphRAGRetriever:
    """
    GraphRAG检索器

    整合混合检索、子图摘要等功能
    """

    def __init__(
        self,
        vector_weight: float = 0.4,
        graph_weight: float = 0.3,
        keyword_weight: float = 0.3
    ):
        """
        Args:
            vector_weight: 向量检索权重
            graph_weight: 图检索权重
            keyword_weight: 关键词检索权重
        """
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.keyword_weight = keyword_weight

        # 组件初始化
        self.query_classifier = QueryClassifier()

        # 数据存储
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._relations: List[Tuple[str, str, str]] = []
        self._text_index: Dict[str, str] = {}  # entity_id -> text
        self._keyword_index: Dict[str, Set[str]] = {}  # keyword -> entity_ids

    def add_entity(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        properties: Optional[Dict[str, Any]] = None,
        keywords: Optional[List[str]] = None
    ) -> None:
        """
        添加实体

        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            text: 实体的文本表示（用于检索）
            properties: 属性字典
            keywords: 关键词列表（自动从text提取）
        """
        self._entities[entity_id] = {
            "type": entity_type,
            "text": text,
            "properties": properties or {}
        }
        self._text_index[entity_id] = text

        # 关键词索引
        if keywords is None:
            classifier = QueryClassifier()
            keywords = classifier.extract_keywords(text)

        for kw in keywords:
            if kw not in self._keyword_index:
                self._keyword_index[kw] = set()
            self._keyword_index[kw].add(entity_id)

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str
    ) -> None:
        """添加关系"""
        if source_id in self._entities and target_id in self._entities:
            self._relations.append((source_id, target_id, relation_type))

    def search_by_vector(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        向量检索

        Returns:
            [(entity_id, score), ...]
        """
        # 简化实现：基于关键词匹配
        # 实际应使用向量数据库
        results = []
        query_lower = query_embedding  # 简化

        for entity_id, entity_data in self._entities.items():
            # 使用文本长度作为相似度代理
            score = len(entity_data["text"]) / 100.0
            results.append((entity_id, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_by_graph(
        self,
        entity_ids: List[str],
        depth: int = 2,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        图检索

        Returns:
            [(entity_id, score), ...]
        """
        if not entity_ids:
            return []

        visited = set(entity_ids)
        current_level = set(entity_ids)

        for _ in range(depth):
            next_level = set()
            for source, target, rel in self._relations:
                if source in current_level and target not in visited:
                    next_level.add(target)
                if target in current_level and source not in visited:
                    next_level.add(source)

            visited.update(next_level)
            current_level = next_level

        # 计算得分（基于连接数）
        scores = []
        for eid in visited:
            connections = sum(
                1 for s, t, _ in self._relations
                if s == eid or t == eid
            )
            scores.append((eid, float(connections)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def search_by_keywords(
        self,
        keywords: List[str],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        关键词检索

        Returns:
            [(entity_id, score), ...]
        """
        entity_scores: Dict[str, float] = {}

        for kw in keywords:
            kw_lower = kw.lower()
            for entity_id, entity_data in self._entities.items():
                text_lower = entity_data["text"].lower()
                if kw_lower in text_lower:
                    entity_scores[entity_id] = entity_scores.get(entity_id, 0) + 1.0

        results = list(entity_scores.items())
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def retrieve(
        self,
        query_text: str,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10
    ) -> GraphRAGContext:
        """
        检索

        Args:
            query_text: 查询文本
            query_embedding: 查询向量
            top_k: 返回数量

        Returns:
            GraphRAGContext
        """
        # 1. 分类查询
        query_type = self.query_classifier.classify(query_text)
        extracted_entities = self.query_classifier.extract_entities(query_text)
        keywords = self.query_classifier.extract_keywords(query_text)

        query = Query(
            text=query_text,
            query_type=query_type,
            entities=extracted_entities,
            keywords=keywords
        )

        # 2. 多路召回
        all_scores: Dict[str, Dict[str, float]] = {}

        # 向量检索
        if query_embedding:
            vector_results = self.search_by_vector(query_embedding, top_k * 2)
            for eid, score in vector_results:
                if eid not in all_scores:
                    all_scores[eid] = {}
                all_scores[eid]["vector"] = score * self.vector_weight

        # 图检索
        graph_results = self.search_by_graph(extracted_entities, depth=2, top_k=top_k * 2)
        for eid, score in graph_results:
            if eid not in all_scores:
                all_scores[eid] = {}
            all_scores[eid]["graph"] = score * self.graph_weight

        # 关键词检索
        keyword_results = self.search_by_keywords(keywords, top_k * 2)
        for eid, score in keyword_results:
            if eid not in all_scores:
                all_scores[eid] = {}
            all_scores[eid]["keyword"] = score * self.keyword_weight

        # 3. 融合排序
        final_scores = []
        for eid, method_scores in all_scores.items():
            total_score = sum(method_scores.values())
            primary_method = max(method_scores, key=method_scores.get)
            final_scores.append((eid, total_score, primary_method))

        final_scores.sort(key=lambda x: x[1], reverse=True)
        top_results = final_scores[:top_k]

        # 4. 构建检索结果
        retrieved_items = []
        for eid, score, method in top_results:
            entity_data = self._entities.get(eid, {})
            retrieved_items.append(RetrievalItem(
                entity_id=eid,
                entity_type=entity_data.get("type", "Unknown"),
                score=score,
                method=method,
                content=entity_data.get("text", "")
            ))

        # 5. 构建实体映射
        entity_map = {
            eid: self._entities.get(eid, {}).get("text", eid)
            for eid, _, _ in top_results
        }

        # 6. 生成摘要文本
        summary_parts = []
        for item in retrieved_items[:5]:
            summary_parts.append(f"[{item.entity_type}] {item.content}")

        subgraph_summary = "\n".join(summary_parts)

        # 7. 生成证据
        evidence = []
        for item in retrieved_items[:3]:
            evidence.append(f"{item.content}")

        return GraphRAGContext(
            query=query,
            retrieved_items=retrieved_items,
            subgraph_summary=subgraph_summary,
            entity_map=entity_map,
            evidence=evidence
        )


class GraphRAGQA:
    """
    GraphRAG问答系统

    端到端的问答流程
    """

    def __init__(self):
        self.retriever = GraphRAGRetriever()

    def build_index(
        self,
        entities: List[Tuple[str, str, str]],  # (id, type, text)
        relations: List[Tuple[str, str, str]]   # (source, target, rel_type)
    ) -> None:
        """构建索引"""
        for entity_id, entity_type, text in entities:
            self.retriever.add_entity(entity_id, entity_type, text)

        for source, target, rel_type in relations:
            self.retriever.add_relation(source, target, rel_type)

    def query(
        self,
        question: str,
        query_embedding: Optional[List[float]] = None
    ) -> GraphRAGContext:
        """
        问答

        Args:
            question: 问题
            query_embedding: 查询向量

        Returns:
            GraphRAGContext
        """
        return self.retriever.retrieve(question, query_embedding)

    def batch_query(
        self,
        questions: List[str],
        query_embeddings: Optional[List[List[float]]] = None
    ) -> List[GraphRAGContext]:
        """批量问答"""
        contexts = []
        for i, question in enumerate(questions):
            emb = query_embeddings[i] if query_embeddings else None
            contexts.append(self.query(question, emb))
        return contexts


def create_graphrag_qa() -> GraphRAGQA:
    """创建GraphRAG QA系统"""
    return GraphRAGQA()
