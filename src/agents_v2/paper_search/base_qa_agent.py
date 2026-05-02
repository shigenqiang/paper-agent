"""统计学问答Agent基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class QuestionType(str, Enum):
    """问题类型枚举"""
    BASIC_QUERY = "basic_query"           # 基础查询（直接回答）
    PROFESSIONAL = "professional"          # 专业问题（需搜索论文）
    FRONTIER = "frontier"                  # 前沿探索（搜索最新论文）
    APPLICATION = "application"           # 应用咨询（搜索案例）


@dataclass
class RoutingDecision:
    """路由决策"""
    question_type: QuestionType
    confidence: float = 1.0
    reasoning: str = ""
    suggested_path: str = ""  # knowledge_base, paper_search, llm_enhanced
    filters: Dict[str, Any] = field(default_factory=dict)  # 搜索过滤器


class BaseQAAgent(ABC):
    """
    统计学问答Agent基类

    提供:
    - 问题类型判断
    - 路由决策
    - LLM调用封装
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.logger = get_logging_logger(f"QA.{name}")

    @abstractmethod
    async def execute(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行问答

        Args:
            question: 用户问题
            context: 上下文信息

        Returns:
            回答结果字典
        """
        pass

    def parse_routing_decision(self, llm_output: str) -> RoutingDecision:
        """解析LLM输出的路由决策"""
        import json
        try:
            # 尝试解析JSON
            data = json.loads(llm_output)
            return RoutingDecision(
                question_type=QuestionType(data.get("question_type", "professional")),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                suggested_path=data.get("suggested_path", "paper_search"),
                filters=data.get("filters", {})
            )
        except json.JSONError:
            # 降级处理
            return RoutingDecision(
                question_type=QuestionType.PROFESSIONAL,
                confidence=0.5,
                reasoning=llm_output,
                suggested_path="paper_search"
            )

    async def _llm_call(self, prompt: str, system_prompt: str = "") -> str:
        """LLM调用封装（简化版，不依赖BaseAgent）"""
        from langchain_openai import ChatOpenAI
        import os

        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.chat/v1")
        model = os.getenv("LLM_MODEL", "MiniMax-M2.7")

        llm = ChatOpenAI(
            model=model,
            temperature=0.3,
            api_key=api_key,
            base_url=base_url if base_url else None
        )

        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=system_prompt or "你是一个专业的统计学问答助手。"),
            HumanMessage(content=prompt)
        ]

        try:
            response = await llm.ainvoke(messages)
            return response.content
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise