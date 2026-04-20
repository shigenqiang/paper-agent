"""记忆持久化存储"""
import json
import os
import pickle
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

from src.memory.short_term_memory import ShortTermMemory
from src.memory.semantic_memory import SemanticMemory
from src.memory.episodic_memory import EpisodicMemory

logger = logging.getLogger(__name__)


class MemoryStorage:
    """记忆存储管理器"""

    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (self.storage_dir / "short_term").mkdir(exist_ok=True)
        (self.storage_dir / "semantic").mkdir(exist_ok=True)
        (self.storage_dir / "episodic").mkdir(exist_ok=True)
        (self.storage_dir / "sessions").mkdir(exist_ok=True)

    def save_short_term_memory(
        self,
        memory: ShortTermMemory,
        session_id: str
    ) -> bool:
        """保存短期记忆"""
        try:
            file_path = self.storage_dir / "short_term" / f"{session_id}.json"
            data = memory.to_dict()

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved short-term memory for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save short-term memory: {e}")
            return False

    def load_short_term_memory(
        self,
        session_id: str
    ) -> Optional[ShortTermMemory]:
        """加载短期记忆"""
        try:
            file_path = self.storage_dir / "short_term" / f"{session_id}.json"

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return ShortTermMemory.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load short-term memory: {e}")
            return None

    def save_semantic_memory(
        self,
        memory: SemanticMemory
    ) -> bool:
        """保存语义记忆"""
        try:
            file_path = self.storage_dir / "semantic" / "semantic_memory.json"

            # 导出记忆数据
            data = {
                "memories": {},
                "tags_index": memory.tags_index,
                "max_memories": memory.max_memories,
                "cleanup_threshold": memory.cleanup_threshold,
                "last_updated": datetime.now().isoformat()
            }

            for memory_id, memory_item in memory.memories.items():
                data["memories"][memory_id] = {
                    "id": memory_item.id,
                    "content": memory_item.content,
                    "memory_type": memory_item.memory_type.value,
                    "importance": memory_item.importance,
                    "confidence": memory_item.confidence,
                    "created_at": memory_item.created_at.isoformat(),
                    "updated_at": memory_item.updated_at.isoformat(),
                    "last_accessed": memory_item.last_accessed.isoformat(),
                    "access_count": memory_item.access_count,
                    "tags": memory_item.tags,
                    "embedding": memory_item.embedding,
                    "source": memory_item.source,
                    "metadata": memory_item.metadata
                }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info("Saved semantic memory")
            return True
        except Exception as e:
            logger.error(f"Failed to save semantic memory: {e}")
            return False

    def load_semantic_memory(self) -> Optional[Dict[str, Any]]:
        """加载语义记忆数据"""
        try:
            file_path = self.storage_dir / "semantic" / "semantic_memory.json"

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return data
        except Exception as e:
            logger.error(f"Failed to load semantic memory: {e}")
            return None

    def save_episodic_memory(
        self,
        memory: EpisodicMemory
    ) -> bool:
        """保存情景记忆"""
        try:
            file_path = self.storage_dir / "episodic" / "episodic_memory.json"

            # 导出情景记忆数据
            data = {
                "events": {},
                "episodes": {},
                "session_episodes": memory.session_episodes,
                "max_events": memory.max_events,
                "max_episodes": memory.max_episodes,
                "current_episode_id": memory.current_episode_id,
                "last_updated": datetime.now().isoformat()
            }

            # 保存事件
            for event_id, event in memory.events.items():
                data["events"][event_id] = event.to_dict()

            # 保存情景
            for episode_id, episode in memory.episodes.items():
                data["episodes"][episode_id] = episode.to_dict()

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info("Saved episodic memory")
            return True
        except Exception as e:
            logger.error(f"Failed to save episodic memory: {e}")
            return False

    def load_episodic_memory(self) -> Optional[Dict[str, Any]]:
        """加载情景记忆数据"""
        try:
            file_path = self.storage_dir / "episodic" / "episodic_memory.json"

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return data
        except Exception as e:
            logger.error(f"Failed to load episodic memory: {e}")
            return None

    def save_session_summary(
        self,
        session_id: str,
        summary: Dict[str, Any]
    ) -> bool:
        """保存会话摘要"""
        try:
            file_path = self.storage_dir / "sessions" / f"{session_id}_summary.json"

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved session summary for {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session summary: {e}")
            return False

    def load_session_summary(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """加载会话摘要"""
        try:
            file_path = self.storage_dir / "sessions" / f"{session_id}_summary.json"

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load session summary: {e}")
            return None

    def list_sessions(self) -> list:
        """列出所有会话"""
        try:
            sessions_dir = self.storage_dir / "sessions"
            session_files = list(sessions_dir.glob("*_summary.json"))

            sessions = []
            for file_path in session_files:
                session_id = file_path.stem.replace("_summary", "")
                sessions.append(session_id)

            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """删除会话相关数据"""
        try:
            # 删除短期记忆
            short_term_path = self.storage_dir / "short_term" / f"{session_id}.json"
            if short_term_path.exists():
                short_term_path.unlink()

            # 删除会话摘要
            summary_path = self.storage_dir / "sessions" / f"{session_id}_summary.json"
            if summary_path.exists():
                summary_path.unlink()

            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    def backup_memory(self, backup_name: Optional[str] = None) -> bool:
        """备份记忆数据"""
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            backup_dir = self.storage_dir / "backups" / backup_name
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 复制所有记忆文件
            import shutil

            # 备份语义记忆
            semantic_src = self.storage_dir / "semantic"
            if semantic_src.exists():
                shutil.copytree(semantic_src, backup_dir / "semantic", dirs_exist_ok=True)

            # 备份情景记忆
            episodic_src = self.storage_dir / "episodic"
            if episodic_src.exists():
                shutil.copytree(episodic_src, backup_dir / "episodic", dirs_exist_ok=True)

            # 备份会话数据
            sessions_src = self.storage_dir / "sessions"
            if sessions_src.exists():
                shutil.copytree(sessions_src, backup_dir / "sessions", dirs_exist_ok=True)

            logger.info(f"Created memory backup: {backup_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup memory: {e}")
            return False

    def restore_memory(self, backup_name: str) -> bool:
        """恢复记忆数据"""
        try:
            backup_dir = self.storage_dir / "backups" / backup_name

            if not backup_dir.exists():
                logger.error(f"Backup not found: {backup_name}")
                return False

            import shutil

            # 恢复语义记忆
            if (backup_dir / "semantic").exists():
                semantic_dst = self.storage_dir / "semantic"
                if semantic_dst.exists():
                    shutil.rmtree(semantic_dst)
                shutil.copytree(backup_dir / "semantic", semantic_dst)

            # 恢复情景记忆
            if (backup_dir / "episodic").exists():
                episodic_dst = self.storage_dir / "episodic"
                if episodic_dst.exists():
                    shutil.rmtree(episodic_dst)
                shutil.copytree(backup_dir / "episodic", episodic_dst)

            # 恢复会话数据
            if (backup_dir / "sessions").exists():
                sessions_dst = self.storage_dir / "sessions"
                if sessions_dst.exists():
                    shutil.rmtree(sessions_dst)
                shutil.copytree(backup_dir / "sessions", sessions_dst)

            logger.info(f"Restored memory from backup: {backup_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore memory: {e}")
            return False

    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        stats = {
            "storage_dir": str(self.storage_dir),
            "total_size_mb": 0,
            "session_count": 0,
            "semantic_memory_size_mb": 0,
            "episodic_memory_size_mb": 0,
            "sessions_size_mb": 0
        }

        try:
            # 计算总大小
            for root, dirs, files in os.walk(self.storage_dir):
                for file in files:
                    file_path = Path(root) / file
                    stats["total_size_mb"] += file_path.stat().st_size / (1024 * 1024)

            # 计算各部分大小
            semantic_dir = self.storage_dir / "semantic"
            if semantic_dir.exists():
                for file in semantic_dir.rglob("*"):
                    if file.is_file():
                        stats["semantic_memory_size_mb"] += file.stat().st_size / (1024 * 1024)

            episodic_dir = self.storage_dir / "episodic"
            if episodic_dir.exists():
                for file in episodic_dir.rglob("*"):
                    if file.is_file():
                        stats["episodic_memory_size_mb"] += file.stat().st_size / (1024 * 1024)

            sessions_dir = self.storage_dir / "sessions"
            if sessions_dir.exists():
                stats["session_count"] = len(list(sessions_dir.glob("*_summary.json")))
                for file in sessions_dir.rglob("*"):
                    if file.is_file():
                        stats["sessions_size_mb"] += file.stat().st_size / (1024 * 1024)

        except Exception as e:
            logger.error(f"Failed to calculate storage stats: {e}")

        return stats
