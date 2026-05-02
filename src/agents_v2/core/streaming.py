"""
Streaming Support - 流式输出支持

提供LLM响应的流式输出，提升用户体验。
"""
from typing import Any, Callable, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from src.agents_v2.logging_config import get_logging_logger

import asyncio
import time

logger = get_logging_logger(__name__)


class StreamEventType(str, Enum):
    """流事件类型"""
    START = "start"
    TOKEN = "token"
    CHUNK = "chunk"
    COMPLETE = "complete"
    ERROR = "error"
    PHASE_START = "phase_start"
    PHASE_COMPLETE = "phase_complete"


@dataclass
class StreamEvent:
    """流式事件"""
    event_type: StreamEventType
    data: Any = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value if isinstance(self.event_type, Enum) else self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class StreamResponse:
    """
    流式响应对象

    管理流式输出的chunk队列

    使用示例:
        stream = StreamResponse()

        # 写入数据
        await stream.write("Hello")
        await stream.write(" World")

        # 异步读取
        async for chunk in stream:
            print(chunk)
    """

    def __init__(self, stream_id: Optional[str] = None):
        self.stream_id = stream_id or f"stream_{int(time.time()*1000)}"
        self._chunks: List[str] = []
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False
        self._complete_event = asyncio.Event()

    async def write(self, chunk: str) -> None:
        """写入chunk"""
        if self._closed:
            return

        self._chunks.append(chunk)
        await self._queue.put(chunk)

    async def write_event(self, event: StreamEvent) -> None:
        """写入事件"""
        if self._closed:
            return

        await self._queue.put(event)

    async def read(self) -> str:
        """读取下一个chunk"""
        return await self._queue.get()

    async def read_all(self) -> str:
        """读取所有剩余chunk"""
        chunks = []
        while not self._queue.empty():
            try:
                chunk = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                chunks.append(chunk)
            except asyncio.TimeoutError:
                break
        return "".join(chunks)

    def get_full_content(self) -> str:
        """获取完整内容（同步）"""
        return "".join(self._chunks)

    async def close(self) -> None:
        """关闭流"""
        self._closed = True
        self._complete_event.set()

    def is_closed(self) -> bool:
        """检查是否关闭"""
        return self._closed

    async def wait_complete(self) -> None:
        """等待流完成"""
        await self._complete_event.wait()

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if self._closed and self._queue.empty():
            raise StopAsyncIteration
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=30.0)
        except asyncio.TimeoutError:
            if self._closed:
                raise StopAsyncIteration
            raise


