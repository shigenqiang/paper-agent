"""
知识图谱嵌入模块

实现图嵌入算法:
1. TransE: 翻译距离模型
2. ComplEx: 复数域嵌入模型
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from src.agents_v2.logging_config import get_logging_logger

import math
import random

logger = get_logging_logger(__name__)


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    entity_id: str
    embedding: List[float]
    entity_type: str = "Unknown"


class TransE:
    """
    TransE嵌入模型

    原理: h + r ≈ t (头实体 + 关系 ≈ 尾实体)

    适用场景: 知识图谱补全, 关系预测
    """

    def __init__(
        self,
        num_entities: int,
        num_relations: int,
        embedding_dim: int = 100,
        margin: float = 1.0,
        learning_rate: float = 0.01,
        batch_size: int = 128,
        epochs: int = 100
    ):
        """
        Args:
            num_entities: 实体数量
            num_relations: 关系数量
            embedding_dim: 嵌入维度
            margin: hinge loss边界
            learning_rate: 学习率
            batch_size: 批大小
            epochs: 训练轮数
        """
        self.num_entities = num_entities
        self.num_relations = num_relations
        self.embedding_dim = embedding_dim
        self.margin = margin
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs

        self.entity_embeddings: Dict[str, List[float]] = {}
        self.relation_embeddings: Dict[str, List[float]] = {}

        self._initialized = False

    def initialize(self, entity_ids: List[str], relation_ids: List[str]) -> None:
        """初始化嵌入向量"""
        # 使用均匀分布初始化
        epsilon = 6.0 / math.sqrt(self.embedding_dim)

        for entity_id in entity_ids:
            self.entity_embeddings[entity_id] = [
                random.uniform(-epsilon, epsilon)
                for _ in range(self.embedding_dim)
            ]

        for relation_id in relation_ids:
            self.relation_embeddings[relation_id] = [
                random.uniform(-epsilon, epsilon)
                for _ in range(self.embedding_dim)
            ]

        self._initialized = True

    def _normalize_embeddings(self) -> None:
        """L2归一化"""
        for entity_id in self.entity_embeddings:
            emb = self.entity_embeddings[entity_id]
            norm = math.sqrt(sum(x * x for x in emb))
            if norm > 0:
                self.entity_embeddings[entity_id] = [x / norm for x in emb]

    def _margin_loss(
        self,
        positive_score: float,
        negative_score: float
    ) -> float:
        """hinge loss"""
        return max(0, self.margin - positive_score + negative_score)

    def _distance(
        self,
        h: List[float],
        r: List[float],
        t: List[float]
    ) -> float:
        """计算L1距离 (h + r - t)"""
        return sum(abs(h_i + r_i - t_i) for h_i, r_i, t_i in zip(h, r, t))

    def _score(
        self,
        h: List[float],
        r: List[float],
        t: List[float]
    ) -> float:
        """计算三元组得分"""
        return -self._distance(h, r, t)

    def train(
        self,
        positive_triplets: List[Tuple[str, str, str]],
        negative_samples_per_positive: int = 1
    ) -> Dict[str, float]:
        """
        训练TransE模型

        Args:
            positive_triplets: 正样本三元组 [(head_id, relation_id, tail_id), ...]
            negative_triplets: 负样本三元组

        Returns:
            训练历史 {"epoch": loss}
        """
        if not positive_triplets:
            return {}

        # 提取实体和关系ID
        entity_ids = set()
        relation_ids = set()
        for h, r, t in positive_triplets:
            entity_ids.add(h)
            entity_ids.add(t)
            relation_ids.add(r)

        self.initialize(list(entity_ids), list(relation_ids))

        history = {}
        all_entities = list(entity_ids)

        for epoch in range(self.epochs):
            total_loss = 0.0
            num_batches = 0

            # 打乱顺序
            random.shuffle(positive_triplets)

            for i in range(0, len(positive_triplets), self.batch_size):
                batch = positive_triplets[i:i + self.batch_size]
                batch_loss = 0.0

                for h, r, t in batch:
                    # 生成负样本
                    h_emb = self.entity_embeddings[h]
                    r_emb = self.relation_embeddings[r]
                    t_emb = self.entity_embeddings[t]

                    # 替换头或尾
                    if random.random() < 0.5:
                        # 替换头
                        neg_entity = random.choice(all_entities)
                        while neg_entity == h:
                            neg_entity = random.choice(all_entities)
                        h_emb_neg = self.entity_embeddings[neg_entity]
                        t_emb_neg = t_emb
                    else:
                        # 替换尾
                        neg_entity = random.choice(all_entities)
                        while neg_entity == t:
                            neg_entity = random.choice(all_entities)
                        h_emb_neg = h_emb
                        t_emb_neg = self.entity_embeddings[neg_entity]

                    pos_score = self._score(h_emb, r_emb, t_emb)
                    neg_score = self._score(h_emb_neg, r_emb, t_emb_neg)

                    loss = self._margin_loss(pos_score, neg_score)
                    if loss > 0:
                        batch_loss += loss

                        # 梯度更新 (简化版)
                        # 实际实现应该使用优化器
                        for j in range(self.embedding_dim):
                            # h + r - t 的符号
                            grad = 1.0 if (h_emb[j] + r_emb[j] - t_emb[j]) > 0 else -1.0

                            # 正样本梯度 (降低距离)
                            h_emb[j] -= self.learning_rate * grad
                            r_emb[j] -= self.learning_rate * grad * 0.5
                            t_emb[j] += self.learning_rate * grad

                            # 负样本梯度 (增加距离)
                            if h_emb_neg is not h_emb:
                                h_emb_neg[j] += self.learning_rate * grad
                            else:
                                t_emb_neg[j] -= self.learning_rate * grad

                total_loss += batch_loss
                num_batches += 1

            # 归一化
            self._normalize_embeddings()

            avg_loss = total_loss / num_batches if num_batches > 0 else 0
            history[epoch] = avg_loss

            if epoch % 10 == 0:
                logger.info(f"TransE epoch {epoch}: loss={avg_loss:.4f}")

        return history

    def get_entity_embedding(self, entity_id: str) -> Optional[List[float]]:
        """获取实体嵌入"""
        return self.entity_embeddings.get(entity_id)

    def get_relation_embedding(self, relation_id: str) -> Optional[List[float]]:
        """获取关系嵌入"""
        return self.relation_embeddings.get(relation_id)

    def predict_tail(
        self,
        head_id: str,
        relation_id: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        预测尾实体

        Args:
            head_id: 头实体ID
            relation_id: 关系ID
            top_k: 返回前k个

        Returns:
            [(tail_id, score), ...]
        """
        if head_id not in self.entity_embeddings or relation_id not in self.relation_embeddings:
            return []

        h_emb = self.entity_embeddings[head_id]
        r_emb = self.relation_embeddings[relation_id]

        # t ≈ h + r
        scores = []
        for tail_id, t_emb in self.entity_embeddings.items():
            if tail_id == head_id:
                continue
            dist = self._distance(h_emb, r_emb, t_emb)
            scores.append((tail_id, -dist))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def predict_head(
        self,
        tail_id: str,
        relation_id: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        预测头实体

        Args:
            tail_id: 尾实体ID
            relation_id: 关系ID
            top_k: 返回前k个

        Returns:
            [(head_id, score), ...]
        """
        if tail_id not in self.entity_embeddings or relation_id not in self.relation_embeddings:
            return []

        t_emb = self.entity_embeddings[tail_id]
        r_emb = self.relation_embeddings[relation_id]

        # h ≈ t - r
        scores = []
        for head_id, h_emb in self.entity_embeddings.items():
            if head_id == tail_id:
                continue
            dist = self._distance(h_emb, r_emb, t_emb)
            scores.append((head_id, -dist))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class ComplEx:
    """
    ComplEx嵌入模型

    原理: 在复数域中学习嵌入, 支持非对称关系

    得分函数: Re(<h, r, t>) = Re(Σ h_i * r_i * conj(t_i))

    适用场景: 多关系知识图谱, 关系类型丰富
    """

    def __init__(
        self,
        num_entities: int,
        num_relations: int,
        embedding_dim: int = 100,
        learning_rate: float = 0.01,
        batch_size: int = 128,
        epochs: int = 100
    ):
        """
        Args:
            num_entities: 实体数量
            num_relations: 关系数量
            embedding_dim: 嵌入维度 (实部和虚部)
            learning_rate: 学习率
            batch_size: 批大小
            epochs: 训练轮数
        """
        self.num_entities = num_entities
        self.num_relations = num_relations
        self.embedding_dim = embedding_dim
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs

        # 存储实部和虚部
        self.entity_embeddings_real: Dict[str, List[float]] = {}
        self.entity_embeddings_imag: Dict[str, List[float]] = {}
        self.relation_embeddings_real: Dict[str, List[float]] = {}
        self.relation_embeddings_imag: Dict[str, List[float]] = {}

        self._initialized = False

    def initialize(self, entity_ids: List[str], relation_ids: List[str]) -> None:
        """初始化嵌入向量 (使用Xavier初始化)"""
        scale = math.sqrt(2.0 / (self.embedding_dim * 2))

        for entity_id in entity_ids:
            self.entity_embeddings_real[entity_id] = [
                random.gauss(0, scale) for _ in range(self.embedding_dim)
            ]
            self.entity_embeddings_imag[entity_id] = [
                random.gauss(0, scale) for _ in range(self.embedding_dim)
            ]

        for relation_id in relation_ids:
            self.relation_embeddings_real[relation_id] = [
                random.gauss(0, scale) for _ in range(self.embedding_dim)
            ]
            self.relation_embeddings_imag[relation_id] = [
                random.gauss(0, scale) for _ in range(self.embedding_dim)
            ]

        self._initialized = True

    def _complex_mul(
        self,
        h_real: List[float],
        h_imag: List[float],
        r_real: List[float],
        r_imag: List[float],
        t_real: List[float],
        t_imag: List[float]
    ) -> float:
        """
        计算复数乘积的实部
        Re(h * r * conj(t)) = Re((h_r + ih_i) * (r_r + ir_i) * (t_r - it_i))
        """
        # h * r
        hr_real = [
            h_r * r_r - h_i * r_i
            for h_r, h_i, r_r, r_i in zip(h_real, h_imag, r_real, r_imag)
        ]
        hr_imag = [
            h_r * r_i + h_i * r_r
            for h_r, h_i, r_r, r_i in zip(h_real, h_imag, r_real, r_imag)
        ]

        # (h * r) * conj(t) = (hr * t - i*hr_imag * t_imag) + i(...)
        result_real = sum(
            hr_r * t_r + hr_i * t_imag
            for hr_r, hr_i, t_r, t_imag in zip(hr_real, hr_imag, t_real, t_imag)
        )

        return result_real

    def _score(
        self,
        h_real: List[float],
        h_imag: List[float],
        r_real: List[float],
        r_imag: List[float],
        t_real: List[float],
        t_imag: List[float]
    ) -> float:
        """计算三元组得分"""
        return self._complex_mul(h_real, h_imag, r_real, r_imag, t_real, t_imag)

    def train(
        self,
        positive_triplets: List[Tuple[str, str, str]],
        negative_samples_per_positive: int = 1
    ) -> Dict[str, float]:
        """
        训练ComplEx模型

        Args:
            positive_triplets: 正样本三元组 [(head_id, relation_id, tail_id), ...]

        Returns:
            训练历史
        """
        if not positive_triplets:
            return {}

        entity_ids = set()
        relation_ids = set()
        for h, r, t in positive_triplets:
            entity_ids.add(h)
            entity_ids.add(t)
            relation_ids.add(r)

        self.initialize(list(entity_ids), list(relation_ids))

        history = {}
        all_entities = list(entity_ids)

        for epoch in range(self.epochs):
            total_loss = 0.0
            num_batches = 0

            random.shuffle(positive_triplets)

            for i in range(0, len(positive_triplets), self.batch_size):
                batch = positive_triplets[i:i + self.batch_size]
                batch_loss = 0.0

                for h, r, t in batch:
                    h_real = self.entity_embeddings_real[h]
                    h_imag = self.entity_embeddings_imag[h]
                    r_real = self.relation_embeddings_real[r]
                    r_imag = self.relation_embeddings_imag[r]
                    t_real = self.entity_embeddings_real[t]
                    t_imag = self.entity_embeddings_imag[t]

                    # 生成负样本
                    if random.random() < 0.5:
                        neg_entity = random.choice(all_entities)
                        while neg_entity == h:
                            neg_entity = random.choice(all_entities)
                        neg_h_real = self.entity_embeddings_real[neg_entity]
                        neg_h_imag = self.entity_embeddings_imag[neg_entity]
                        neg_t_real = t_real
                        neg_t_imag = t_imag
                    else:
                        neg_entity = random.choice(all_entities)
                        while neg_entity == t:
                            neg_entity = random.choice(all_entities)
                        neg_h_real = h_real
                        neg_h_imag = h_imag
                        neg_t_real = self.entity_embeddings_real[neg_entity]
                        neg_t_imag = self.entity_embeddings_imag[neg_entity]

                    pos_score = self._score(h_real, h_imag, r_real, r_imag, t_real, t_imag)
                    neg_score = self._score(neg_h_real, neg_h_imag, r_real, r_imag, neg_t_real, neg_t_imag)

                    # softplus loss
                    loss = math.log(1 + math.exp(-(pos_score - neg_score)))
                    batch_loss += loss

                total_loss += batch_loss
                num_batches += 1

            avg_loss = total_loss / num_batches if num_batches > 0 else 0
            history[epoch] = avg_loss

            if epoch % 10 == 0:
                logger.info(f"ComplEx epoch {epoch}: loss={avg_loss:.4f}")

        return history

    def get_entity_embedding(self, entity_id: str) -> Optional[List[float]]:
        """获取实体嵌入 (实部和虚部拼接)"""
        if entity_id not in self.entity_embeddings_real:
            return None
        real = self.entity_embeddings_real[entity_id]
        imag = self.entity_embeddings_imag[entity_id]
        return real + imag  # 拼接

    def get_relation_embedding(self, relation_id: str) -> Optional[List[float]]:
        """获取关系嵌入"""
        if relation_id not in self.relation_embeddings_real:
            return None
        real = self.relation_embeddings_real[relation_id]
        imag = self.relation_embeddings_imag[relation_id]
        return real + imag

    def predict_tail(
        self,
        head_id: str,
        relation_id: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """预测尾实体"""
        if head_id not in self.entity_embeddings_real or relation_id not in self.relation_embeddings_real:
            return []

        h_real = self.entity_embeddings_real[head_id]
        h_imag = self.entity_embeddings_imag[head_id]
        r_real = self.relation_embeddings_real[relation_id]
        r_imag = self.relation_embeddings_imag[relation_id]

        scores = []
        for tail_id in self.entity_embeddings_real:
            if tail_id == head_id:
                continue
            t_real = self.entity_embeddings_real[tail_id]
            t_imag = self.entity_embeddings_imag[tail_id]
            score = self._score(h_real, h_imag, r_real, r_imag, t_real, t_imag)
            scores.append((tail_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class EmbeddingTrainer:
    """
    嵌入训练器

    统一接口训练TransE和ComplEx
    """

    def __init__(self, algorithm: str = "TransE", **kwargs):
        """
        Args:
            algorithm: "TransE" 或 "ComplEx"
            **kwargs: 传给嵌入模型的参数
        """
        self.algorithm = algorithm
        self.kwargs = kwargs
        self.model = None

    def train(
        self,
        triplets: List[Tuple[str, str, str]],
        epochs: int = 100
    ) -> Dict[str, Any]:
        """
        训练模型

        Args:
            triplets: 三元组列表 [(head, relation, tail), ...]
            epochs: 训练轮数

        Returns:
            {"model": trained_model, "history": {...}}
        """
        if not triplets:
            return {"model": None, "history": {}}

        # 统计实体和关系数量
        entity_ids = set()
        relation_ids = set()
        for h, r, t in triplets:
            entity_ids.add(h)
            entity_ids.add(t)
            relation_ids.add(r)

        # 构建kwargs，epochs由参数传入，不从kwargs覆盖
        kwargs = dict(self.kwargs)

        if self.algorithm == "TransE":
            self.model = TransE(
                num_entities=len(entity_ids),
                num_relations=len(relation_ids),
                epochs=epochs,
                **kwargs
            )
        elif self.algorithm == "ComplEx":
            self.model = ComplEx(
                num_entities=len(entity_ids),
                num_relations=len(relation_ids),
                epochs=epochs,
                **kwargs
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")

        history = self.model.train(triplets)
        return {"model": self.model, "history": history}

    def get_entity_embedding(self, entity_id: str) -> Optional[List[float]]:
        """获取实体嵌入"""
        if self.model is None:
            return None
        return self.model.get_entity_embedding(entity_id)

    def get_relation_embedding(self, relation_id: str) -> Optional[List[float]]:
        """获取关系嵌入"""
        if self.model is None:
            return None
        return self.model.get_relation_embedding(relation_id)

    def predict(self, head_id: str, relation_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """预测尾实体"""
        if self.model is None:
            return []
        return self.model.predict_tail(head_id, relation_id, top_k)
