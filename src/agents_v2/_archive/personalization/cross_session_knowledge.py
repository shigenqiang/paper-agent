"""
跨会话知识累积 - Cross Session Knowledge

实现跨会话的知识累积和共享:
- 跨会话上下文保持
- 知识图谱构建
- 长期记忆整合
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str
    content: str
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    importance: float = 5.0  # 1-10
    tags: Set[str] = field(default_factory=set)
    related_entries: List[str] = field(default_factory=list)
    source_type: str = "interaction"  # interaction/document/summary
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self):
        """更新访问时间"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class SessionContext:
    """会话上下文"""
    session_id: str
    user_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    topic: str = ""
    key_points: List[str] = field(default_factory=list)
    knowledge_built: List[str] = field(default_factory=list)  # 知识条目ID列表


class CrossSessionKnowledge:
    """跨会话知识管理系统

    功能:
    1. 知识跨会话累积
    2. 知识图谱构建
    3. 会话上下文恢复
    4. 知识重要性评估
    """

    def __init__(self, user_id: str = "default"):
        """初始化

        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self._knowledge_store: Dict[str, KnowledgeEntry] = {}
        self._sessions: Dict[str, SessionContext] = {}
        self._current_session: Optional[SessionContext] = None
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> entry_ids
        self._topic_index: Dict[str, Set[str]] = defaultdict(set)  # topic -> entry_ids

    def start_session(self, session_id: str, topic: str = "") -> SessionContext:
        """开始新会话

        Args:
            session_id: 会话ID
            topic: 会话主题

        Returns:
            SessionContext: 会话上下文
        """
        self._current_session = SessionContext(
            session_id=session_id,
            user_id=self.user_id,
            topic=topic
        )
        self._sessions[session_id] = self._current_session
        logger.info(f"开始会话: {session_id}, topic={topic}")
        return self._current_session

    def end_session(self) -> Optional[SessionContext]:
        """结束当前会话

        Returns:
            Optional[SessionContext]: 会话上下文
        """
        if self._current_session:
            self._current_session.end_time = time.time()
            session = self._current_session
            self._current_session = None
            logger.info(f"结束会话: {session.session_id}")
            return session
        return None

    def add_knowledge(self,
                      content: str,
                      importance: float = 5.0,
                      tags: List[str] = None,
                      source_type: str = "interaction",
                      metadata: Dict = None) -> KnowledgeEntry:
        """添加知识条目

        Args:
            content: 知识内容
            importance: 重要性 (1-10)
            tags: 标签列表
            source_type: 来源类型
            metadata: 元数据

        Returns:
            KnowledgeEntry: 创建的知识条目
        """
        import uuid

        entry = KnowledgeEntry(
            id=str(uuid.uuid4()),
            content=content,
            session_id=self._current_session.session_id if self._current_session else "",
            importance=importance,
            tags=set(tags) if tags else set(),
            source_type=source_type,
            metadata=metadata or {}
        )

        self._knowledge_store[entry.id] = entry

        # 更新索引
        for tag in entry.tags:
            self._tag_index[tag].add(entry.id)

        if self._current_session:
            self._current_session.knowledge_built.append(entry.id)

        logger.info(f"添加知识: {entry.id[:8]}, importance={importance}")
        return entry

    def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """获取知识条目

        Args:
            entry_id: 知识ID

        Returns:
            Optional[KnowledgeEntry]: 知识条目
        """
        entry = self._knowledge_store.get(entry_id)
        if entry:
            entry.touch()
        return entry

    def search_knowledge(self,
                        query: str,
                        tags: List[str] = None,
                        top_k: int = 10) -> List[KnowledgeEntry]:
        """搜索知识

        Args:
            query: 查询文本
            tags: 标签过滤
            top_k: 返回数量

        Returns:
            List[KnowledgeEntry]: 匹配的知识列表
        """
        query_lower = query.lower()

        # 标签过滤
        candidate_ids = None
        if tags:
            candidate_ids = set()
            for tag in tags:
                if tag in self._tag_index:
                    if candidate_ids is None:
                        candidate_ids = self._tag_index[tag].copy()
                    else:
                        candidate_ids &= self._tag_index[tag]

        matched = []
        for entry_id, entry in self._knowledge_store.items():
            # 跳过被过滤的
            if candidate_ids and entry_id not in candidate_ids:
                continue

            # 文本匹配
            if query_lower in entry.content.lower():
                matched.append((entry, entry.access_count))

        # 按访问次数排序（更常用的在前）
        matched.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matched[:top_k]]

    def get_related_knowledge(self, entry_id: str, top_k: int = 5) -> List[KnowledgeEntry]:
        """获取相关知识

        Args:
            entry_id: 知识ID
            top_k: 返回数量

        Returns:
            List[KnowledgeEntry]: 相关的知识列表
        """
        entry = self._knowledge_store.get(entry_id)
        if not entry:
            return []

        related = []
        for related_id in entry.related_entries:
            related_entry = self._knowledge_store.get(related_id)
            if related_entry:
                related.append(related_entry)

        # 也考虑同标签的知识
        for tag in entry.tags:
            for candidate_id in self._tag_index.get(tag, set()):
                if candidate_id != entry_id and candidate_id not in entry.related_entries:
                    candidate = self._knowledge_store.get(candidate_id)
                    if candidate:
                        related.append(candidate)

        return related[:top_k]

    def link_knowledge(self, entry_id1: str, entry_id2: str):
        """链接两个知识条目

        Args:
            entry_id1: 知识ID 1
            entry_id2: 知识ID 2
        """
        entry1 = self._knowledge_store.get(entry_id1)
        entry2 = self._knowledge_store.get(entry_id2)

        if entry1 and entry2:
            if entry_id2 not in entry1.related_entries:
                entry1.related_entries.append(entry_id2)
            if entry_id1 not in entry2.related_entries:
                entry2.related_entries.append(entry_id1)
            logger.info(f"链接知识: {entry_id1[:8]} <-> {entry_id2[:8]}")

    def build_knowledge_graph(self) -> Dict[str, Any]:
        """构建知识图谱

        Returns:
            Dict: 图谱数据
        """
        nodes = []
        edges = []

        for entry in self._knowledge_store.values():
            nodes.append({
                "id": entry.id,
                "content": entry.content[:50],
                "importance": entry.importance,
                "tags": list(entry.tags)
            })

        for entry in self._knowledge_store.values():
            for related_id in entry.related_entries:
                edges.append({
                    "source": entry.id,
                    "target": related_id
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

    def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """获取会话上下文

        Args:
            session_id: 会话ID

        Returns:
            Optional[SessionContext]: 会话上下文
        """
        return self._sessions.get(session_id)

    def get_recent_context(self, hours: int = 24) -> List[SessionContext]:
        """获取最近的会话上下文

        Args:
            hours: 过去多少小时

        Returns:
            List[SessionContext]: 会话上下文列表
        """
        cutoff = time.time() - hours * 3600

        recent = [
            s for s in self._sessions.values()
            if s.start_time >= cutoff
        ]

        recent.sort(key=lambda x: x.start_time, reverse=True)
        return recent

    def get_topic_summary(self, topic: str) -> Dict[str, Any]:
        """获取主题摘要

        Args:
            topic: 主题

        Returns:
            Dict: 主题摘要
        """
        entry_ids = self._topic_index.get(topic, set())

        if not entry_ids:
            return {
                "topic": topic,
                "count": 0,
                "key_points": [],
                "summary": ""
            }

        entries = [
            self._knowledge_store[eid]
            for eid in entry_ids
            if eid in self._knowledge_store
        ]

        # 按重要性排序取前5
        top_entries = sorted(entries, key=lambda x: x.importance, reverse=True)[:5]

        return {
            "topic": topic,
            "count": len(entries),
            "key_points": [e.content[:100] for e in top_entries],
            "summary": " ".join([e.content[:200] for e in top_entries[:3]])
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        total_knowledge = len(self._knowledge_store)
        total_sessions = len(self._sessions)
        total_tags = len(self._tag_index)

        avg_importance = 0.0
        if total_knowledge > 0:
            avg_importance = sum(e.importance for e in self._knowledge_store.values()) / total_knowledge

        return {
            "total_knowledge": total_knowledge,
            "total_sessions": total_sessions,
            "total_tags": total_tags,
            "avg_importance": avg_importance
        }

    def consolidate_knowledge(self, min_importance: float = 3.0) -> int:
        """整合知识，删除低重要性条目

        Args:
            min_importance: 最小重要性阈值

        Returns:
            int: 删除的条目数量
        """
        to_remove = [
            entry_id for entry_id, entry in self._knowledge_store.items()
            if entry.importance < min_importance and entry.access_count < 2
        ]

        for entry_id in to_remove:
            entry = self._knowledge_store[entry_id]
            # 清理标签索引
            for tag in entry.tags:
                self._tag_index[tag].discard(entry_id)
            del self._knowledge_store[entry_id]

        logger.info(f"整合知识: 删除 {len(to_remove)} 条低重要性条目")
        return len(to_remove)


# 便捷函数
def create_cross_session_knowledge(user_id: str = "default") -> CrossSessionKnowledge:
    """创建跨会话知识管理器"""
    return CrossSessionKnowledge(user_id=user_id)