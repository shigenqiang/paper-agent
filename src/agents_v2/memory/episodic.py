"""
情景记忆 - Episodic Memory

职责: 记录Agent执行轨迹，支持回溯
- 按任务/时间组织
- 支持回放和复现
"""
import asyncio
import time
import json
import os
import hashlib
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .types import EpisodicEntry, MemoryType


class EpisodicMemory:
    """
    情景记忆 - 记录Agent执行轨迹

    特点:
    - 按任务ID + 时间戳索引
    - 记录完整的执行上下文
    - 支持回放和复现
    """

    def __init__(self, storage_path: str = ".memory/episodes"):
        self.storage_path = storage_path
        self._index_path = os.path.join(storage_path, "index.json")
        self._episodes: Dict[str, EpisodicEntry] = {}  # episode_id -> entry
        self._task_index: Dict[str, List[str]] = {}  # task_id -> [episode_ids]
        self._lock = asyncio.Lock()
        self._ensure_storage()
        self._load_index()

    def _ensure_storage(self) -> None:
        """确保存储目录存在"""
        os.makedirs(self.storage_path, exist_ok=True)

    def _load_index(self) -> None:
        """加载索引"""
        if os.path.exists(self._index_path):
            try:
                with open(self._index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._task_index = data.get("task_index", {})
            except Exception:
                pass

    def _save_index(self) -> None:
        """保存索引"""
        with open(self._index_path, 'w', encoding='utf-8') as f:
            json.dump({
                "task_index": self._task_index
            }, f, ensure_ascii=False, indent=2)

    def _get_episode_path(self, episode_id: str) -> str:
        """获取情节文件路径"""
        return os.path.join(self.storage_path, f"{episode_id}.json")

    async def record_episode(
        self,
        task_id: str,
        agent_id: str,
        action: str,
        result: Any,
        context_snapshot: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """
        记录执行事件

        Args:
            task_id: 任务ID
            agent_id: Agent ID
            action: 执行的动作
            result: 执行结果
            context_snapshot: 上下文快照
            duration_ms: 执行时长(毫秒)
            success: 是否成功
            error: 错误信息

        Returns:
            episode_id
        """
        async with self._lock:
            # 生成episode_id
            episode_id = hashlib.md5(
                f"{task_id}{agent_id}{action}{time.time()}".encode()
            ).hexdigest()[:16]

            entry = EpisodicEntry(
                episode_id=episode_id,
                task_id=task_id,
                agent_id=agent_id,
                action=action,
                result=result,
                context_snapshot=context_snapshot or {},
                duration_ms=duration_ms,
                success=success,
                error=error
            )

            # 存储情节
            episode_path = self._get_episode_path(episode_id)
            with open(episode_path, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)

            # 更新索引
            self._episodes[episode_id] = entry
            if task_id not in self._task_index:
                self._task_index[task_id] = []
            self._task_index[task_id].append(episode_id)
            self._save_index()

            return episode_id

    async def get_episode(self, episode_id: str) -> Optional[EpisodicEntry]:
        """
        获取单个情节

        Args:
            episode_id: 情节ID

        Returns:
            EpisodicEntry或None
        """
        async with self._lock:
            # 先检查内存
            if episode_id in self._episodes:
                return self._episodes[episode_id]

            # 从磁盘加载
            episode_path = self._get_episode_path(episode_id)
            if not os.path.exists(episode_path):
                return None

            try:
                with open(episode_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    entry = EpisodicEntry(
                        episode_id=data["episode_id"],
                        task_id=data["task_id"],
                        agent_id=data["agent_id"],
                        action=data["action"],
                        result=data["result"],
                        context_snapshot=data.get("context_snapshot", {}),
                        timestamp=data.get("timestamp", time.time()),
                        duration_ms=data.get("duration_ms", 0.0),
                        success=data.get("success", True),
                        error=data.get("error")
                    )
                    self._episodes[episode_id] = entry
                    return entry
            except Exception:
                return None

    async def get_episodes(self, task_id: str) -> List[EpisodicEntry]:
        """
        获取任务的所有情节

        Args:
            task_id: 任务ID

        Returns:
            按时间排序的情节列表
        """
        async with self._lock:
            episode_ids = self._task_index.get(task_id, [])
            episodes = []

            for episode_id in episode_ids:
                entry = await self.get_episode(episode_id)
                if entry:
                    episodes.append(entry)

            # 按时间排序
            episodes.sort(key=lambda e: e.timestamp)
            return episodes

    async def replay_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """
        回放情节

        Args:
            episode_id: 情节ID

        Returns:
            可用于重建上下文的字典
        """
        entry = await self.get_episode(episode_id)
        if not entry:
            return None

        return {
            "episode_id": entry.episode_id,
            "task_id": entry.task_id,
            "agent_id": entry.agent_id,
            "action": entry.action,
            "result": entry.result,
            "context_snapshot": entry.context_snapshot,
            "timestamp": entry.timestamp,
            "duration_ms": entry.duration_ms,
            "success": entry.success
        }

    async def search_episodes(
        self,
        query: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 20
    ) -> List[EpisodicEntry]:
        """
        搜索历史情节

        Args:
            query: 搜索查询
            task_id: 可选的任务ID过滤
            agent_id: 可选的Agent ID过滤
            limit: 返回数量限制

        Returns:
            匹配的情节列表
        """
        async with self._lock:
            results = []

            # 确定搜索范围
            if task_id:
                episode_ids = self._task_index.get(task_id, [])
            else:
                episode_ids = list(self._episodes.keys())

            for episode_id in episode_ids:
                entry = await self.get_episode(episode_id)
                if not entry:
                    continue

                # Agent过滤
                if agent_id and entry.agent_id != agent_id:
                    continue

                # 关键词匹配
                query_lower = query.lower()
                if (query_lower in entry.action.lower() or
                    query_lower in str(entry.result).lower() or
                    query_lower in str(entry.context_snapshot).lower()):
                    results.append(entry)

                if len(results) >= limit:
                    break

            # 按时间排序
            results.sort(key=lambda e: e.timestamp, reverse=True)
            return results

    async def get_task_timeline(
        self,
        task_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取任务时间线

        Args:
            task_id: 任务ID

        Returns:
            时间线列表
        """
        episodes = await self.get_episodes(task_id)

        timeline = []
        for entry in episodes:
            timeline.append({
                "time": entry.timestamp,
                "agent_id": entry.agent_id,
                "action": entry.action,
                "duration_ms": entry.duration_ms,
                "success": entry.success
            })

        return timeline

    async def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务执行摘要

        Args:
            task_id: 任务ID

        Returns:
            摘要字典
        """
        episodes = await self.get_episodes(task_id)

        if not episodes:
            return {
                "task_id": task_id,
                "total_episodes": 0,
                "agents": [],
                "success_rate": 0.0
            }

        agents = set(e.agent_id for e in episodes)
        successful = sum(1 for e in episodes if e.success)
        total_duration = sum(e.duration_ms for e in episodes)

        return {
            "task_id": task_id,
            "total_episodes": len(episodes),
            "agents": list(agents),
            "success_rate": successful / len(episodes) if episodes else 0.0,
            "total_duration_ms": total_duration,
            "first_action": episodes[0].action if episodes else None,
            "last_action": episodes[-1].action if episodes else None
        }

    async def delete_task_episodes(self, task_id: str) -> int:
        """
        删除任务的所有情节

        Args:
            task_id: 任务ID

        Returns:
            删除数量
        """
        async with self._lock:
            episode_ids = self._task_index.get(task_id, [])
            deleted = 0

            for episode_id in episode_ids:
                episode_path = self._get_episode_path(episode_id)
                if os.path.exists(episode_path):
                    os.remove(episode_path)
                    deleted += 1

                if episode_id in self._episodes:
                    del self._episodes[episode_id]

            del self._task_index[task_id]
            self._save_index()

            return deleted

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_episodes": len(self._episodes),
            "total_tasks": len(self._task_index),
            "memory_type": MemoryType.EPISODIC.value
        }

    async def get_temporal_edges(
        self,
        task_id: str,
        window_seconds: float = 300
    ) -> List[Dict[str, Any]]:
        """
        获取时间边 (Zep式时序推理)

        构建相邻情节之间的时间边关系

        Args:
            task_id: 任务ID
            window_seconds: 时间窗口大小(秒)

        Returns:
            时间边列表 [{from_episode, to_episode, time_gap, relation}]
        """
        episodes = await self.get_episodes(task_id)

        edges = []
        for i in range(len(episodes) - 1):
            current = episodes[i]
            next_ep = episodes[i + 1]

            time_gap = next_ep.timestamp - current.timestamp

            edge = {
                "from_episode_id": current.episode_id,
                "to_episode_id": next_ep.episode_id,
                "from_agent": current.agent_id,
                "to_agent": next_ep.agent_id,
                "from_action": current.action,
                "to_action": next_ep.action,
                "time_gap_seconds": time_gap,
                "relation": self._classify_temporal_relation(
                    current.action,
                    next_ep.action,
                    time_gap,
                    window_seconds
                )
            }
            edges.append(edge)

        return edges

    def _classify_temporal_relation(
        self,
        from_action: str,
        to_action: str,
        time_gap: float,
        window_seconds: float
    ) -> str:
        """
        分类时序关系类型

        关系类型:
        - IMMEDIATE: < 5秒, 可能是同一操作分解
        - SEQUENTIAL: 5-60秒, 明确的先后顺序
        - DELAYED: 60-300秒, 有延迟的操作
        - CONCURRENT: 多Agent同时操作
        - PARALLEL: 并行执行
        """
        if time_gap < 5:
            return "IMMEDIATE"
        elif time_gap < 60:
            return "SEQUENTIAL"
        elif time_gap < window_seconds:
            return "DELAYED"
        else:
            return "DELAYED"

    async def find_causal_chain(
        self,
        task_id: str,
        target_episode_id: str
    ) -> List[str]:
        """
        查找因果链 (从结果反推原因)

        Args:
            task_id: 任务ID
            target_episode_id: 目标情节ID

        Returns:
            按因果顺序排列的情节ID列表
        """
        episodes = await self.get_episodes(task_id)
        episode_map = {e.episode_id: e for e in episodes}

        # 从目标情节向前追溯
        chain = [target_episode_id]
        current_id = target_episode_id

        while True:
            # 找到当前情节的索引
            current_idx = next(
                (i for i, e in enumerate(episodes) if e.episode_id == current_id),
                -1
            )

            if current_idx <= 0:
                break

            # 检查前一个情节是否与当前有因果关系
            prev_episode = episodes[current_idx - 1]

            # 如果时间间隔小于5分钟，认为有因果关系
            time_gap = episodes[current_idx].timestamp - prev_episode.timestamp
            if time_gap < 300:
                chain.insert(0, prev_episode.episode_id)
                current_id = prev_episode.episode_id
            else:
                break

        return chain

    async def get_concurrent_agents(
        self,
        task_id: str,
        time_point: float
    ) -> List[str]:
        """
        获取指定时间点的并发Agent

        Args:
            task_id: 任务ID
            time_point: 时间戳

        Returns:
            在该时间点活跃的Agent列表
        """
        episodes = await self.get_episodes(task_id)
        concurrent = []

        for entry in episodes:
            # 计算情节结束时间
            end_time = entry.timestamp + (entry.duration_ms / 1000)

            # 检查是否包含时间点
            if entry.timestamp <= time_point <= end_time:
                if entry.agent_id not in concurrent:
                    concurrent.append(entry.agent_id)

        return concurrent
