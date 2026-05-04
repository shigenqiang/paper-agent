r"""
Local Embedding Module - 本地Qwen3嵌入模型

集成 D:\Qwen3_model\Qwen3-Embedding-0.6B 本地模型，
当云API不可用时提供本地嵌入能力。
"""

from .local_embedding import LocalEmbeddingModel, get_local_embedding_model

__all__ = ["LocalEmbeddingModel", "get_local_embedding_model"]
