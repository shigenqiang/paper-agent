"""BERTopic主题建模"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TopicModeler:
    """使用BERTopic进行主题建模"""

    def __init__(
        self,
        language: str = "chinese",
        nr_topics: Optional[int] = None,
        min_topic_size: int = 5,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        verbose: bool = True
    ):
        """
        Args:
            language: 语言
            nr_topics: 主题数量，None表示自动确定
            min_topic_size: 每个主题的最小文档数
            embedding_model: 嵌入模型
            verbose: 是否显示详细输出
        """
        self.language = language
        self.nr_topics = nr_topics
        self.min_topic_size = min_topic_size
        self.embedding_model = embedding_model
        self.verbose = verbose

        self.topic_model = None
        self.topics = []
        self.topic_info = None

    def fit(self, documents: List[str]) -> Dict[str, Any]:
        """
        训练主题模型

        Args:
            documents: 文档列表

        Returns:
            主题信息字典
        """
        try:
            from bertopic import BERTopic
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error(
                "BERTopic or sentence-transformers not installed. "
                "Please install them: pip install bertopic sentence-transformers"
            )
            return {}

        logger.info(f"Training BERTopic on {len(documents)} documents...")

        # 初始化BERTopic
        self.topic_model = BERTopic(
            language=self.language,
            nr_topics=self.nr_topics,
            min_topic_size=self.min_topic_size,
            embedding_model=self.embedding_model,
            verbose=self.verbose
        )

        # 训练模型
        topics, probs = self.topic_model.fit_transform(documents)

        # 获取主题信息
        self.topic_info = self.topic_model.get_topic_info()

        # 提取主题
        self.topics = self._extract_topics()

        logger.info(f"Topic modeling completed: {len(self.topics)} topics found")

        return {
            "topics": self.topics,
            "topic_info": self.topic_info.to_dict(),
            "topic_distribution": topics,
            "probabilities": probs.tolist()
        }

    def _extract_topics(self) -> List[Dict[str, Any]]:
        """提取主题信息"""
        if self.topic_model is None:
            return []

        topics = []

        # 获取主题信息
        topic_info = self.topic_model.get_topic_info()

        for _, row in topic_info.iterrows():
            topic_id = int(row['Topic'])

            if topic_id == -1:  # -1 是离群点
                continue

            # 获取主题词
            topic_words = self.topic_model.get_topic(topic_id)

            topics.append({
                "topic_id": topic_id,
                "name": self._generate_topic_name(topic_words),
                "words": [word for word, _ in topic_words[:10]],
                "word_scores": [score for _, score in topic_words[:10]],
                "count": int(row['Count']),
                "frequency": float(row['Freq'])
            })

        return topics

    def _generate_topic_name(self, topic_words: List[tuple]) -> str:
        """生成主题名称"""
        if not topic_words:
            return "Unknown Topic"

        # 使用前3个词生成主题名称
        top_words = [word for word, _ in topic_words[:3]]
        return " + ".join(top_words)

    def predict(self, documents: List[str]) -> List[int]:
        """
        预测文档的主题

        Args:
            documents: 文档列表

        Returns:
            主题ID列表
        """
        if self.topic_model is None:
            raise ValueError("Topic model not trained. Call fit() first.")

        topics, _ = self.topic_model.transform(documents)
        return topics.tolist()

    def get_document_topics(
        self,
        document: str,
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        获取文档的主题分布

        Args:
            document: 文档文本
            top_n: 返回前n个主题

        Returns:
            主题分布列表
        """
        if self.topic_model is None:
            raise ValueError("Topic model not trained. Call fit() first.")

        # 转换为向量
        topics, probs = self.topic_model.transform([document])

        # 获取主题概率
        topic_probs = []
        for topic_id, prob in zip(topics, probs[0]):
            if topic_id != -1:  # 排除离群点
                topic_name = self._get_topic_name(topic_id)
                topic_probs.append({
                    "topic_id": int(topic_id),
                    "topic_name": topic_name,
                    "probability": float(prob)
                })

        # 按概率排序
        topic_probs.sort(key=lambda x: x["probability"], reverse=True)

        return topic_probs[:top_n]

    def _get_topic_name(self, topic_id: int) -> str:
        """获取主题名称"""
        for topic in self.topics:
            if topic["topic_id"] == topic_id:
                return topic["name"]
        return f"Topic {topic_id}"

    def visualize_topics(self):
        """可视化主题（需要Jupyter notebook）"""
        if self.topic_model is None:
            raise ValueError("Topic model not trained. Call fit() first.")

        return self.topic_model.visualize_topics()

    def get_topic_hierarchy(self) -> Dict[str, Any]:
        """获取主题层次结构"""
        if self.topic_model is None:
            raise ValueError("Topic model not trained. Call fit() first.")

        # 获取层次聚类
        hierarchy = self.topic_model.hierarchical_topics()

        return {
            "hierarchy": hierarchy.to_dict(),
            "topics": self.topics
        }

    def update(self, new_documents: List[str]) -> Dict[str, Any]:
        """
        增量更新主题模型

        Args:
            new_documents: 新文档列表

        Returns:
            更新后的主题信息
        """
        if self.topic_model is None:
            raise ValueError("Topic model not trained. Call fit() first.")

        logger.info(f"Updating topic model with {len(new_documents)} new documents...")

        # 增量更新
        topics, probs = self.topic_model.partial_fit(new_documents)

        # 更新主题信息
        self.topic_info = self.topic_model.get_topic_info()
        self.topics = self._extract_topics()

        logger.info("Topic model updated successfully")

        return {
            "topics": self.topics,
            "topic_info": self.topic_info.to_dict()
        }

    def reduce_topics(self, nr_topics: int) -> Dict[str, Any]:
        """
        减少主题数量

        Args:
            nr_topics: 目标主题数量

        Returns:
            减少后的主题信息
        """
        if self.topic_model is None:
            raise ValueError("Topic model not trained. Call fit() first.")

        logger.info(f"Reducing topics to {nr_topics}...")

        # 减少主题
        self.topic_model.reduce_topics(self.topic_model.nr_topics)

        # 更新主题信息
        self.topic_info = self.topic_model.get_topic_info()
        self.topics = self._extract_topics()

        logger.info(f"Topics reduced to {len(self.topics)}")

        return {
            "topics": self.topics,
            "topic_info": self.topic_info.to_dict()
        }


