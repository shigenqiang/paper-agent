"""
文本嵌入
Text Embedding
"""

from typing import List, Dict, Optional, Any, Union
import numpy as np


class TextEmbedder:
    """文本嵌入器"""

    def __init__(
        self,
        model_name: str = "bge-m3",
        embedding_dim: int = 256,
        normalize: bool = True
    ):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.normalize = normalize

        self.model = None
        self.tokenizer = None
        self._initialized = False

        self._init_model()

    def _init_model(self):
        """初始化模型"""
        try:
            if "bge" in self.model_name.lower():
                self._init_bge_model()
            elif "openai" in self.model_name.lower():
                self._init_openai_model()
            else:
                # 使用基础TF-IDF作为fallback
                self._init_tfidf_model()
        except Exception as e:
            print(f"Failed to initialize embedding model: {e}")
            self._init_tfidf_model()

    def _init_bge_model(self):
        """初始化BGE模型"""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.model.eval()

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)

            self._initialized = True
        except Exception as e:
            print(f"Failed to load BGE model: {e}")
            self._init_tfidf_model()

    def _init_openai_model(self):
        """初始化OpenAI模型"""
        try:
            import openai
            self.client = openai.OpenAI()
            self._initialized = True
        except Exception as e:
            print(f"Failed to initialize OpenAI client: {e}")
            self._init_tfidf_model()

    def _init_tfidf_model(self):
        """初始化TF-IDF作为fallback"""
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=self.embedding_dim,
            stop_words='english'
        )
        self.tfidf_fitted = False
        self._initialized = True

    def embed_text(self, text: str) -> np.ndarray:
        """嵌入单个文本"""
        if not text:
            return np.zeros(self.embedding_dim)

        if self.tokenizer and self.model:
            return self._embed_with_transformers(text)
        elif hasattr(self, 'client'):
            return self._embed_with_openai(text)
        else:
            return self._embed_with_tfidf([text])[0]

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """嵌入多个文本"""
        if not texts:
            return [np.zeros(self.embedding_dim)]

        if self.tokenizer and self.model:
            return self._embed_with_transformers_batch(texts)
        elif hasattr(self, 'client'):
            return self._embed_with_openai_batch(texts)
        else:
            return self._embed_with_tfidf(texts)

    def _embed_with_transformers(self, text: str) -> np.ndarray:
        """使用transformers模型嵌入"""
        import torch

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            # 使用[CLS]token的输出
            embedding = outputs.last_hidden_state[0, 0].cpu().numpy()

        if self.normalize:
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)

        return embedding

    def _embed_with_transformers_batch(
        self,
        texts: List[str]
    ) -> List[np.ndarray]:
        """批量使用transformers嵌入"""
        import torch

        embeddings = []

        for i in range(0, len(texts), 8):  # 批量大小8
            batch = texts[i:i + 8]

            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                batch_embeddings = outputs.last_hidden_state[:, 0].cpu().numpy()

            for emb in batch_embeddings:
                if self.normalize:
                    emb = emb / (np.linalg.norm(emb) + 1e-8)
                embeddings.append(emb)

        return embeddings

    def _embed_with_openai(self, text: str) -> np.ndarray:
        """使用OpenAI嵌入"""
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text
        )

        embedding = response.data[0].embedding

        if self.normalize:
            embedding = np.array(embedding)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)

        return np.array(embedding)

    def _embed_with_openai_batch(self, texts: List[str]) -> List[np.ndarray]:
        """批量使用OpenAI嵌入"""
        embeddings = []

        for i in range(0, len(texts), 100):  # OpenAI批量限制
            batch = texts[i:i + 100]

            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch
            )

            for emb_data in response.data:
                emb = np.array(emb_data.embedding)

                if self.normalize:
                    emb = emb / (np.linalg.norm(emb) + 1e-8)

                embeddings.append(emb)

        return embeddings

    def _embed_with_tfidf(self, texts: List[str]) -> List[np.ndarray]:
        """使用TF-IDF嵌入"""
        if not self.tfidf_fitted:
            self.tfidf_vectorizer.fit(texts)
            self.tfidf_fitted = True
        else:
            # 增量添加新文本
            self.tfidf_vectorizer.fit(list(texts) + [""])

        embeddings = self.tfidf_vectorizer.transform(texts).toarray()

        # 归一化
        if self.normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            embeddings = embeddings / norms

        return [emb for emb in embeddings]

    def compute_similarity(
        self,
        text1: str,
        text2: str,
        metric: str = "cosine"
    ) -> float:
        """计算两个文本的相似度"""
        emb1 = self.embed_text(text1)
        emb2 = self.embed_text(text2)

        if metric == "cosine":
            dot = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            return dot / (norm1 * norm2 + 1e-8)
        elif metric == "euclidean":
            return -np.linalg.norm(emb1 - emb2)
        else:
            return 0.0

    def find_most_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """查找最相似的文本"""
        query_emb = self.embed_text(query)
        candidate_embs = self.embed_texts(candidates)

        similarities = []
        for i, emb in enumerate(candidate_embs):
            sim = np.dot(query_emb, emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-8
            )
            similarities.append((i, float(sim)))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def get_embedding_dimension(self) -> int:
        """获取嵌入维度"""
        return self.embedding_dim
