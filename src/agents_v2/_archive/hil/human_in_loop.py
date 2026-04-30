"""
Human-In-the-Loop (HIL) - 人机交互

提供人类干预机制，让用户在关键决策点介入。
"""
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class InterventionType(str, Enum):
    """干预类型"""
    APPROVAL = "approval"       # 审批请求
    CORRECTION = "correction"   # 纠正错误
    SELECTION = "selection"     # 选择选项
    CONFIRMATION = "confirmation"  # 确认操作
    FEEDBACK = "feedback"       # 提供反馈


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


class HumanInTheLoop:
    """
    人机交互控制器

    功能:
    - 在关键点暂停等待人类输入
    - 支持多种干预类型
    - 超时处理
    - 干预历史记录

    使用示例:
        hil = HumanInTheLoop()

        # 注册处理器
        hil.register_handler(lambda req: input(f"Approve? {req.description}"))

        # 请求干预
        response = await hil.request_intervention(
            intervention_type=InterventionType.APPROVAL,
            description="确认提交论文?"
        )
    """

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
        """
        注册干预处理器

        Args:
            handler: 处理函数，接收InterventionRequest，返回InterventionResponse
        """
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
        """
        请求人类干预

        Args:
            intervention_type: 干预类型
            agent_id: 请求干预的Agent ID
            description: 干预描述
            options: 可选项列表
            context: 上下文信息
            priority: 优先级
            timeout_seconds: 超时时间

        Returns:
            InterventionResponse: 干预响应
        """
        request_id = f"hil_{int(time.time() * 1000)}"
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

        # 创建Future用于异步等待响应
        future = asyncio.Future()
        self._response_futures[request_id] = future

        # 发送到处理器
        response = None
        for handler in self._handlers:
            try:
                response = await handler(request)
                if response:
                    break
            except Exception as e:
                logger.warning(f"HIL handler error: {e}")

        # 如果有响应，立即返回
        if response:
            return self._complete_request(request_id, response)

        # 如果启用自动批准且没有处理器，超时后自动批准
        if self.enable_auto_approve and not self._handlers:
            return await self._wait_with_timeout(request_id, timeout)

        # 等待响应
        return await self._wait_with_timeout(request_id, timeout)

    async def _wait_with_timeout(
        self,
        request_id: str,
        timeout_seconds: float
    ) -> InterventionResponse:
        """等待响应，带超时"""
        future = self._response_futures.get(request_id)
        if not future:
            return InterventionResponse(
                request_id=request_id,
                approved=False,
                feedback="Request not found"
            )

        try:
            response = await asyncio.wait_for(future, timeout=timeout_seconds)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Intervention request {request_id} timed out")
            return InterventionResponse(
                request_id=request_id,
                approved=False,
                feedback="Timeout - no response received"
            )

    def respond(
        self,
        request_id: str,
        approved: bool,
        selected_option: Optional[str] = None,
        feedback: str = "",
        responder: str = "human"
    ) -> None:
        """
        响应干预请求（外部调用）

        Args:
            request_id: 请求ID
            approved: 是否批准
            selected_option: 选择的选项
            feedback: 反馈
            responder: 响应者
        """
        response = InterventionResponse(
            request_id=request_id,
            approved=approved,
            selected_option=selected_option,
            feedback=feedback,
            responder=responder
        )

        self._complete_request(request_id, response)

    def _complete_request(
        self,
        request_id: str,
        response: InterventionResponse
    ) -> InterventionResponse:
        """完成请求"""
        # 记录历史
        self._intervention_history.append(response)

        # 清理
        if request_id in self._pending_requests:
            del self._pending_requests[request_id]

        if request_id in self._response_futures:
            future = self._response_futures[request_id]
            if not future.done():
                future.set_result(response)
            del self._response_futures[request_id]

        logger.info(f"Intervention {request_id} completed: approved={approved}")
        return response

    def get_pending_requests(self) -> List[InterventionRequest]:
        """获取待处理的请求"""
        return list(self._pending_requests.values())

    def get_intervention_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[InterventionResponse]:
        """获取干预历史"""
        history = self._intervention_history

        if agent_id:
            # 需要从request获取agent_id，这里简化处理
            pass

        return history[-limit:]

    def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        if request_id in self._pending_requests:
            del self._pending_requests[request_id]

        if request_id in self._response_futures:
            future = self._response_futures[request_id]
            if not future.done():
                future.set_result(InterventionResponse(
                    request_id=request_id,
                    approved=False,
                    feedback="Cancelled"
                ))
            del self._response_futures[request_id]

        return True


class HILMiddleware:
    """
    HIL中间件

    用于包装Agent执行，在关键点自动请求干预
    """

    def __init__(self, hil: HumanInTheLoop):
        self.hil = hil
        self._checkpoint_callbacks: Dict[str, Callable] = {}

    def register_checkpoint(
        self,
        name: str,
        callback: Callable[[], bool]
    ) -> None:
        """
        注册检查点

        Args:
            name: 检查点名称
            callback: 回调函数，返回True表示需要干预
        """
        self._checkpoint_callbacks[name] = callback

    async def execute_with_hil(
        self,
        func: Callable,
        checkpoints: Optional[List[str]] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        带HIL的执行

        Args:
            func: 要执行的函数
            checkpoints: 检查点名称列表
            args, kwargs: 函数参数

        Returns:
            函数执行结果
        """
        # 执行前检查
        if checkpoints:
            for checkpoint_name in checkpoints:
                if checkpoint_name in self._checkpoint_callbacks:
                    callback = self._checkpoint_callbacks[checkpoint_name]
                    if callback():
                        # 需要干预
                        await self.hil.request_intervention(
                            intervention_type=InterventionType.CONFIRMATION,
                            agent_id="middleware",
                            description=f"Checkpoint: {checkpoint_name}"
                        )

        # 执行函数
        result = await func(*args, **kwargs)

        return result


def create_hil(default_timeout: float = 300) -> HumanInTheLoop:
    """创建HIL控制器"""
    return HumanInTheLoop(default_timeout=default_timeout)
