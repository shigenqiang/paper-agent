"""
Local Embedding Model - 本地Qwen3嵌入模型

使用本地Qwen3-Embedding-0.6B模型进行文本嵌入，
当云API（ModelScope）不可用时作为后备方案。
"""

import os
import math
from typing import List, Optional

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)

# 模型本地路径（模型文件直接存放在此目录）
MODEL_PATH = os.path.dirname(__file__)


class LocalEmbeddingModel:
    """本地Qwen3嵌入模型

    使用 transformers 加载本地Qwen3-Embedding-0.6B模型，
    提供与云API兼容的嵌入接口。
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        max_length: int = 512
    ):
        """
        Args:
            model_path: 模型路径，默认使用本地Qwen3-Embedding-0.6B
            device: 设备类型，"cpu" 或 "cuda"
            max_length: 最大输入长度
        """
        self.model_path = model_path or MODEL_PATH
        self.device = device
        self.max_length = max_length
        self._model = None
        self._tokenizer = None
        self._dimension = 768  # Qwen3-Embedding-0.6B 维度

    def _load_model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from transformers import AutoModel, AutoTokenizer
                import torch

                self._torch = torch  # 保存torch引用供encode使用

                logger.info(f"Loading local embedding model from {self.model_path}")

                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.model_path,
                    trust_remote_code=True
                )
                self._model = AutoModel.from_pretrained(
                    self.model_path,
                    trust_remote_code=True
                )

                if self.device == "cuda" and torch.cuda.is_available():
                    self._model = self._model.cuda()

                self._model.eval()
                logger.info(f"Local embedding model loaded successfully, dimension: {self._dimension}")

            except ImportError as e:
                logger.error(f"transformers/torch not installed: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to load local embedding model: {e}")
                raise

    def encode(self, texts: List[str], batch_size: int = 8) -> List[List[float]]:
        """
        将文本编码为嵌入向量

        Args:
            texts: 文本列表
            batch_size: 批大小

        Returns:
            嵌入向量列表
        """
        self._load_model()

        if isinstance(texts, str):
            texts = [texts]

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Tokenize
            encoded = self._tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt"
            )

            # Move to device
            if self.device == "cuda":
                encoded = {k: v.cuda() for k, v in encoded.items()}

            # Forward pass
            with self._torch.no_grad():
                outputs = self._model(**encoded)

            # Mean pooling
            attention_mask = encoded["attention_mask"]
            token_embeddings = outputs.last_hidden_state

            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            sum_embeddings = self._torch.sum(token_embeddings * input_mask_expanded, dim=1)
            sum_mask = self._torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
            embeddings = sum_embeddings / sum_mask

            # L2 normalize
            norms = self._torch.norm(embeddings, p=2, dim=1, keepdim=True)
            embeddings = embeddings / norms

            all_embeddings.extend(embeddings.cpu().numpy().tolist())

        return all_embeddings

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取单个文本的嵌入向量

        Args:
            text: 输入文本

        Returns:
            嵌入向量或None（如果失败）
        """
        try:
            embeddings = self.encode([text])
            return embeddings[0] if embeddings else None
        except Exception as e:
            logger.debug(f"Local embedding failed: {e}")
            return None

    @property
    def dimension(self) -> int:
        """嵌入向量维度"""
        return self._dimension

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


# 全局实例
_local_model_instance: Optional[LocalEmbeddingModel] = None


def get_local_embedding_model(
    model_path: Optional[str] = None,
    device: str = "cpu"
) -> LocalEmbeddingModel:
    """
    获取本地嵌入模型单例

    Args:
        model_path: 模型路径
        device: 设备类型

    Returns:
        LocalEmbeddingModel实例
    """
    global _local_model_instance

    if _local_model_instance is None:
        _local_model_instance = LocalEmbeddingModel(
            model_path=model_path,
            device=device
        )

    return _local_model_instance