class TopicChangeDetector:
    """主题变化检测器 - 用于CDC-BERTopic"""

    def __init__(
        self,
        window_size: int = 100,
        min_topic_size: int = 5,
        similarity_threshold: float = 0.7
    ):
        """
        Args:
            window_size: 滑动窗口大小
            min_topic_size: 最小主题大小
            similarity_threshold: 主题相似度阈值
        """
        self.window_size = window_size
        self.min_topic_size = min_topic_size
        self.similarity_threshold = similarity_threshold

        self.topic_modeler = TopicModeler(
            min_topic_size=min_topic_size,
            verbose=False
        )

        self.previous_topics = []
        self.topic_history = []

    def process_batch(
        self,
        documents: List[str],
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        处理一批文档，检测主题变化

        Args:
            documents: 文档列表
            timestamp: 时间戳

        Returns:
            检测结果
        """
        if timestamp is None:
            timestamp = datetime.now()

        logger.info(f"Processing batch of {len(documents)} documents...")

        # 在当前批次上训练主题模型
        result = self.topic_modeler.fit(documents)
        current_topics = result.get("topics", [])

        # 检测变化
        changes = self._detect_changes(current_topics)

        # 记录历史
        topic_snapshot = {
            "timestamp": timestamp.isoformat(),
            "topics": current_topics,
            "changes": changes
        }
        self.topic_history.append(topic_snapshot)

        # 更新之前的主题
        self.previous_topics = current_topics

        return {
            "timestamp": timestamp.isoformat(),
            "current_topics": current_topics,
            "changes": changes,
            "action": self._determine_action(changes)
        }

    def _detect_changes(
        self,
        current_topics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """检测主题变化"""
        if not self.previous_topics:
            return {
                "status": "initial",
                "new_topics": [t["topic_id"] for t in current_topics],
                "disappeared_topics": [],
                "similar_topics": []
            }

        # 比较主题
        current_topic_ids = {t["topic_id"] for t in current_topics}
        previous_topic_ids = {t["topic_id"] for t in self.previous_topics}

        new_topics = current_topic_ids - previous_topic_ids
        disappeared_topics = previous_topic_ids - current_topic_ids
        common_topics = current_topic_ids & previous_topic_ids

        # 检测相似主题
        similar_topics = []
        for new_topic_id in new_topics:
            new_topic = next(
                (t for t in current_topics if t["topic_id"] == new_topic_id),
                None
            )

            for old_topic in self.previous_topics:
                similarity = self._calculate_topic_similarity(new_topic, old_topic)

                if similarity >= self.similarity_threshold:
                    similar_topics.append({
                        "new_topic_id": new_topic_id,
                        "old_topic_id": old_topic["topic_id"],
                        "similarity": similarity
                    })

        # 判断变化类型
        if not new_topics and not disappeared_topics:
            status = "stable"
        elif len(new_topics) > len(disappeared_topics):
            status = "expanding"
        elif len(new_topics) < len(disappeared_topics):
            status = "contracting"
        else:
            status = "changing"

        return {
            "status": status,
            "new_topics": list(new_topics),
            "disappeared_topics": list(disappeared_topics),
            "similar_topics": similar_topics,
            "topic_count_change": len(current_topics) - len(self.previous_topics)
        }

    def _calculate_topic_similarity(
        self,
        topic1: Dict[str, Any],
        topic2: Dict[str, Any]
    ) -> float:
        """计算两个主题的相似度"""
        words1 = set(topic1.get("words", []))
        words2 = set(topic2.get("words", []))

        if not words1 or not words2:
            return 0.0

        # Jaccard相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _determine_action(self, changes: Dict[str, Any]) -> str:
        """确定需要的操作"""
        status = changes["status"]

        if status == "initial":
            return "initialize_knowledge_graph"
        elif status == "expanding" or status == "changing":
            # 有新主题出现，需要触发局部重抽
            return "trigger_partial_extraction"
        elif status == "stable":
            # 主题稳定，无需操作
            return "no_action"
        else:
            return "monitor"

    def get_topic_evolution(self) -> List[Dict[str, Any]]:
        """获取主题演化历史"""
        return self.topic_history

    def get_drift_report(self) -> Dict[str, Any]:
        """生成主题漂移报告"""
        if not self.topic_history:
            return {"status": "no_data"}

        # 统计变化
        total_changes = 0
        new_topics_count = 0
        disappeared_topics_count = 0

        for snapshot in self.topic_history:
            changes = snapshot.get("changes", {})
            if changes.get("status") != "initial":
                total_changes += 1
                new_topics_count += len(changes.get("new_topics", []))
                disappeared_topics_count += len(changes.get("disappeared_topics", []))

        return {
            "total_snapshots": len(self.topic_history),
            "total_changes": total_changes,
            "total_new_topics": new_topics_count,
            "total_disappeared_topics": disappeared_topics_count,
            "current_topic_count": len(self.topic_history[-1].get("topics", [])),
            "last_change": self.topic_history[-1].get("changes", {})
        }
