"""Memory 系统接入 - 将记忆系统集成到主流水线"""
import logging
from typing import Dict, Any, Optional, List

from src.memory.memory_manager import UnifiedMemoryManager
from src.memory.semantic_memory import MemoryType

logger = logging.getLogger(__name__)

# 全局 Memory Manager 实例
_memory_manager: Optional[UnifiedMemoryManager] = None


def get_memory_manager() -> UnifiedMemoryManager:
    """获取或创建 Memory Manager 单例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = UnifiedMemoryManager(
            storage_dir="./data/memory",
            embedding_service=None
        )
    return _memory_manager


async def memory_retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Memory检索节点 - 在查询开始前检索历史经验

    从长期记忆系统中检索相关的历史研究经验，
    帮助：
    1. 避免重复搜索相同主题
    2. 利用之前的分析结果
    3. 发现相关研究趋势
    """
    query = state.get("query", "")
    if not query:
        return state

    try:
        memory = get_memory_manager()

        # 检索相关记忆
        results = await memory.retrieve(
            query=query,
            top_k=5,
            include_short_term=False
        )

        if results:
            similar_research = []
            for r in results:
                similar_research.append({
                    "content": r.content,
                    "score": r.score,
                    "source": r.source
                })

            state["similar_research"] = similar_research
            logger.info(f"Memory retrieve: found {len(results)} similar memories")

            # 如果有非常相似的研究，可以跳过搜索或调整查询
            high_score_count = sum(1 for r in results if r.score > 0.8)
            if high_score_count >= 2:
                state["skip_search"] = True
                state["use_cached_results"] = True
                logger.info(f"High similarity found ({high_score_count}), considering cached results")

        else:
            state["similar_research"] = []
            logger.info("Memory retrieve: no similar memories found")

        return state

    except Exception as e:
        logger.error(f"Memory retrieve failed: {e}")
        return state


async def memory_store_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Memory存储节点 - 将研究结果存储到记忆系统

    存储内容：
    1. 研究主题和查询
    2. 发现的主题聚类
    3. 研究空白和矛盾
    4. 重要论文信息
    """
    try:
        memory = get_memory_manager()

        query = state.get("query", "")
        if not query:
            return state

        # 存储研究主题
        memory.add_insight(
            insight=f"研究主题: {query}",
            importance=0.8,
            source="research_pipeline"
        )

        # 存储主题聚类
        themes = state.get("themes", [])
        for theme in themes:
            theme_name = theme.get("name", theme.get("theme_description", "未知主题"))
            memory.add_semantic_memory(
                content=f"主题: {theme_name}",
                memory_type=MemoryType.CONCEPT,
                importance=0.7,
                tags=["research_theme", query],
                source="analysis_node"
            )

        # 存储研究空白
        research_gaps = state.get("research_gaps", [])
        for gap in research_gaps:
            memory.add_semantic_memory(
                content=f"研究空白: {gap}",
                memory_type=MemoryType.INSIGHT,
                importance=0.8,
                tags=["research_gap", query],
                source="analysis_node"
            )

        # 存储论文元数据
        papers = state.get("papers", [])
        for paper in papers[:10]:  # 只存储前10篇
            if isinstance(paper, dict):
                title = paper.get("title", "")
                if title:
                    memory.add_semantic_memory(
                        content=f"论文: {title}",
                        memory_type=MemoryType.REFERENCE,
                        importance=0.6,
                        tags=["paper", query],
                        source="search_node"
                    )

        # 持久化
        memory.save_all()

        logger.info(f"Memory store: stored research results for '{query}'")

        return state

    except Exception as e:
        logger.error(f"Memory store failed: {e}")
        return state


async def session_start_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    会话开始节点 - 创建新的研究会话

    初始化会话记忆，为后续的对话管理做准备
    """
    try:
        memory = get_memory_manager()
        session_id = state.get("session_id", "default")

        # 创建或获取会话
        memory.create_session(session_id)

        # 添加用户查询到会话
        query = state.get("query", "")
        if query:
            memory.add_message(
                session_id=session_id,
                role="user",
                content=query
            )

        state["session_id"] = session_id
        logger.info(f"Session started: {session_id}")

        return state

    except Exception as e:
        logger.error(f"Session start failed: {e}")
        return state


async def session_end_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    会话结束节点 - 关闭研究会话

    将短期记忆整合到长期记忆，然后关闭会话
    """
    try:
        memory = get_memory_manager()
        session_id = state.get("session_id", "default")

        # 关闭会话（自动保存到长期记忆）
        memory.close_session(session_id, save=True)

        logger.info(f"Session ended: {session_id}")

        return state

    except Exception as e:
        logger.error(f"Session end failed: {e}")
        return state