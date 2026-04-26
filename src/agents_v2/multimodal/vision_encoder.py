"""
视觉编码器 - Vision Encoder

使用CLIP/ViT集成进行图像编码和文本-图像相似度计算。
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    """视觉编码结果"""
    image_embedding: List[float]
    text_embedding: Optional[List[float]] = None
    similarity: Optional[float] = None
    metadata: Dict[str, Any] = None


class VisionEncoder:
    """视觉编码器 - CLIP/ViT集成

    支持:
    - 图像编码
    - 文本编码
    - 图文相似度计算
    """

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """初始化视觉编码器

        Args:
            model_name: CLIP模型名称
        """
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = "cpu"  # 默认CPU
        self._load_model()

    def _load_model(self):
        """加载CLIP模型"""
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model = CLIPModel.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()

            logger.info(f"成功加载CLIP模型: {self.model_name}, 设备: {self.device}")

        except ImportError as e:
            logger.warning(f"缺少必要依赖，使用简单实现: {e}")
            self.model = None
        except Exception as e:
            logger.error(f"加载CLIP模型失败: {e}")
            self.model = None

    def encode_image(self, image: Any) -> List[float]:
        """将图像编码为向量

        Args:
            image: PIL.Image或图像路径

        Returns:
            List[float]: 图像embedding
        """
        if self.model is None:
            return self._encode_simple(image)

        try:
            from PIL import Image
            import torch

            # 加载图像
            if isinstance(image, str):
                image = Image.open(image).convert('RGB')
            elif not isinstance(image, Image.Image):
                raise ValueError("image必须是PIL.Image或图像路径")

            # 编码
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)

            return image_features.cpu().numpy()[0].tolist()

        except Exception as e:
            logger.error(f"图像编码失败: {e}")
            return self._encode_simple(image)

    def encode_text(self, text: str) -> List[float]:
        """将文本编码为向量

        Args:
            text: 文本字符串

        Returns:
            List[float]: 文本embedding
        """
        if self.model is None:
            return self._encode_text_simple(text)

        try:
            import torch

            # 编码
            inputs = self.processor(text=[text], return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)

            return text_features.cpu().numpy()[0].tolist()

        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            return self._encode_text_simple(text)

    def compute_similarity(self, image: Any, text: str) -> float:
        """计算图像与文本的相似度

        Args:
            image: PIL.Image或图像路径
            text: 文本字符串

        Returns:
            float: 相似度分数 (0-1)
        """
        image_feat = np.array(self.encode_image(image))
        text_feat = np.array(self.encode_text(text))

        # 余弦相似度
        norm_image = np.linalg.norm(image_feat)
        norm_text = np.linalg.norm(text_feat)

        if norm_image == 0 or norm_text == 0:
            return 0.0

        similarity = np.dot(image_feat, text_feat) / (norm_image * norm_text)

        # 归一化到0-1
        return float((similarity + 1) / 2)

    def encode_image_batch(self, images: List[Any]) -> List[List[float]]:
        """批量编码图像

        Args:
            images: 图像列表

        Returns:
            List[List[float]]: 图像embedding列表
        """
        return [self.encode_image(img) for img in images]

    def encode_text_batch(self, texts: List[str]) -> List[List[float]]:
        """批量编码文本

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 文本embedding列表
        """
        return [self.encode_text(text) for text in texts]

    def find_similar_images(self,
                           query_text: str,
                           image_list: List[Any],
                           top_k: int = 5) -> List[tuple]:
        """查找最相似的图像

        Args:
            query_text: 查询文本
            image_list: 候选图像列表
            top_k: 返回前k个

        Returns:
            List[tuple]: (图像, 相似度) 列表
        """
        similarities = []

        for i, image in enumerate(image_list):
            try:
                sim = self.compute_similarity(image, query_text)
                similarities.append((i, sim))
            except Exception as e:
                logger.warning(f"计算图像{i}相似度失败: {e}")
                similarities.append((i, 0.0))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        return [(image_list[idx], sim) for idx, sim in similarities[:top_k]]

    def _encode_simple(self, image: Any) -> List[float]:
        """简单的图像编码（无模型时使用）

        基于图像尺寸和简单特征生成伪embedding。
        """
        try:
            from PIL import Image

            if isinstance(image, str):
                image = Image.open(image)

            if not isinstance(image, Image.Image):
                return [0.0] * 512

            # 简单的特征：尺寸、颜色统计
            width, height = image.size
            pixels = list(image.getdata())

            features = [
                width / 1000,
                height / 1000,
                len(pixels) / 10000,
                sum(p[:3] for p in pixels[:100]) / (100 * 255) if pixels else 0
            ]

            # 填充到固定长度
            embedding = features + [0.0] * (512 - len(features))
            return embedding[:512]

        except Exception as e:
            logger.error(f"简单图像编码失败: {e}")
            return [0.0] * 512

    def _encode_text_simple(self, text: str) -> List[float]:
        """简单的文本编码（无模型时使用）

        基于词频和字符统计生成伪embedding。
        """
        # 简单的词袋特征
        words = text.lower().split()
        char_count = len(text)
        word_count = len(words)

        # 使用hash生成伪随机但稳定的embedding
        import hashlib

        features = []
        for i in range(512):
            hash_input = f"{text}_{i}".encode()
            hash_val = int(hashlib.md5(hash_input).hexdigest(), 16) % 1000
            features.append(hash_val / 1000)

        return features


class ImageTextMatcher:
    """图像-文本匹配器"""

    def __init__(self, vision_encoder: VisionEncoder = None):
        """初始化匹配器

        Args:
            vision_encoder: 视觉编码器实例
        """
        self.encoder = vision_encoder or VisionEncoder()

    def match_images_to_query(self,
                             query: str,
                             images: List[Any],
                             threshold: float = 0.5) -> List[Dict]:
        """将图像匹配到查询

        Args:
            query: 查询文本
            images: 候选图像列表
            threshold: 相似度阈值

        Returns:
            List[Dict]: 匹配的图像及其相似度
        """
        results = []

        for i, image in enumerate(images):
            try:
                similarity = self.encoder.compute_similarity(image, query)

                if similarity >= threshold:
                    results.append({
                        "image_index": i,
                        "similarity": similarity,
                        "match": True
                    })
            except Exception as e:
                logger.warning(f"图像{i}匹配失败: {e}")

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results

    def extract_image_tags(self, image: Any, candidate_tags: List[str]) -> List[str]:
        """从候选标签中提取图像相关的标签

        Args:
            image: PIL.Image
            candidate_tags: 候选标签列表

        Returns:
            List[str]: 匹配的标签
        """
        matched = []

        for tag in candidate_tags:
            try:
                similarity = self.encoder.compute_similarity(image, tag)
                if similarity >= 0.5:
                    matched.append(tag)
            except Exception as e:
                logger.warning(f"标签'{tag}'匹配失败: {e}")

        return matched


# 便捷函数
def encode_image(image: Any, model_name: str = "openai/clip-vit-base-patch32") -> List[float]:
    """编码图像的便捷函数

    Args:
        image: PIL.Image或图像路径
        model_name: 模型名称

    Returns:
        List[float]: 图像embedding
    """
    encoder = VisionEncoder(model_name=model_name)
    return encoder.encode_image(image)


def compute_image_text_similarity(image: Any,
                                  text: str,
                                  model_name: str = "openai/clip-vit-base-patch32") -> float:
    """计算图像-文本相似度的便捷函数

    Args:
        image: PIL.Image或图像路径
        text: 文本
        model_name: 模型名称

    Returns:
        float: 相似度
    """
    encoder = VisionEncoder(model_name=model_name)
    return encoder.compute_similarity(image, text)
