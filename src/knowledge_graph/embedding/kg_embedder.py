"""
知识图谱嵌入
Knowledge Graph Embedding
"""

from typing import List, Dict, Tuple, Optional, Any
import numpy as np


class KGEmbedder:
    """知识图谱嵌入器"""

    def __init__(
        self,
        method: str = "TransE",
        embedding_dim: int = 256,
        margin: float = 1.0,
        learning_rate: float = 0.01
    ):
        self.method = method
        self.embedding_dim = embedding_dim
        self.margin = margin
        self.learning_rate = learning_rate

        self.entity_embeddings: Dict[str, np.ndarray] = {}
        self.relation_embeddings: Dict[str, np.ndarray] = {}

        self._initialized = False

    def initialize(self, entity_count: int, relation_count: int):
        """初始化嵌入矩阵"""
        # 使用较小的初始值初始化
        epsilon = 0.001

        # 初始化实体嵌入
        for i in range(entity_count):
            entity_id = f"entity_{i}"
            # Xavier初始化
            emb = np.random.uniform(
                -epsilon, epsilon,
                self.embedding_dim
            )
            # 归一化
            emb = emb / (np.linalg.norm(emb) + 1e-8)
            self.entity_embeddings[entity_id] = emb

        # 初始化关系嵌入
        for i in range(relation_count):
            rel_id = f"relation_{i}"
            emb = np.random.uniform(
                -epsilon, epsilon,
                self.embedding_dim
            )
            emb = emb / (np.linalg.norm(emb) + 1e-8)
            self.relation_embeddings[rel_id] = emb

        self._initialized = True

    def get_entity_embedding(self, entity_id: str) -> Optional[np.ndarray]:
        """获取实体嵌入"""
        return self.entity_embeddings.get(entity_id)

    def get_relation_embedding(self, relation_id: str) -> Optional[np.ndarray]:
        """获取关系嵌入"""
        return self.relation_embeddings.get(relation_id)

    def compute_score(
        self,
        head: np.ndarray,
        relation: np.ndarray,
        tail: np.ndarray
    ) -> float:
        """计算三元组的得分"""
        if self.method == "TransE":
            return self._transE_score(head, relation, tail)
        elif self.method == "TransR":
            return self._transR_score(head, relation, tail)
        elif self.method == "RotatE":
            return self._rotatE_score(head, relation, tail)
        else:
            return self._transE_score(head, relation, tail)

    def _transE_score(
        self,
        head: np.ndarray,
        relation: np.ndarray,
        tail: np.ndarray
    ) -> float:
        """TransE得分函数: h + r ≈ t"""
        score = head + relation - tail
        # 返回负的距离作为得分（越小越好）
        return -np.linalg.norm(score)

    def _transR_score(
        self,
        head: np.ndarray,
        relation: np.ndarray,
        tail: np.ndarray
    ) -> float:
        """TransR得分函数"""
        # 简化实现
        score = head + relation - tail
        return -np.linalg.norm(score)

    def _rotatE_score(
        self,
        head: np.ndarray,
        relation: np.ndarray,
        tail: np.ndarray
    ) -> float:
        """RotatE得分函数: h * r ≈ t"""
        # 简化实现，假设embedding_dim是偶数
        dim = len(head)
        half_dim = dim // 2

        # 复数旋转
        head_h = head[:half_dim]
        head_t = head[half_dim:]

        rel_phase = relation[:half_dim]
        rel_scale = relation[half_dim:]

        # 旋转
        rotated = head_h * np.cos(rel_phase) + head_t * np.sin(rel_phase)
        rotated = rotated * rel_scale

        score = rotated - tail[:half_dim]
        return -np.linalg.norm(score)

    def train(
        self,
        positive_triples: List[Tuple[str, str, str]],
        negative_triples: List[Tuple[str, str, str]],
        epochs: int = 100,
        batch_size: int = 256
    ) -> Dict[str, float]:
        """训练嵌入模型"""
        if not self._initialized:
            # 自动初始化
            all_entities = set()
            all_relations = set()

            for h, r, t in positive_triples + negative_triples:
                all_entities.add(h)
                all_entities.add(t)
                all_relations.add(r)

            self.initialize(len(all_entities), len(all_relations))

        losses = []

        for epoch in range(epochs):
            epoch_loss = 0.0

            # 批训练
            for i in range(0, len(positive_triples), batch_size):
                pos_batch = positive_triples[i:i + batch_size]
                neg_batch = negative_triples[i:i + batch_size]

                batch_loss = self._compute_batch_loss(pos_batch, neg_batch)
                epoch_loss += batch_loss

                # 更新梯度（简化版）
                self._gradient_descent_step(pos_batch, neg_batch)

            losses.append(epoch_loss)

            if epoch % 10 == 0:
                print(f"Epoch {epoch}, Loss: {epoch_loss:.4f}")

        return {
            "final_loss": losses[-1] if losses else 0.0,
            "epochs": epochs
        }

    def _compute_batch_loss(
        self,
        pos_triples: List[Tuple[str, str, str]],
        neg_triples: List[Tuple[str, str, str]]
    ) -> float:
        """计算批次损失"""
        pos_scores = []
        neg_scores = []

        for h, r, t in pos_triples:
            h_emb = self.get_entity_embedding(h)
            r_emb = self.get_relation_embedding(r)
            t_emb = self.get_entity_embedding(t)

            if all(e is not None for e in [h_emb, r_emb, t_emb]):
                score = self.compute_score(h_emb, r_emb, t_emb)
                pos_scores.append(score)

        for h, r, t in neg_triples:
            h_emb = self.get_entity_embedding(h)
            r_emb = self.get_relation_embedding(r)
            t_emb = self.get_entity_embedding(t)

            if all(e is not None for e in [h_emb, r_emb, t_emb]):
                score = self.compute_score(h_emb, r_emb, t_emb)
                neg_scores.append(score)

        if not pos_scores or not neg_scores:
            return 0.0

        # margin ranking loss
        pos_scores = np.array(pos_scores)
        neg_scores = np.array(neg_scores)

        loss = np.mean(np.maximum(0, self.margin - pos_scores[:, None] + neg_scores[None, :]))

        return float(loss)

    def _gradient_descent_step(
        self,
        pos_triples: List[Tuple[str, str, str]],
        neg_triples: List[Tuple[str, str, str]]
    ):
        """简化的梯度下降步骤"""
        alpha = self.learning_rate

        for h, r, t in pos_triples:
            h_emb = self.get_entity_embedding(h)
            r_emb = self.get_relation_embedding(r)
            t_emb = self.get_entity_embedding(t)

            if all(e is not None for e in [h_emb, r_emb, t_emb]):
                # 简化梯度更新
                gradient = h_emb + r_emb - t_emb
                h_emb = h_emb - alpha * gradient * 0.1
                t_emb = t_emb + alpha * gradient * 0.1

                self.entity_embeddings[h] = h_emb / (np.linalg.norm(h_emb) + 1e-8)
                self.entity_embeddings[t] = t_emb / (np.linalg.norm(t_emb) + 1e-8)

        for h, r, t in neg_triples:
            h_emb = self.get_entity_embedding(h)
            r_emb = self.get_relation_embedding(r)
            t_emb = self.get_entity_embedding(t)

            if all(e is not None for e in [h_emb, r_emb, t_emb]):
                gradient = h_emb + r_emb - t_emb
                h_emb = h_emb + alpha * gradient * 0.1
                t_emb = t_emb - alpha * gradient * 0.1

                self.entity_embeddings[h] = h_emb / (np.linalg.norm(h_emb) + 1e-8)
                self.entity_embeddings[t] = t_emb / (np.linalg.norm(t_emb) + 1e-8)

    def compute_similarity(
        self,
        entity1: str,
        entity2: str,
        metric: str = "cosine"
    ) -> float:
        """计算两个实体的相似度"""
        emb1 = self.get_entity_embedding(entity1)
        emb2 = self.get_entity_embedding(entity2)

        if emb1 is None or emb2 is None:
            return 0.0

        if metric == "cosine":
            # 余弦相似度
            dot = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            return dot / (norm1 * norm2 + 1e-8)
        elif metric == "euclidean":
            # 欧氏距离
            return -np.linalg.norm(emb1 - emb2)
        else:
            return 0.0

    def find_similar_entities(
        self,
        entity_id: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """查找相似实体"""
        target_emb = self.get_entity_embedding(entity_id)
        if target_emb is None:
            return []

        similarities = []
        for eid, emb in self.entity_embeddings.items():
            if eid != entity_id:
                sim = np.dot(target_emb, emb) / (
                    np.linalg.norm(target_emb) * np.linalg.norm(emb) + 1e-8
                )
                similarities.append((eid, float(sim)))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def get_neighbors_embedding(self, entity_id: str) -> np.ndarray:
        """获取邻居节点的聚合嵌入"""
        # 这是一个简化实现
        neighbors = []  # 应该从图中获取

        if not neighbors:
            # 返回自身嵌入
            return self.get_entity_embedding(entity_id) or np.zeros(self.embedding_dim)

        neighbor_embs = [self.get_entity_embedding(n) for n in neighbors]
        neighbor_embs = [e for e in neighbor_embs if e is not None]

        if not neighbor_embs:
            return self.get_entity_embedding(entity_id) or np.zeros(self.embedding_dim)

        return np.mean(neighbor_embs, axis=0)
