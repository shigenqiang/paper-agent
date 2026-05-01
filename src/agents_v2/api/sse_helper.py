"""
SSE (Server-Sent Events) Helper for aiohttp

Provides SSE streaming support for long-running LLM operations.
"""
import json
import asyncio
import time
import logging
from typing import Any, AsyncIterator, Optional
from aiohttp import web

logger = logging.getLogger(__name__)


class SSEResponse(web.StreamResponse):
    """
    SSE流式响应

    使用示例:
        async def handler(request):
            sse = SSEResponse(request)
            await sse.start()
            await sse.send_event("token", {"text": "Hello"})
            await sse.send_event("complete", {"status": "done"})
            return sse
    """

    def __init__(self, request: web.Request, heartbeat_interval: float = 15.0):
        super().__init__(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            }
        )
        self._request = request
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._closed = False

    async def start(self) -> web.StreamResponse:
        """启动SSE连接"""
        resp = await super().prepare(self._request)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        return resp

    async def send_event(self, event: str, data: Any = None, event_id: Optional[str] = None) -> None:
        """发送SSE事件"""
        if self._closed:
            return

        lines = []
        if event_id:
            lines.append(f"id: {event_id}")
        lines.append(f"event: {event}")

        if data is not None:
            if isinstance(data, (dict, list)):
                payload = json.dumps(data, ensure_ascii=False)
            else:
                payload = str(data)
            for line in payload.split('\n'):
                lines.append(f"data: {line}")
        else:
            lines.append("data: ")

        lines.append("")  # 空行分隔
        lines.append("")  # SSE规范要求两个换行

        try:
            await self.write(('\n'.join(lines)).encode('utf-8'))
        except (ConnectionResetError, ConnectionError):
            self._closed = True

    async def send_token(self, token: str) -> None:
        """发送token（快捷方法）"""
        await self.send_event("token", {"text": token})

    async def send_phase(self, phase: str, status: str = "start", detail: str = "") -> None:
        """发送阶段事件"""
        await self.send_event("phase", {
            "phase": phase,
            "status": status,
            "detail": detail,
            "timestamp": time.time(),
        })

    async def send_error(self, error: str) -> None:
        """发送错误事件"""
        await self.send_event("error", {"error": error})

    async def send_complete(self, data: Any = None) -> None:
        """发送完成事件"""
        await self.send_event("complete", data or {"status": "done"})
        await self.close()

    async def close(self) -> None:
        """关闭SSE连接"""
        self._closed = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        try:
            await super().write_eof()
        except Exception:
            pass

    async def _heartbeat_loop(self) -> None:
        """心跳保活"""
        try:
            while not self._closed:
                await asyncio.sleep(self._heartbeat_interval)
                if not self._closed:
                    try:
                        await self.write(b": heartbeat\n\n")
                    except (ConnectionResetError, ConnectionError):
                        self._closed = True
                        break
        except asyncio.CancelledError:
            pass


async def stream_llm_tokens(
    sse: SSEResponse,
    llm_call_fn,
    *args,
    **kwargs,
) -> Any:
    """
    流式调用LLM并通过SSE发送token

    Args:
        sse: SSE响应对象
        llm_call_fn: LLM调用函数，需支持流式返回
        *args, **kwargs: 传递给LLM的参数

    Returns:
        完整的LLM响应结果
    """
    full_content = []

    try:
        if hasattr(llm_call_fn, '__aiter__'):
            # 异步迭代器（流式）
            async for chunk in llm_call_fn:
                content = getattr(chunk, 'content', str(chunk))
                if content:
                    full_content.append(content)
                    await sse.send_token(content)
        else:
            # 普通异步函数（非流式），模拟token输出
            result = await llm_call_fn(*args, **kwargs)
            content = str(result) if result else ""
            # 分块发送模拟流式体验
            chunk_size = 20
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                full_content.append(chunk)
                await sse.send_token(chunk)
                await asyncio.sleep(0.02)  # 模拟延迟

    except Exception as e:
        logger.error(f"SSE stream error: {e}")
        await sse.send_error(str(e))
        raise

    return "".join(full_content)
