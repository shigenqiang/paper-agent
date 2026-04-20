"""情景记忆（Episodic Memory）模块"""
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """事件类型"""
    QUERY = "query"  # 查询事件
    SEARCH = "search"  # 搜索事件
    ANALYSIS = "analysis"  # 分析事件
    ERROR = "error"  # 错误事件
    INSIGHT = "insight"  # 洞察事件
    DECISION = "decision"  # 决策事件
    INTERACTION = "interaction"  # 交互事件


class Event(BaseModel):
    """事件"""
    id: str
    event_type: EventType
    description: str
    timestamp: datetime
    session_id: str
    participants: List[str] = Field(default_factory=list)
    outcomes: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    embedding: Optional[List[float]] = None
    related_events: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "participants": self.participants,
            "outcomes": self.outcomes,
            "context": self.context,
            "importance": self.importance,
            "related_events": self.related_events
        }


class Episode(BaseModel):
    """情景（Episode）- 一系列相关的事件"""
    id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    session_id: str
    event_ids: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None

    def duration(self) -> timedelta:
        """计算情景持续时间"""
        return self.end_time - self.start_time

    def add_event(self, event_id: str) -> None:
        """添加事件"""
        if event_id not in self.event_ids:
            self.event_ids.append(event_id)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration().total_seconds(),
            "session_id": self.session_id,
            "event_count": len(self.event_ids),
            "summary": self.summary,
            "tags": self.tags,
            "metadata": self.metadata
        }


