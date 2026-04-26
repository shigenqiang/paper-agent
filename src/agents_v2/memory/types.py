"""
记忆类型定义 - Memory Types

定义各层记忆的类型和基础结构
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import time


class MemoryType(str, Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"        # 短期记忆 - 当前任务上下文
    SESSION = "session"              # 会话级记忆 - 任务内跨Agent共享
    LONG_TERM = "long_term"          # 长期记忆 - 跨任务持久化
    EPISODIC = "episodic"            # 情景记忆 - 执行轨迹记录
    USER_PROFILE = "user_profile"     # 用户画像 - 偏好和特征
    PROCEDURAL = "procedural"        # 程序记忆 - 工作流程和SOP


class ImportanceLevel(float, Enum):
    """重要性等级"""
    CRITICAL = 1.0   # 关键 - 不能遗忘
    HIGH = 0.8       # 高 - 长期保留
    MEDIUM = 0.5     # 中 - 标准衰减
    LOW = 0.3        # 低 - 快速遗忘


@dataclass
class MemoryEntry:
    """记忆条目基类"""
    id: str
    memory_type: MemoryType
    content: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    importance: float = 0.5  # 0.0 - 1.0
    importance_level: ImportanceLevel = ImportanceLevel.MEDIUM
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"  # 来源: system/user/agent/llm

    def access(self) -> None:
        """记录访问，增加重要性"""
        self.access_count += 1
        self.last_accessed = time.time()
        # 频繁访问的记忆重要性递增
        if self.access_count > 5:
            self.importance = min(1.0, self.importance + 0.01)

    def retention_score(self) -> float:
        """
        计算保留分数 (参考艾宾浩斯遗忘曲线)

        分数 = importance * e^(-t/S)
        - t: 距离上次访问的时间
        - S: 记忆强度参数 (基于importance_level)
        """
        t = time.time() - self.last_accessed

        # 根据重要性等级设置记忆强度
        S_map = {
            ImportanceLevel.CRITICAL: float('inf'),  # 永不遗忘
            ImportanceLevel.HIGH: 86400 * 7,          # 7天
            ImportanceLevel.MEDIUM: 86400,             # 1天
            ImportanceLevel.LOW: 3600,                 # 1小时
        }
        S = S_map.get(self.importance_level, 86400)

        # 基础保留率
        retention = self.importance * (1.0 if S == float('inf') else np_exp(-t / S))
        return retention

    def should_forget(self, threshold: float = 0.1) -> bool:
        """判断是否应该遗忘"""
        return self.retention_score() < threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "importance": self.importance,
            "importance_level": self.importance_level.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "source": self.source,
            "retention_score": self.retention_score()
        }


@dataclass
class EpisodicEntry:
    """情景记忆条目 - 记录Agent执行轨迹"""
    episode_id: str
    task_id: str
    agent_id: str
    action: str
    result: Any
    context_snapshot: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "action": self.action,
            "result": self.result,
            "context_snapshot": self.context_snapshot,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error
        }


@dataclass
class UserPreference:
    """用户偏好条目"""
    user_id: str
    preference_key: str
    preference_value: Any
    confidence: float = 0.5  # 置信度
    updated_at: float = field(default_factory=time.time)
    source_interactions: int = 1

    def boost(self, value: Any, confidence_boost: float = 0.1) -> None:
        """强化偏好"""
        if self.preference_value == value:
            self.confidence = min(1.0, self.confidence + confidence_boost)
            self.source_interactions += 1
        else:
            # 偏好改变，降低置信度
            self.confidence = max(0.0, self.confidence - confidence_boost * 2)
            if self.confidence < 0.3:
                self.preference_value = value
                self.confidence = 0.3


@dataclass
class ProcedureEntry:
    """程序记忆条目 - 存储工作流程和SOP"""
    procedure_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    success_rate: float = 1.0
    total_executions: int = 0
    successful_executions: int = 0
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_execution(self, success: bool) -> None:
        """记录执行结果"""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        self.success_rate = self.successful_executions / self.total_executions
        self.last_used = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "success_rate": self.success_rate,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "metadata": self.metadata
        }


# 简单的numpy替代，避免依赖
import math


def np_exp(x):
    """简单的指数函数替代"""
    return math.exp(x)
