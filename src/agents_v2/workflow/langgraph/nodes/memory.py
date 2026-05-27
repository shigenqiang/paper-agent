"""
Memory Integration Node - LangGraph 工作流记忆节点

将 UnifiedMemoryManager 集成到 LangGraph 工作流，
在检索前召回历史记忆，在筛选后记住检索结果。
"""

import asyncio
import time
from typing import List, Optional

from ...core.memory.unified import UnifiedMemoryManager, get_memory_manager
from ...core.memory.types import MemoryType, MemoryEntry
from ..state import PaperAgentState
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


class MemoryNode:
    """记忆管理节点 - LangGraph 节点

    在工作流中提供：
    1. 检索前：召回相关历史记忆，增强查询
    2. 筛选后：记住本次检索结果
    """

    def __init__(
        self,
        memory_manager: Optional[UnifiedMemoryManager] = None,
        storage_path: str = ".memory",
    ):
        """
        Args:
            memory_manager: 已有的记忆管理器实例（可选）
            storage_path: 存储路径（未提供 memory_manager 时使用）
        """
        if memory_manager:
            self.memory_manager = memory_manager
        else:
            self.memory_manager = get_memory_manager()

    def _get_or_create_loop(self):
        """获取或创建事件循环"""
        try:
            # 首先尝试获取运行中的循环
            loop = asyncio.get_running_loop()
            # 如果有运行中的循环，不能使用 run_until_complete
            raise RuntimeError("Cannot use run_until_complete in running loop")
        except RuntimeError as e:
            if "Cannot use" in str(e):
                # 运行中的循环存在，抛出异常让调用者处理
                raise
            # 如果是"no running event loop"，创建新循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def recall_before_search(self, state: PaperAgentState) -> PaperAgentState:
        """检索前召回相关记忆，增强查询

        将相关历史记忆附加到用户查询中，提供更丰富的上下文。
        触发条件：
        1. 用户问题涉及"之前"、"上次"等历史关键词
        2. 用户问题涉及具体实体或任务

        v4.0改进：
        - 使用 recall_with_decay() 带遗忘曲线的时间衰减召回
        - 重要性阈值过滤
        - 基于Ebbinghaus公式的保留分数排序
        """
        user_id = state.user_id or "anonymous"
        query = state.user_query

        if not user_id:
            return state

        # 智能触发判断 - 检查是否需要召回记忆
        if not self._should_recall_memories(query):
            logger.debug(f"[Memory] 查询 '{query}' 不需要召回记忆，跳过")
            return state

        # 召回相关记忆（带遗忘曲线衰减）
        try:
            loop = self._get_or_create_loop()
        except RuntimeError as e:
            logger.debug(f"[Memory] 事件循环已在运行，跳过记忆召回")
            return state

        try:
            recalled = loop.run_until_complete(
                self.memory_manager.recall_with_decay(
                    query=query,
                    top_k=3,
                    enable_decay=True
                )
            )
        except Exception as e:
            logger.warning(f"记忆召回失败: {e}")
            return state

        if recalled:
            memory_context = "\n\nRelated previous knowledge (with forgetting decay):\n"
            for mem in recalled:
                importance = getattr(mem, 'importance', 0.5)
                retention = mem.retention_score() if hasattr(mem, 'retention_score') else 1.0
                memory_context += f"- {mem.content} (importance: {importance:.2f}, retention: {retention:.2f})\n"

            # 增强查询
            enhanced_query = query + memory_context
            state["user_query"] = enhanced_query
            state["metadata"] = {
                **state.get("metadata", {}),
                "recalled_memories": len(recalled),
                "original_query": query,
                "recall_with_decay": True,
            }

            logger.info(f"[Memory] 为 {user_id} 召回 {len(recalled)} 条历史记忆 (with decay)")

        return state

    def _should_recall_memories(self, query: str) -> bool:
        """判断是否需要召回记忆

        触发条件：
        1. 问题涉及历史上下文关键词
        2. 问题涉及具体实体（人名、项目名等）

        Args:
            query: 用户查询

        Returns:
            是否应该召回记忆
        """
        # 触发条件1: 历史关键词
        history_keywords = [
            "之前", "上次", "之前那个", "上次那个",
            "以前", "曾经", "之前你", "上次我",
            "还记得", "之前提到", "上次说的"
        ]

        for keyword in history_keywords:
            if keyword in query:
                logger.debug(f"[Memory] 检测到历史关键词: {keyword}")
                return True

        # 触发条件2: 项目相关名词（如果之前有相关记忆，可能需要加载）
        # 这个可以通过检查记忆是否存在来判断，但会增加一次存储查询
        # 暂时跳过，后续可以根据需要启用

        # 默认不触发（除非有明确的历史引用）
        return False

    def remember_after_selection(self, state: PaperAgentState) -> PaperAgentState:
        """筛选后记住检索结果

        将本次筛选的高质量论文添加到记忆中，作为未来的知识积累。
        """
        # 处理 dict 和 PaperAgentState 两种类型
        if isinstance(state, dict):
            user_id = state.get("user_id") or "anonymous"
            query = state.get("user_query", "")
            papers = state.get("selected_papers") or state.get("papers") or []
        else:
            user_id = state.user_id or "anonymous"
            query = state.user_query
            papers = state.selected_papers or state.papers

        if not user_id or not papers:
            return state

        try:
            loop = self._get_or_create_loop()
        except RuntimeError as e:
            logger.debug(f"[Memory] 事件循环已在运行，跳过记忆存储: {e}")
            return state

        # 记住 Top 5 论文
        remember_count = 0
        for paper in papers[:5]:
            # 处理 dict 和对象两种格式
            if isinstance(paper, dict):
                paper_title = paper.get("title", "")
                paper_abstract = paper.get("abstract", "")[:200] if paper.get("abstract") else ""
                paper_id = paper.get("id", f"paper_{remember_count}")
                paper_relevance = paper.get("relevance_score", 0.5)
            else:
                paper_title = getattr(paper, 'title', "")
                paper_abstract = getattr(paper, 'abstract', "")[:200] if getattr(paper, 'abstract', None) else ""
                paper_id = getattr(paper, 'id', f"paper_{remember_count}")
                paper_relevance = getattr(paper, 'relevance_score', 0.5)

            paper_content = f"Title: {paper_title}. Abstract: {paper_abstract}"
            importance = min(paper_relevance * 2, 1.0)

            try:
                loop.run_until_complete(
                    self.memory_manager.remember(
                        key=f"paper_{paper_id}" if paper_id else f"paper_{remember_count}",
                        value=paper_content,
                        memory_type=MemoryType.LONG_TERM,
                        persist=True,
                        importance=importance,
                        tags=["paper", "research", query[:50] if query else "unknown"],
                        metadata={
                            "user_id": user_id,
                            "query": query,
                            "title": paper_title or "unknown",
                        }
                    )
                )
                remember_count += 1
            except Exception as e:
                logger.debug(f"记忆存储失败: {e}")

        logger.info(f"[Memory] 为 {user_id} 记住 {remember_count} 篇检索结果论文")

        state["metadata"] = {
            **state.get("metadata", {}),
            "remembered_papers": remember_count,
        }

        return state

    def personalize_output(self, state: PaperAgentState) -> PaperAgentState:
        """个性化输出（已简化）

        基于用户偏好生成个性化响应。
        注意：当 UnifiedMemoryManager 不支持时，保留接口但返回原状态。
        """
        user_id = state.user_id or "anonymous"
        draft = state.draft

        if not user_id or not draft:
            return state

        # 尝试获取用户画像进行个性化
        try:
            loop = self._get_or_create_loop()
        except RuntimeError as e:
            logger.debug(f"[Memory] 事件循环已在运行，跳过个性化输出")
            return state

        try:
            user_profile = loop.run_until_complete(
                self.memory_manager.get_user_profile(user_id)
            )

            if user_profile:
                # 如果有用户偏好，可以在draft上添加标注
                state["metadata"] = {
                    **state.get("metadata", {}),
                    "personalized": True,
                    "user_profile_loaded": True,
                }
                logger.info(f"[Memory] 为 {user_id} 加载用户画像，包含 {len(user_profile)} 项偏好")
        except Exception as e:
            logger.debug(f"个性化输出失败: {e}")

        return state


def create_memory_node(
    memory_manager: Optional[UnifiedMemoryManager] = None,
    storage_path: str = ".memory",
) -> MemoryNode:
    """便捷函数：创建记忆节点"""
    return MemoryNode(
        memory_manager=memory_manager,
        storage_path=storage_path,
    )