class EpisodicMemory(BaseModel):
    """情景记忆（Episodic Memory）"""

    events: Dict[str, Event] = {}
    episodes: Dict[str, Episode] = {}
    session_episodes: Dict[str, List[str]] = {}  # 会话到情景的映射
    max_events: int = 10000
    max_episodes: int = 1000
    current_episode_id: Optional[str] = None

    def start_episode(
        self,
        title: str,
        description: str,
        session_id: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """开始一个新情景"""
        episode_id = f"epi_{datetime.now().timestamp()}"

        episode = Episode(
            id=episode_id,
            title=title,
            description=description,
            start_time=datetime.now(),
            end_time=datetime.now(),
            session_id=session_id,
            tags=tags or [],
            metadata={}
        )

        self.episodes[episode_id] = episode

        # 更新会话映射
        if session_id not in self.session_episodes:
            self.session_episodes[session_id] = []
        self.session_episodes[session_id].append(episode_id)

        self.current_episode_id = episode_id

        logger.info(f"Started episode: {episode_id} - {title}")
        return episode_id

    def end_episode(self, episode_id: Optional[str] = None, summary: Optional[str] = None) -> bool:
        """结束一个情景"""
        episode_id = episode_id or self.current_episode_id
        if not episode_id:
            return False

        episode = self.episodes.get(episode_id)
        if not episode:
            return False

        episode.end_time = datetime.now()
        if summary:
            episode.summary = summary

        if self.current_episode_id == episode_id:
            self.current_episode_id = None

        logger.info(f"Ended episode: {episode_id}")
        return True

    def add_event(
        self,
        event_type: EventType,
        description: str,
        session_id: str,
        participants: Optional[List[str]] = None,
        outcomes: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        embedding: Optional[List[float]] = None
    ) -> str:
        """添加事件"""
        event_id = f"evt_{datetime.now().timestamp()}"

        event = Event(
            id=event_id,
            event_type=event_type,
            description=description,
            timestamp=datetime.now(),
            session_id=session_id,
            participants=participants or [],
            outcomes=outcomes,
            context=context,
            importance=importance,
            embedding=embedding
        )

        self.events[event_id] = event

        # 添加到当前情景
        if self.current_episode_id:
            self.episodes[self.current_episode_id].add_event(event_id)
            # 更新情景的结束时间
            self.episodes[self.current_episode_id].end_time = datetime.now()

        logger.debug(f"Added event: {event_id} - {event_type.value}")
        return event_id

    def get_event(self, event_id: str) -> Optional[Event]:
        """获取事件"""
        return self.events.get(event_id)

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """获取情景"""
        return self.episodes.get(episode_id)

    def get_session_episodes(self, session_id: str) -> List[Episode]:
        """获取会话的所有情景"""
        episode_ids = self.session_episodes.get(session_id, [])
        return [self.episodes[eid] for eid in episode_ids if eid in self.episodes]

    def get_episode_events(self, episode_id: str) -> List[Event]:
        """获取情景的所有事件"""
        episode = self.episodes.get(episode_id)
        if not episode:
            return []

        return [self.events[eid] for eid in episode.event_ids if eid in self.events]

    def search_events(
        self,
        query: str,
        event_type: Optional[EventType] = None,
        session_id: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        top_k: int = 10
    ) -> List[Tuple[Event, float]]:
        """搜索事件"""
        query_lower = query.lower()
        results = []

        for event in self.events.values():
            # 类型过滤
            if event_type and event.event_type != event_type:
                continue

            # 会话过滤
            if session_id and event.session_id != session_id:
                continue

            # 时间范围过滤
            if time_range:
                start, end = time_range
                if not (start <= event.timestamp <= end):
                    continue

            # 内容匹配
            score = 0.0
            desc_lower = event.description.lower()

            if query_lower in desc_lower:
                score = 1.0
            else:
                query_words = set(query_lower.split())
                desc_words = set(desc_lower.split())
                if query_words & desc_words:
                    intersection = query_words & desc_words
                    score = len(intersection) / len(query_words)

            if score > 0:
                # 考虑重要性
                relevance_score = score * event.importance
                results.append((event, relevance_score))

        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_episodes(
        self,
        query: str,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Tuple[Episode, float]]:
        """搜索情景"""
        query_lower = query.lower()
        results = []

        for episode in self.episodes.values():
            # 会话过滤
            if session_id and episode.session_id != session_id:
                continue

            # 标签过滤
            if tags and not any(tag in episode.tags for tag in tags):
                continue

            # 内容匹配
            score = 0.0
            desc_lower = episode.description.lower()
            title_lower = episode.title.lower()

            if query_lower in desc_lower or query_lower in title_lower:
                score = 1.0
            else:
                query_words = set(query_lower.split())
                desc_words = set(desc_lower.split())
                title_words = set(title_lower.split())
                if query_words & desc_words or query_words & title_words:
                    intersection = (query_words & desc_words) | (query_words & title_words)
                    score = len(intersection) / len(query_words)

            if score > 0:
                results.append((episode, score))

        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_recent_events(
        self,
        n: int = 10,
        event_type: Optional[EventType] = None
    ) -> List[Event]:
        """获取最近的事件"""
        events = list(self.events.values())

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # 按时间排序
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:n]

    def get_recent_episodes(self, n: int = 10) -> List[Episode]:
        """获取最近的情景"""
        episodes = list(self.episodes.values())
        episodes.sort(key=lambda e: e.start_time, reverse=True)
        return episodes[:n]

    def get_events_by_type(
        self,
        event_type: EventType,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> List[Event]:
        """根据类型获取事件"""
        events = [e for e in self.events.values() if e.event_type == event_type]

        if time_range:
            start, end = time_range
            events = [e for e in events if start <= e.timestamp <= end]

        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events

    def cleanup_old_events(self, days_threshold: int = 30, min_importance: float = 0.3) -> int:
        """清理旧事件"""
        threshold = datetime.now() - timedelta(days=days_threshold)

        to_delete = [
            event_id for event_id, event in self.events.items()
            if event.timestamp < threshold and event.importance < min_importance
        ]

        for event_id in to_delete:
            # 从情景中移除
            for episode in self.episodes.values():
                if event_id in episode.event_ids:
                    episode.event_ids.remove(event_id)
            del self.events[event_id]

        logger.info(f"Cleaned up {len(to_delete)} old events")
        return len(to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.events:
            return {"total_events": 0, "total_episodes": 0}

        type_counts = {}
        for event in self.events.values():
            event_type = event.event_type.value
            type_counts[event_type] = type_counts.get(event_type, 0) + 1

        return {
            "total_events": len(self.events),
            "total_episodes": len(self.episodes),
            "events_by_type": type_counts,
            "total_sessions": len(self.session_episodes),
            "current_episode": self.current_episode_id
        }

    def export_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """导出会话历史"""
        episodes = self.get_session_episodes(session_id)
        history = []

        for episode in episodes:
            events = self.get_episode_events(episode.id)
            history.append({
                "episode": episode.to_dict(),
                "events": [e.to_dict() for e in events]
            })

        return history
