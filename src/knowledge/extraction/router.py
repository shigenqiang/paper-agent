"""知识抽取路由器"""
from typing import Literal
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class ExtractionRouter(BaseModel):
    """知识抽取路由器 - 决定使用哪种抽取方法"""

    def __init__(
        self,
        simple_threshold: float = 0.3,
        complex_threshold: float = 0.7,
        use_external_router: bool = True
    ):
        self.simple_threshold = simple_threshold
        self.complex_threshold = complex_threshold
        self.use_external_router = use_external_router
        self._external_router = None

    def set_external_router(self, router):
        """设置外部路由器（如DeBERTa-v3）"""
        self._external_router = router

    def route_by_length(self, text: str) -> Literal["small_model", "llm", "complex"]:
        """
        基于文本长度的简单路由
        - 短文本: 小模型
        - 中等长度: 大模型
        - 长文本: 大模型 + Self-Consistency
        """
        text_length = len(text)

        if text_length < 500:
            return "small_model"
        elif text_length < 2000:
            return "llm"
        else:
            return "complex"

    def route_by_complexity(
        self,
        text: str,
        entity_count: int = 0,
        relation_count: int = 0
    ) -> Literal["small_model", "llm", "complex"]:
        """
        基于复杂度的路由
        - 简单: 小模型
        - 中等: 大模型
        - 复杂: 大模型 + Self-Consistency
        """
        complexity_score = 0.0

        # 文本长度
        text_length = len(text)
        if text_length < 500:
            complexity_score += 0.1
        elif text_length < 2000:
            complexity_score += 0.5
        else:
            complexity_score += 0.8

        # 实体数量
        complexity_score += min(entity_count * 0.1, 0.3)

        # 关系数量
        complexity_score += min(relation_count * 0.1, 0.3)

        # 决策
        if complexity_score < self.simple_threshold:
            return "small_model"
        elif complexity_score < self.complex_threshold:
            return "llm"
        else:
            return "complex"

    def route(self, text: str, **kwargs) -> Literal["small_model", "llm", "complex"]:
        """
        路由决策
        优先使用外部路由器，降级到内部逻辑
        """
        if self.use_external_router and self._external_router:
            try:
                # 调用外部路由器
                result = self._external_router.route(text)
                # 转换结果
                if result == "small_model":
                    return "small_model"
                elif result == "llm":
                    return "llm"
                else:
                    return "complex"
            except Exception as e:
                logger.warning(f"External routing failed: {e}, falling back to internal routing")

        # 降级到内部路由
        return self.route_by_length(text, **kwargs)

    def get_route_statistics(self, routes: list) -> dict:
        """获取路由统计信息"""
        stats = {
            "small_model": routes.count("small_model"),
            "llm": routes.count("llm"),
            "complex": routes.count("complex"),
            "total": len(routes)
        }

        if stats["total"] > 0:
            stats["small_model_pct"] = stats["small_model"] / stats["total"]
            stats["llm_pct"] = stats["llm"] / stats["total"]
            stats["complex_pct"] = stats["complex"] / stats["total"]

        return stats


class ExtractionRequest(BaseModel):
    """抽取请求"""
    text: str = Field(..., description="待抽取的文本")
    extraction_type: str = Field(default="entity", description="抽取类型: entity, relation, both")
    domain: str = Field(default="general", description="领域")
    metadata: dict = Field(default_factory=dict, description="元数据")
