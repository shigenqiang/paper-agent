"""
记忆类型定义 - Memory Types

定义各层记忆的类型和基础结构
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import time
import math


class MemoryType(str, Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"        # 短期记忆 - 当前任务上下文
    SESSION = "session"              # 会话级记忆 - 任务内跨Agent共享
    LONG_TERM = "long_term"          # 长期记忆 - 跨任务持久化
    EPISODIC = "episodic"            # 情景记忆 - 执行轨迹记录
    USER_PROFILE = "user_profile"     # 用户画像 - 偏好和特征
    PROCEDURAL = "procedural"        # 程序记忆 - 工作流程和SOP


class ImportanceLevel(float, Enum):
    """重要性等级（五级体系）

    | 等级 | 分数 | 语义 | S参数（秒）| 保留时间 |
    |------|------|------|-----------|---------|
    | CRITICAL | 1.0 | 永不遗忘 | ∞ | 永不 |
    | HIGH | 0.8 | 长期保留 | 604,800 (7天) | 7天 |
    | MEDIUM | 0.5 | 标准衰减 | 86,400 (1天) | 1天 |
    | LOW | 0.3 | 快速遗忘 | 3,600 (1小时) | 1小时 |
    | FORGOTTEN | <0.1 | 已删除 | <3,600 | - |
    """
    CRITICAL = 1.0   # 关键 - 不能遗忘
    HIGH = 0.8       # 高 - 长期保留
    MEDIUM = 0.5      # 中 - 标准衰减
    LOW = 0.3        # 低 - 快速遗忘
    FORGOTTEN = 0.1   # 已遗忘 - 待删除

    @classmethod
    def from_score(cls, importance: float) -> "ImportanceLevel":
        """根据分数确定等级"""
        if importance >= 0.9:
            return cls.CRITICAL
        elif importance >= 0.7:
            return cls.HIGH
        elif importance >= 0.4:
            return cls.MEDIUM
        elif importance >= 0.2:
            return cls.LOW
        else:
            return cls.FORGOTTEN

    def get_strength_seconds(self) -> float:
        """获取记忆强度参数（秒）"""
        if self == ImportanceLevel.CRITICAL:
            return float('inf')  # 永不遗忘
        elif self == ImportanceLevel.HIGH:
            return 604800  # 7天
        elif self == ImportanceLevel.MEDIUM:
            return 86400   # 1天
        elif self == ImportanceLevel.LOW:
            return 3600     # 1小时
        else:
            return 0        # FORGOTTEN


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

    # SM-2 间隔复习参数
    sm2_interval_days: float = 1.0  # 下次复习间隔（天）
    sm2_ease_factor: float = 2.5    # 难度因子
    sm2_repetitions: int = 0        # 重复次数

    def access(self) -> None:
        """记录访问，增加重要性"""
        self.access_count += 1
        self.last_accessed = time.time()
        # 频繁访问的记忆重要性递增
        if self.access_count > 5:
            self.importance = min(1.0, self.importance + 0.01)

    def compute_importance_score(
        self,
        relevance: float = 0.5,
        explicit: float = None,
        recency: float = None
    ) -> float:
        """
        计算重要性评分

        公式: score = relevance×0.3 + explicit×0.4 + recency×0.2 + access_boost×0.1

        Args:
            relevance: 与当前任务的相关性 (0.0-1.0)
            explicit: 显式标记的重要性 (0.0-1.0)，默认使用 self.importance
            recency: 新近度 (0.0-1.0)，默认根据创建时间计算

        Returns:
            综合重要性评分 (0.0-1.0)
        """
        explicit = explicit if explicit is not None else self.importance

        # 计算 recency（7天内为1.0，之后线性衰减）
        if recency is None:
            age_seconds = time.time() - self.created_at
            age_days = age_seconds / 86400
            recency = max(0.0, 1.0 - age_days / 7.0)

        # 计算 access_boost
        access_boost = min(self.access_count / 10, 1.0)

        # 综合评分
        score = (
            relevance * 0.3 +
            explicit * 0.4 +
            recency * 0.2 +
            access_boost * 0.1
        )

        # 动态调整等级
        self.importance = score
        self.importance_level = ImportanceLevel.from_score(score)

        return score

    def sm2_review(self, quality: int) -> None:
        """
        SM-2 间隔复习算法

        公式:
        - I(1) = 1
        - I(2) = 6
        - I(n) = I(n-1) × EF (n > 2)
        - EF' = EF + 0.1 - (5-q) × (0.08 + (5-q) × 0.02)

        Args:
            quality: 回忆质量 (0-5)
                0: 完全忘记
                1: 错误但看到答案后想起
                2: 错误但看到答案后容易想起
                3: 正确但有困难
                4: 正确稍有犹豫
                5: 完美正确
        """
        quality = max(0, min(5, quality))

        if quality < 3:
            # 复习失败，重置
            self.sm2_repetitions = 0
            self.sm2_interval_days = 1
        else:
            if self.sm2_repetitions == 0:
                self.sm2_interval_days = 1
            elif self.sm2_repetitions == 1:
                self.sm2_interval_days = 6
            else:
                self.sm2_interval_days = self.sm2_interval_days * self.sm2_ease_factor

            self.sm2_repetitions += 1

        # 更新难度因子
        self.sm2_ease_factor = max(
            1.3,
            self.sm2_ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        )

        # 根据 SM-2 结果更新重要性
        self.compute_importance_score(
            explicit=self.importance,
            recency=min(self.sm2_interval_days / 30, 1.0)
        )

    def should_review(self) -> bool:
        """检查是否应该复习"""
        if self.sm2_repetitions == 0:
            return True

        next_review_time = self.last_accessed + (self.sm2_interval_days * 86400)
        return time.time() >= next_review_time

    def retention_score(self) -> float:
        """
        计算保留分数 (参考艾宾浩斯遗忘曲线)

        公式: retention = importance * e^(-t/S)
        - t: 距离上次访问的时间
        - S: 记忆强度参数 (基于importance_level)
        """
        t = time.time() - self.last_accessed
        S = self.importance_level.get_strength_seconds()

        if S == float('inf'):
            return 1.0

        retention = self.importance * math.exp(-t / S)
        return min(1.0, max(0.0, retention))

    def should_forget(self, threshold: float = 0.1) -> bool:
        """判断是否应该遗忘"""
        if self.importance_level == ImportanceLevel.CRITICAL:
            return False
        return self.retention_score() < threshold

    def should_promote_to_long_term(self, threshold: float = 0.7) -> bool:
        """判断是否应该晋升到长期记忆"""
        return self.importance >= threshold or self.access_count > 10

    def adjust_level(self) -> None:
        """
        动态调整重要性等级

        规则:
        - 升级: 7天内访问>10次 → HIGH；用户明确标记 → CRITICAL
        - 降级: 30天未访问 → MEDIUM；过时信息 → LOW
        """
        current_time = time.time()

        # 检查降级条件
        days_since_access = (current_time - self.last_accessed) / 86400

        if days_since_access > 30 and self.importance_level != ImportanceLevel.CRITICAL:
            # 30天未访问，降级
            if self.importance_level == ImportanceLevel.HIGH:
                self.importance_level = ImportanceLevel.MEDIUM
                self.importance = max(self.importance * 0.8, 0.5)
        elif days_since_access > 7 and self.importance_level == ImportanceLevel.MEDIUM:
            # 7天未访问，降级到 LOW
            self.importance_level = ImportanceLevel.LOW
            self.importance = max(self.importance * 0.6, 0.3)

        # 检查升级条件
        if self.access_count > 10 and days_since_access < 7:
            if self.importance_level == ImportanceLevel.MEDIUM:
                self.importance_level = ImportanceLevel.HIGH
                self.importance = max(self.importance, 0.8)

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
            "retention_score": self.retention_score(),
            "sm2_interval_days": self.sm2_interval_days,
            "sm2_ease_factor": self.sm2_ease_factor,
            "sm2_repetitions": self.sm2_repetitions,
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


# numpy替代在各自方法中使用 math.exp
