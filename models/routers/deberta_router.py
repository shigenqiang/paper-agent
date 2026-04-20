"""DeBERTa-v3路由器"""
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from typing import Dict, List, Literal
import logging

logger = logging.getLogger(__name__)


class DeBERTaRouter:
    """DeBERTa-v3路由器，决定使用哪个抽取器"""

    def __init__(
        self,
        model_name: str = "microsoft/deberta-v3-base",
        device: str = "cpu",
        simple_threshold: float = 0.3,
        complex_threshold: float = 0.7
    ):
        self.model_name = model_name
        self.device = device
        self.simple_threshold = simple_threshold
        self.complex_threshold = complex_threshold

        logger.info(f"Loading DeBERTa-v3 model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(device)
        self.model.eval()

    def route(
        self,
        text: str
    ) -> Literal["small_model", "llm", "complex"]:
        """
        路由决策
        - small_model: 简单文本，使用小模型
        - llm: 中等复杂度，使用大模型
        - complex: 高复杂度，使用7B大模型并启用Self-Consistency
        """
        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                complexity_score = probabilities[0][1].item()

            logger.debug(f"Complexity score for text: {complexity_score:.4f}")

            if complexity_score < self.simple_threshold:
                return "small_model"
            elif complexity_score < self.complex_threshold:
                return "llm"
            else:
                return "complex"

        except Exception as e:
            logger.error(f"Routing error: {e}")
            return "llm"

    def route_batch(
        self,
        texts: List[str]
    ) -> List[Literal["small_model", "llm", "complex"]]:
        """批量路由"""
        return [self.route(text) for text in texts]

    def get_complexity_score(self, text: str) -> float:
        """获取文本复杂度分数"""
        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                return probabilities[0][1].item()

        except Exception as e:
            logger.error(f"Error calculating complexity score: {e}")
            return 0.5
