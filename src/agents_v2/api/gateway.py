"""
API网关 - API Gateway

统一API入口:
- /v1/agents - Agent管理
- /v1/memories - 记忆管理
- /v1/skills - 技能库
- /v1/audit - 审计日志
- /v1/hitl - 人机协作管理
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class APIEndpoint:
    """API端点定义"""

    def __init__(self,
                 path: str,
                 method: str,
                 handler: Callable,
                 auth_required: bool = True):
        self.path = path
        self.method = method
        self.handler = handler
        self.auth_required = auth_required


@dataclass
class APIRequest:
    """API请求"""
    path: str
    method: str
    headers: Dict[str, str]
    body: Optional[Dict] = None
    params: Dict[str, str] = None


@dataclass
class APIResponse:
    """API响应"""
    status_code: int
    body: Any
    headers: Dict[str, str] = None
    latency_ms: float = 0.0


class APIRouter:
    """API路由器"""

    def __init__(self):
        self._routes: Dict[str, APIEndpoint] = {}
        self._middleware: List[Callable] = []

    def add_route(self, path: str, method: str, handler: Callable, auth: bool = True):
        """添加路由"""
        key = f"{method}:{path}"
        self._routes[key] = APIEndpoint(path, method, handler, auth)
        logger.info(f"注册路由: {method} {path}")

    def add_middleware(self, middleware: Callable):
        """添加中间件"""
        self._middleware.append(middleware)

    async def handle_request(self, request: APIRequest) -> APIResponse:
        """处理请求"""
        start_time = time.time()

        # 匹配路由
        key = f"{request.method}:{request.path}"
        endpoint = self._routes.get(key)

        if not endpoint:
            return APIResponse(
                status_code=404,
                body={"error": "Not Found", "path": request.path},
                latency_ms=(time.time() - start_time) * 1000
            )

        # 执行中间件
        for mw in self._middleware:
            try:
                result = mw(request)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"中间件错误: {e}")

        # 执行处理函数
        try:
            if endpoint.auth_required:
                # 检查认证
                if not self._check_auth(request):
                    return APIResponse(
                        status_code=401,
                        body={"error": "Unauthorized"},
                        latency_ms=(time.time() - start_time) * 1000
                    )

            result = await endpoint.handler(request)

            return APIResponse(
                status_code=200,
                body=result,
                latency_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return APIResponse(
                status_code=500,
                body={"error": str(e)},
                latency_ms=(time.time() - start_time) * 1000
            )

    def _check_auth(self, request: APIRequest) -> bool:
        """检查认证"""
        auth_header = request.headers.get("Authorization", "")
        return bool(auth_header)


class APIGateway:
    """API网关

    统一入口，管理所有API路由。
    """

    def __init__(self):
        self.router = APIRouter()
        self._rate_limiter = None
        self._setup_default_routes()

    def _setup_default_routes(self):
        """设置默认路由"""
        # Agent管理
        self.router.add_route("/v1/agents", "POST", self._create_agent)
        self.router.add_route("/v1/agents/{id}", "GET", self._get_agent)
        self.router.add_route("/v1/agents/{id}/execute", "POST", self._execute_agent)

        # 记忆管理
        self.router.add_route("/v1/memories", "GET", self._get_memories)
        self.router.add_route("/v1/memories", "POST", self._create_memory)

        # 技能库
        self.router.add_route("/v1/skills", "GET", self._get_skills)
        self.router.add_route("/v1/skills", "POST", self._create_skill)

        # 审计日志
        self.router.add_route("/v1/audit", "GET", self._get_audit_logs)

        # HITL人机协作
        self.router.add_route("/v1/hitl/pending", "GET", self._get_hitl_pending)
        self.router.add_route("/v1/hitl/respond", "POST", self._respond_hitl)
        self.router.add_route("/v1/hitl/history", "GET", self._get_hitl_history)
        self.router.add_route("/v1/hitl/stats", "GET", self._get_hitl_stats)
        self.router.add_route("/v1/hitl/cancel", "POST", self._cancel_hitl)

    async def _create_agent(self, request: APIRequest) -> Dict:
        """创建Agent"""
        body = request.body or {}
        return {
            "id": "agent_001",
            "name": body.get("name", "unnamed"),
            "created_at": time.time()
        }

    async def _get_agent(self, request: APIRequest) -> Dict:
        """获取Agent"""
        return {
            "id": request.params.get("id", ""),
            "name": "agent_001",
            "status": "active"
        }

    async def _execute_agent(self, request: APIRequest) -> Dict:
        """执行Agent任务"""
        body = request.body or {}
        return {
            "result": f"执行任务: {body.get('task', '')}",
            "status": "completed"
        }

    async def _get_memories(self, request: APIRequest) -> List[Dict]:
        """获取记忆列表"""
        return [{"id": "mem1", "content": "测试记忆"}]

    async def _create_memory(self, request: APIRequest) -> Dict:
        """创建记忆"""
        body = request.body or {}
        return {
            "id": "mem_new",
            "content": body.get("content", ""),
            "created_at": time.time()
        }

    async def _get_skills(self, request: APIRequest) -> List[Dict]:
        """获取技能列表"""
        return [{"id": "skill1", "name": "代码生成"}]

    async def _create_skill(self, request: APIRequest) -> Dict:
        """创建技能"""
        body = request.body or {}
        return {
            "id": "skill_new",
            "name": body.get("name", ""),
            "created_at": time.time()
        }

    async def _get_audit_logs(self, request: APIRequest) -> List[Dict]:
        """获取审计日志"""
        try:
            from ..core.security import SecurityAudit
            if not hasattr(self, '_audit'):
                self._audit = SecurityAudit()
            limit = int(request.params.get("limit", "50"))
            events = self._audit.get_events(limit=limit)
            return [
                {
                    "event_type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
                    "user_id": e.user_id,
                    "ip_address": e.ip_address,
                    "severity": e.severity.value if hasattr(e.severity, 'value') else str(e.severity),
                    "timestamp": e.timestamp,
                }
                for e in events
            ]
        except Exception as e:
            logger.warning(f"Failed to get audit logs: {e}")
            return [{"timestamp": time.time(), "event": "audit_unavailable"}]

    # ---- HITL 人机协作 ----

    async def _get_hitl_pending(self, request: APIRequest) -> Dict:
        """获取待处理的HITL请求"""
        try:
            from ..unified.hitl_manager import get_hitl_manager
            hitl = get_hitl_manager()
            pending = hitl.get_pending_requests()
            return {
                "pending_count": len(pending),
                "requests": [
                    {
                        "request_id": r.request_id,
                        "type": r.intervention_type.value,
                        "agent_id": r.agent_id,
                        "description": r.description,
                        "options": r.options,
                        "priority": r.priority.value,
                        "created_at": r.created_at,
                        "timeout_seconds": r.timeout_seconds,
                    }
                    for r in pending
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get HITL pending: {e}")
            return {"pending_count": 0, "requests": [], "error": str(e)}

    async def _respond_hitl(self, request: APIRequest) -> Dict:
        """响应HITL请求"""
        try:
            from ..unified.hitl_manager import get_hitl_manager
            hitl = get_hitl_manager()
            body = request.body or {}
            request_id = body.get("request_id", "")
            approved = body.get("approved", False)
            selected_option = body.get("selected_option")
            feedback = body.get("feedback", "")
            responder = body.get("responder", "human")

            success = hitl.respond(
                request_id=request_id,
                approved=approved,
                selected_option=selected_option,
                feedback=feedback,
                responder=responder,
            )
            return {"success": success, "request_id": request_id}
        except Exception as e:
            logger.error(f"Failed to respond HITL: {e}")
            return {"success": False, "error": str(e)}

    async def _get_hitl_history(self, request: APIRequest) -> Dict:
        """获取HITL干预历史"""
        try:
            from ..unified.hitl_manager import get_hitl_manager
            hitl = get_hitl_manager()
            limit = int(request.params.get("limit", "50"))
            history = hitl.get_intervention_history(limit=limit)
            return {
                "count": len(history),
                "history": [
                    {
                        "request_id": r.request_id,
                        "approved": r.approved,
                        "feedback": r.feedback,
                        "responder": r.responder,
                        "timestamp": r.timestamp,
                    }
                    for r in history
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get HITL history: {e}")
            return {"count": 0, "history": [], "error": str(e)}

    async def _get_hitl_stats(self, request: APIRequest) -> Dict:
        """获取HITL统计信息"""
        try:
            from ..unified.hitl_manager import get_hitl_manager
            hitl = get_hitl_manager()
            return hitl.get_stats()
        except Exception as e:
            logger.error(f"Failed to get HITL stats: {e}")
            return {"error": str(e)}

    async def _cancel_hitl(self, request: APIRequest) -> Dict:
        """取消HITL请求"""
        try:
            from ..unified.hitl_manager import get_hitl_manager
            hitl = get_hitl_manager()
            body = request.body or {}
            request_id = body.get("request_id")
            if request_id:
                success = hitl.cancel_request(request_id)
                return {"success": success, "request_id": request_id}
            else:
                count = hitl.cancel_all()
                return {"success": True, "cancelled_count": count}
        except Exception as e:
            logger.error(f"Failed to cancel HITL: {e}")
            return {"success": False, "error": str(e)}

    async def handle(self, request: APIRequest) -> APIResponse:
        """处理API请求"""
        return await self.router.handle_request(request)


# 便捷函数
def create_gateway() -> APIGateway:
    """创建API网关"""
    return APIGateway()