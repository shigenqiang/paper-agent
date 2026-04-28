"""
流式生成器 - Streaming Generator

功能:
1. 流式文本生成
2. 流式LLM集成
3. 进度追踪
4. 中断支持

设计原则:
- 高效的流式处理
- 实时进度反馈
- 可中断的生成
"""
import asyncio
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time


class StreamStatus(str, Enum):
    """流状态"""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class StreamChunk:
    """流数据块"""
    content: str
    is_final: bool
    status: StreamStatus
    tokens_generated: int = 0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationProgress:
    """生成进度"""
    status: StreamStatus
    tokens_generated: int
    characters_generated: int
    estimated_total_tokens: Optional[int]
    elapsed_time: float
    tokens_per_second: float
    estimated_remaining_time: Optional[float]


class StreamingGenerator:
    """流式生成器"""

    def __init__(
        self,
        llm_stream_func: Optional[Callable] = None,
        buffer_size: int = 10
    ):
        self.llm_stream_func = llm_stream_func
        self.buffer_size = buffer_size

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stop_tokens: Optional[List[str]] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式生成文本

        Args:
            prompt: 提示词
            max_tokens: 最大生成token数
            temperature: 温度参数
            stop_tokens: 停止token列表

        Yields:
            StreamChunk: 流数据块
        """
        stop_tokens = stop_tokens or []

        yield StreamChunk(
            content="",
            is_final=False,
            status=StreamStatus.STARTING,
            tokens_generated=0
        )

        accumulated_content = ""
        tokens_generated = 0

        try:
            if self.llm_stream_func:
                # 使用LLM流函数
                async for chunk in self.llm_stream_func(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                ):
                    accumulated_content += chunk
                    tokens_generated += 1

                    # 检查停止条件
                    should_stop = any(
                        accumulated_content.endswith(stop)
                        for stop in stop_tokens
                    )

                    yield StreamChunk(
                        content=chunk,
                        is_final=should_stop,
                        status=StreamStatus.RUNNING,
                        tokens_generated=tokens_generated
                    )

                    if should_stop:
                        break

                    if tokens_generated >= max_tokens:
                        break

            else:
                # 模拟流式生成
                words = prompt.split()
                for i, word in enumerate(words[:max_tokens]):
                    await asyncio.sleep(0.01)  # 模拟延迟
                    accumulated_content += word + " "
                    tokens_generated += 1

                    yield StreamChunk(
                        content=word + " ",
                        is_final=False,
                        status=StreamStatus.RUNNING,
                        tokens_generated=tokens_generated
                    )

            # 生成完成
            yield StreamChunk(
                content="",
                is_final=True,
                status=StreamStatus.COMPLETED,
                tokens_generated=tokens_generated
            )

        except asyncio.CancelledError:
            yield StreamChunk(
                content="",
                is_final=True,
                status=StreamStatus.CANCELLED,
                tokens_generated=tokens_generated
            )
            raise

        except Exception as e:
            yield StreamChunk(
                content="",
                is_final=True,
                status=StreamStatus.ERROR,
                tokens_generated=tokens_generated,
                metadata={"error": str(e)}
            )

    async def generate_with_progress(
        self,
        prompt: str,
        **kwargs
    ) -> tuple[str, GenerationProgress]:
        """带进度的流式生成

        Args:
            prompt: 提示词
            **kwargs: 传递给generate的参数

        Returns:
            tuple[str, GenerationProgress]: 完整文本和进度信息
        """
        start_time = time.time()
        accumulated = []
        tokens = 0

        async for chunk in self.generate(prompt, **kwargs):
            if chunk.content:
                accumulated.append(chunk.content)
                tokens = chunk.tokens_generated

        elapsed = time.time() - start_time
        tokens_per_second = tokens / elapsed if elapsed > 0 else 0

        full_text = "".join(accumulated)
        progress = GenerationProgress(
            status=StreamStatus.COMPLETED,
            tokens_generated=tokens,
            characters_generated=len(full_text),
            estimated_total_tokens=None,
            elapsed_time=elapsed,
            tokens_per_second=tokens_per_second,
            estimated_remaining_time=None
        )

        return full_text, progress


class ChunkManager:
    """分块管理器"""

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[str]:
        """将文本分块

        Args:
            text: 待分块的文本
            chunk_size: 块大小
            overlap: 重叠大小

        Returns:
            List[str]: 文本块列表
        """
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.overlap

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            chunks.append(chunk)
            start = end - overlap

        return chunks

    def chunk_by_sentence(
        self,
        text: str,
        max_chunk_size: int = 500
    ) -> List[str]:
        """按句子分块

        Args:
            text: 待分块的文本
            max_chunk_size: 最大块大小

        Returns:
            List[str]: 文本块列表
        """
        # 简单的句子分割
        import re
        sentences = re.split(r'[。！？.!?]+', text)

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_size = len(sentence)

            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size

        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks


# 便捷函数
async def stream_generate(
    prompt: str,
    llm_stream_func: Optional[Callable] = None
) -> AsyncGenerator[StreamChunk, None]:
    """便捷流式生成函数"""
    generator = StreamingGenerator(llm_stream_func=llm_stream_func)
    async for chunk in generator.generate(prompt):
        yield chunk