class StreamingHandler:
    """
    流式处理器

    管理多个流式响应

    使用示例:
        handler = StreamingHandler()

        # 创建流
        stream = await handler.create_stream("task_1")

        # 添加回调
        handler.on_token("task_1", lambda token: print(token, end=""))

        # 启动流式LLM调用
        await handler.stream_llm_response(prompt, "task_1")
    """

    def __init__(self):
        self._active_streams: Dict[str, StreamResponse] = {}
        self._handlers: Dict[str, Dict[str, Callable]] = {}

    async def create_stream(self, task_id: str) -> StreamResponse:
        """创建流"""
        stream = StreamResponse(stream_id=task_id)
        self._active_streams[task_id] = stream
        self._handlers[task_id] = {}
        return stream

    def get_stream(self, task_id: str) -> Optional[StreamResponse]:
        """获取流"""
        return self._active_streams.get(task_id)

    def on_token(self, task_id: str, handler: Callable[[str], None]) -> None:
        """注册token处理回调"""
        if task_id not in self._handlers:
            self._handlers[task_id] = {}
        self._handlers[task_id]["token"] = handler

    def on_event(self, task_id: str, event_type: StreamEventType, handler: Callable) -> None:
        """注册事件处理回调"""
        if task_id not in self._handlers:
            self._handlers[task_id] = {}
        self._handlers[task_id][event_type.value] = handler

    async def write_to_stream(self, task_id: str, chunk: str) -> None:
        """写入流"""
        stream = self._active_streams.get(task_id)
        if not stream:
            return

        await stream.write(chunk)

        # 触发回调
        handlers = self._handlers.get(task_id, {})
        if "token" in handlers:
            try:
                handlers["token"](chunk)
            except Exception as e:
                logger.warning(f"Token handler error: {e}")

    async def write_event_to_stream(self, task_id: str, event: StreamEvent) -> None:
        """写入事件到流"""
        stream = self._active_streams.get(task_id)
        if not stream:
            return

        await stream.write_event(event)

        # 触发回调
        handlers = self._handlers.get(task_id, {})
        event_key = event.event_type.value if isinstance(event.event_type, Enum) else event.event_type
        if event_key in handlers:
            try:
                handlers[event_key](event)
            except Exception as e:
                logger.warning(f"Event handler error: {e}")

    async def close_stream(self, task_id: str) -> None:
        """关闭流"""
        stream = self._active_streams.get(task_id)
        if stream:
            await stream.close()

        if task_id in self._handlers:
            del self._handlers[task_id]

    async def stream_llm_response(
        self,
        prompt: str,
        task_id: str,
        llm: Any = None,
        model: str = "minimax-m2.7",
        stream_handler: Optional[Callable] = None
    ) -> StreamResponse:
        """
        流式获取LLM响应

        Args:
            prompt: 提示词
            task_id: 任务ID
            llm: LLM实例
            model: 模型名称
            stream_handler: 自定义流处理器

        Returns:
            StreamResponse: 流式响应对象
        """
        stream = await self.create_stream(task_id)

        await stream.write_event(StreamEvent(
            event_type=StreamEventType.START,
            data={"prompt": prompt, "model": model}
        ))

        if llm is None:
            # 没有LLM，发送模拟数据
            asyncio.create_task(self._simulate_stream(stream, prompt))
        else:
            # 使用实际LLM
            asyncio.create_task(self._stream_llm(stream, llm, prompt, model))

        return stream

    async def _simulate_stream(self, stream: StreamResponse, prompt: str) -> None:
        """模拟流式输出（用于测试）"""
        try:
            # 模拟生成过程
            chunks = ["正在", "分析", "请求", "...", "\n\n"]

            for i, chunk in enumerate(chunks):
                await asyncio.sleep(0.1)
                await stream.write(chunk)

            await stream.write_event(StreamEvent(
                event_type=StreamEventType.COMPLETE,
                data={"total_tokens": len(chunks)}
            ))

            await stream.close()

        except Exception as e:
            await stream.write_event(StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": str(e)}
            ))
            await stream.close()

    async def _stream_llm(
        self,
        stream: StreamResponse,
        llm: Any,
        prompt: str,
        model: str
    ) -> None:
        """流式调用LLM"""
        try:
            if hasattr(llm, 'astream'):
                # 异步流式调用
                async for chunk in llm.astream(prompt):
                    content = getattr(chunk, 'content', str(chunk))
                    if content:
                        await stream.write(content)
            elif hasattr(llm, 'stream'):
                # 同步流式调用
                for chunk in llm.stream(prompt):
                    content = getattr(chunk, 'content', str(chunk))
                    if content:
                        await stream.write(content)
            else:
                # 非流式调用，转为流式
                response = await llm.ainvoke(prompt)
                content = getattr(response, 'content', str(response))
                await stream.write(content)

            await stream.write_event(StreamEvent(
                event_type=StreamEventType.COMPLETE,
                data={"status": "complete"}
            ))

            await stream.close()

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            await stream.write_event(StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"error": str(e)}
            ))
            await stream.close()


async def stream_to_async_iterator(stream: StreamResponse) -> AsyncIterator[str]:
    """将StreamResponse转为异步迭代器"""
    async for chunk in stream:
        yield chunk


class PhaseStreamer:
    """
    阶段流式处理器

    在每个阶段完成时立即输出结果
    """

    def __init__(self, handler: Optional[StreamingHandler] = None):
        self.handler = handler or StreamingHandler()

    async def stream_phase(
        self,
        task_id: str,
        phase_name: str,
        execute_fn: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        流式执行阶段

        Args:
            task_id: 任务ID
            phase_name: 阶段名称
            execute_fn: 执行函数

        Returns:
            执行结果
        """
        await self.handler.write_event_to_stream(task_id, StreamEvent(
            event_type=StreamEventType.PHASE_START,
            data={"phase": phase_name}
        ))

        try:
            result = await execute_fn(*args, **kwargs)

            await self.handler.write_event_to_stream(task_id, StreamEvent(
                event_type=StreamEventType.PHASE_COMPLETE,
                data={"phase": phase_name, "success": True}
            ))

            return result

        except Exception as e:
            await self.handler.write_event_to_stream(task_id, StreamEvent(
                event_type=StreamEventType.ERROR,
                data={"phase": phase_name, "error": str(e)}
            ))
            raise


def create_streaming_handler() -> StreamingHandler:
    """创建流式处理器"""
    return StreamingHandler()
