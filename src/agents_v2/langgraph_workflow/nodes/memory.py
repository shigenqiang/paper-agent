"""
Memory Integration Node - LangGraph 工作流记忆节点

将 EnhancedMemorySystem 集成到 LangGraph 工作流，
在检索前召回历史记忆，在筛选后记住检索结果，
在最终输出时生成个性化响应。
"""
import logging
from typing import List, Optional

from ...personalization.enhanced_memory_system import (
    EnhancedMemorySystem,
    MemoryContext,
    PersonalizedResponse,
)
from ..state import PaperAgentState

logger = logging.getLogger(__name__)


class MemoryNode:
    """记忆管理节点 - LangGraph 节点

    在工作流中提供：
    1. 检索前：召回相关历史记忆，注入到用户查询中
    2. 筛选后：记住本次检索结果
    3. 输出前：生成个性化响应
    """

    def __init__(
        self,
        memory_system: Optional[EnhancedMemorySystem] = None,
        storage_path: str = ".memory",
    ):
        """
        Args:
            memory_system: 已有的记忆系统实例（可选）
            storage_path: 存储路径（未提供 memory_system 时使用）
        """
        if memory_system:
            self.memory_system = memory_system
        else:
            self.memory_system = EnhancedMemorySystem(
                storage_path=storage_path,
                enable_forgetting_curve=True,
                enable_preference_learning=True,
            )

    def recall_before_search(self, state: PaperAgentState) -> PaperAgentState:
        """检索前召回相关记忆，增强查询

        将相关历史记忆附加到用户查询中，提供更丰富的上下文。
        """
        user_id = state.user_id or "anonymous"
        query = state.user_query

        if not user_id:
            return state

        # 召回相关记忆
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            recalled = loop.run_until_complete(
                self.memory_system.recall(user_id=user_id, query=query, top_k=3)
            )
        except Exception as e:
            logger.warning(f"记忆召回失败: {e}")
            return state

        if recalled:
            memory_context = "\n\nRelated previous knowledge:\n"
            for mem in recalled:
                memory_context += f"- {mem.content} (importance: {mem.importance})\n"

            # 增强查询
            enhanced_query = query + memory_context
            state["user_query"] = enhanced_query
            state["metadata"] = {
                **state.get("metadata", {}),
                "recalled_memories": len(recalled),
                "original_query": query,
            }

            logger.info(f"[Memory] 为 {user_id} 召回 {len(recalled)} 条历史记忆")

        return state

    def remember_after_selection(self, state: PaperAgentState) -> PaperAgentState:
        """筛选后记住检索结果

        将本次筛选的高质量论文添加到记忆中，作为未来的知识积累。
        """
        user_id = state.user_id or "anonymous"
        query = state.user_query
        papers = state.selected_papers or state.papers

        if not user_id or not papers:
            return state

        context = MemoryContext(
            user_id=user_id,
            session_id=state.session_id or "session_default",
            query=query,
        )

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 记住 Top 5 论文
        remember_count = 0
        for paper in papers[:5]:
            paper_content = f"Title: {paper.title}. Abstract: {paper.abstract[:200]}"
            importance = min(paper.relevance_score * 10, 10)  # 转为 1-10 重要性

            try:
                loop.run_until_complete(
                    self.memory_system.remember(
                        user_id=user_id,
                        content=paper_content,
                        importance=importance,
                        context=context,
                    )
                )
                remember_count += 1
            except Exception as e:
                # 跨会话知识存储可能失败，但遗忘曲线记忆仍应成功
                logger.debug(f"记忆存储失败: {e}")
                # 继续尝试直接添加到遗忘曲线记忆
                if self.memory_system.forgetting_memory:
                    self.memory_system.forgetting_memory.add(
                        content=paper_content,
                        importance=importance,
                        metadata={"user_id": user_id, "query": query},
                    )
                    remember_count += 1

        logger.info(f"[Memory] 为 {user_id} 记住 {remember_count} 篇检索结果论文")

        state["metadata"] = {
            **state.get("metadata", {}),
            "remembered_papers": remember_count,
        }

        return state

    def personalize_output(self, state: PaperAgentState) -> PaperAgentState:
        """个性化输出

        基于用户偏好和历史记忆，生成个性化的最终响应。
        """
        user_id = state.user_id or "anonymous"
        query = state.user_query
        draft = state.draft

        if not user_id or not draft:
            return state

        context = MemoryContext(
            user_id=user_id,
            session_id=state.session_id or "session_default",
            query=query,
        )

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            personalized = loop.run_until_complete(
                self.memory_system.get_personalized_response(
                    user_id=user_id,
                    query=query,
                    base_response=draft,
                    context=context,
                )
            )

            state["personalized_draft"] = personalized.content
            state["personalization_style"] = personalized.style
            state["personalization_confidence"] = personalized.confidence
            state["metadata"] = {
                **state.get("metadata", {}),
                "personalized": True,
                "personalization_style": personalized.style,
                "personalization_confidence": personalized.confidence,
            }

            logger.info(
                f"[Memory] 为 {user_id} 生成个性化响应，风格: {personalized.style}, "
                f"置信度: {personalized.confidence:.2f}"
            )
        except Exception as e:
            logger.warning(f"个性化输出失败: {e}")

        return state


def create_memory_node(
    memory_system: Optional[EnhancedMemorySystem] = None,
    storage_path: str = ".memory",
) -> MemoryNode:
    """便捷函数：创建记忆节点"""
    return MemoryNode(
        memory_system=memory_system,
        storage_path=storage_path,
    )
