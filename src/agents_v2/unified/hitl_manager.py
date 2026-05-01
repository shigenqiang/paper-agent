"""
Human-In-the-Loop (HITL) Manager - 人机协作管理器

在关键决策点暂停Agent执行，等待人工审核/批准/反馈。
借鉴PaperDebugger Diff补丁 + LangGraph Interrupt模式。
"""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging
import uuid

logger = logging.getLogger(__name__)


class InterventionType(str, Enum):
    """干预类型"""
    APPROVAL = "approval"           # 审批请求
    CORRECTION = "correction"       # 纠正错误
    SELECTION = "selection"         # 选择选项
    CONFIRMATION = "confirmation"   # 确认操作
    FEEDBACK = "feedback"           # 提供反馈


class InterventionPriority(str, Enum):
    """干预优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InterventionRequest:
    """干预请求"""
    request_id: str
    intervention_type: InterventionType
    agent_id: str
    description: str
    options: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: InterventionPriority = InterventionPriority.NORMAL
    timeout_seconds: float = 300
    created_at: float = field(default_factory=time.time)


@dataclass
class InterventionResponse:
    """干预响应"""
    request_id: str
    approved: bool
    selected_option: Optional[str] = None
    feedback: str = ""
    timestamp: float = field(default_factory=time.time)
    responder: str = ""


class HITLManager:
    """
    人机协作管理器

    功能:
    - 5个预定义中断点（大纲后/文献后/每章后/终稿前/低质量时）
    - 异步请求/响应 + 超时处理
    - 干预历史记录
    - 自动批准模式（可选）

    使用示例:
        hitl = HITLManager()

        # 请求干预
        response = await hitl.request_intervention(
            intervention_type=InterventionType.APPROVAL,
            agent_id="outline_agent",
            description="大纲已完成，请确认",
            options=["批准", "需要修改"]
        )

        # 外部响应
        hitl.respond(request_id, approved=True)
    """

    # 预定义中断点
    INTERRUPT_POINTS = {
        "after_outline":    "大纲完成后需人工确认",
        "after_literature": "文献综述完成后需审核",
        "after_section":    "每章节完成后可选审核",
        "before_final":     "终稿前需全面审核",
        "on_low_quality":   "质量评分<阈值时强制中断",
    }

    def __init__(
        self,
        default_timeout: float = 300,
        enable_auto_approve: bool = False
    ):
        self.default_timeout = default_timeout
        self.enable_auto_approve = enable_auto_approve

        self._handlers: List[Callable] = []
        self._pending_requests: Dict[str, InterventionRequest] = {}
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._intervention_history: List[InterventionResponse] = []

    def register_handler(self, handler: Callable) -> None:
        """注册干预处理器"""
        self._handlers.append(handler)

    async def request_intervention(
        self,
        intervention_type: InterventionType,
        agent_id: str,
        description: str,
        options: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: InterventionPriority = InterventionPriority.NORMAL,
        timeout_seconds: Optional[float] = None
    ) -> InterventionResponse:
        """请求人类干预"""
        request_id = f"hil_{uuid.uuid4().hex[:12]}"
        timeout = timeout_seconds or self.default_timeout

        request = InterventionRequest(
            request_id=request_id,
            intervention_type=intervention_type,
            agent_id=agent_id,
            description=description,
            options=options or [],
            context=context or {},
            priority=priority,
            timeout_seconds=timeout
        )

        self._pending_requests[request_id] = request
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._response_futures[request_id] = future

        logger.info(
            f"HITL request {request_id}: type={intervention_type.value}, "
            f"agent={agent_id}, desc={description[:50]}"
        )

        # 发送到已注册的处理器
        for handler in self._handlers:
            try:
                response = await handler(request)
                if response:
                    return self._complete_request(request_id, response)
            except Exception as e:
                logger.warning(f"HITL handler error: {e}")

        # 无处理器时，如果启用自动批准
        if self.enable_auto_approve and not self._handlers:
            return self._complete_request(request_id, InterventionResponse(
                request_id=request_id,
                approved=True,
                feedback="Auto-approved (no handler registered)",
                responder="system"
            ))

        # 等待外部响应（带超时）
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"HITL request {request_id} timed out after {timeout}s")
            return InterventionResponse(
                request_id=request_id,
                approved=False,
                feedback=f"Timeout after {timeout}s - no response received",
                responder="system"
            )

    def respond(
        self,
        request_id: str,
        approved: bool,
        selected_option: Optional[str] = None,
        feedback: str = "",
        responder: str = "human"
    ) -> bool:
        """
        响应干预请求（外部调用）

        Returns:
            True if request was found and responded, False otherwise
        """
        response = InterventionResponse(
            request_id=request_id,
            approved=approved,
            selected_option=selected_option,
            feedback=feedback,
            responder=responder
        )

        if request_id in self._response_futures:
            future = self._response_futures[request_id]
            if not future.done():
                future.set_result(response)
            self._complete_request(request_id, response)
            return True

        logger.warning(f"HITL respond: request {request_id} not found")
        return False

    def _complete_request(
        self,
        request_id: str,
        response: InterventionResponse
    ) -> InterventionResponse:
        """完成请求，记录历史，清理状态"""
        self._intervention_history.append(response)

        self._pending_requests.pop(request_id, None)
        self._response_futures.pop(request_id, None)

        logger.info(
            f"HITL completed {request_id}: approved={response.approved}, "
            f"responder={response.responder}"
        )
        return response

    def get_pending_requests(self) -> List[InterventionRequest]:
        """获取待处理的请求"""
        return list(self._pending_requests.values())

    def get_pending_count(self) -> int:
        """获取待处理请求数量"""
        return len(self._pending_requests)

    def get_intervention_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[InterventionResponse]:
        """获取干预历史"""
        history = self._intervention_history
        return history[-limit:]

    def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        if request_id in self._pending_requests:
            self._pending_requests.pop(request_id, None)

        if request_id in self._response_futures:
            future = self._response_futures[request_id]
            if not future.done():
                future.set_result(InterventionResponse(
                    request_id=request_id,
                    approved=False,
                    feedback="Cancelled by system"
                ))
            self._response_futures.pop(request_id, None)
            return True

        return False

    def cancel_all(self) -> int:
        """取消所有待处理请求，返回取消数量"""
        count = 0
        for request_id in list(self._pending_requests.keys()):
            if self.cancel_request(request_id):
                count += 1
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "pending_count": len(self._pending_requests),
            "history_count": len(self._intervention_history),
            "handlers_count": len(self._handlers),
            "auto_approve": self.enable_auto_approve,
            "default_timeout": self.default_timeout,
            "interrupt_points": list(self.INTERRUPT_POINTS.keys()),
        }


# 全局单例
_global_hitl: Optional[HITLManager] = None


def get_hitl_manager() -> HITLManager:
    """获取全局HITL管理器"""
    global _global_hitl
    if _global_hitl is None:
        _global_hitl = HITLManager()
    return _global_hitl
