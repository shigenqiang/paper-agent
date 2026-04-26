"""
间隔重复系统 - Spaced Repetition System

基于间隔重复算法（Spaced Repetition）实现复习提醒:
- 复习间隔 [1, 2, 4, 7, 15, 30] 天
- 根据表现调整间隔
- 推送提醒通知
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ReviewQuality(Enum):
    """复习质量"""
    FAIL = 0      # 完全忘记
    HARD = 1      # 困难想起
    GOOD = 2      # 正常回忆
    EASY = 3      # 轻松回忆


@dataclass
class ReviewSchedule:
    """复习计划条目"""
    item_id: str
    item_type: str  # memory/skill/knowledge
    next_review: float  # 下次复习时间戳
    interval_days: int = 1
    ease_factor: float = 2.5  # 容易度因子
    consecutive_correct: int = 0

    @property
    def is_due(self) -> bool:
        """是否到期"""
        return time.time() >= self.next_review


@dataclass
class ReviewSession:
    """复习会话"""
    start_time: float
    end_time: Optional[float] = None
    items_reviewed: List[str] = field(default_factory=list)
    correct_count: int = 0
    total_count: int = 0

    @property
    def accuracy(self) -> float:
        """正确率"""
        if self.total_count == 0:
            return 0.0
        return self.correct_count / self.total_count


class SpacedRepetitionSystem:
    """间隔重复复习系统

    核心算法 (SM-2变体):
    - EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    - interval = previous_interval * EF
    """

    def __init__(self, notification_callback: Optional[Callable] = None):
        """初始化

        Args:
            notification_callback: 复习提醒回调函数
        """
        self.notification_callback = notification_callback
        self._schedules: Dict[str, ReviewSchedule] = {}
        self._current_session: Optional[ReviewSession] = None
        self._review_history: List[ReviewSession] = []

    def schedule_review(self,
                       item_id: str,
                       item_type: str = "memory",
                       initial_interval: int = 1) -> ReviewSchedule:
        """添加复习计划

        Args:
            item_id: 条目ID
            item_type: 条目类型
            initial_interval: 初始间隔（天）

        Returns:
            ReviewSchedule: 复习计划
        """
        schedule = ReviewSchedule(
            item_id=item_id,
            item_type=item_type,
            next_review=time.time() + initial_interval * 24 * 3600,
            interval_days=initial_interval
        )

        self._schedules[item_id] = schedule
        logger.info(f"安排复习: {item_id[:8]}, 间隔={initial_interval}天")

        return schedule

    def get_due_items(self, limit: int = 20) -> List[ReviewSchedule]:
        """获取到期的复习项

        Args:
            limit: 返回数量

        Returns:
            List[ReviewSchedule]: 到期的复习项
        """
        now = time.time()
        due_items = [
            s for s in self._schedules.values()
            if s.next_review <= now
        ]

        # 按到期时间排序
        due_items.sort(key=lambda x: x.next_review)
        return due_items[:limit]

    def get_upcoming_items(self, hours: int = 24) -> List[ReviewSchedule]:
        """获取即将到期的复习项

        Args:
            hours: 未来多少小时

        Returns:
            List[ReviewSchedule]: 即将到期的项
        """
        now = time.time()
        future = now + hours * 3600

        upcoming = [
            s for s in self._schedules.values()
            if now < s.next_review <= future
        ]

        upcoming.sort(key=lambda x: x.next_review)
        return upcoming

    def start_session(self) -> ReviewSession:
        """开始复习会话"""
        self._current_session = ReviewSession(start_time=time.time())
        logger.info("开始复习会话")
        return self._current_session

    def record_review(self,
                     item_id: str,
                     quality: ReviewQuality) -> ReviewSchedule:
        """记录复习结果

        Args:
            item_id: 条目ID
            quality: 复习质量

        Returns:
            ReviewSchedule: 更新后的计划
        """
        if item_id not in self._schedules:
            raise ValueError(f"复习项不存在: {item_id}")

        schedule = self._schedules[item_id]

        # SM-2算法更新
        q = quality.value  # 0-3

        if q < 2:
            # 失败：重新开始
            schedule.consecutive_correct = 0
            schedule.interval_days = 1
        else:
            # 成功：增加间隔
            schedule.consecutive_correct += 1

            if schedule.consecutive_correct == 1:
                schedule.interval_days = 1
            elif schedule.consecutive_correct == 2:
                schedule.interval_days = 6
            else:
                schedule.interval_days = int(schedule.interval_days * schedule.ease_factor)

        # 更新容易度因子
        schedule.ease_factor = max(
            1.3,
            schedule.ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        )

        # 设置下次复习时间
        schedule.next_review = time.time() + schedule.interval_days * 24 * 3600

        # 更新会话
        if self._current_session:
            self._current_session.items_reviewed.append(item_id)
            self._current_session.total_count += 1
            if q >= 2:
                self._current_session.correct_count += 1

        logger.info(f"复习记录: {item_id[:8]}, quality={q}, next_interval={schedule.interval_days}天")

        return schedule

    def end_session(self) -> ReviewSession:
        """结束复习会话"""
        if self._current_session:
            self._current_session.end_time = time.time()
            self._review_history.append(self._current_session)

            logger.info(
                f"结束复习会话: {self._current_session.correct_count}/"
                f"{self._current_session.total_count}, "
                f"accuracy={self._current_session.accuracy:.1%}"
            )

        session = self._current_session
        self._current_session = None
        return session

    def cancel_review(self, item_id: str) -> bool:
        """取消复习计划

        Args:
            item_id: 条目ID

        Returns:
            bool: 是否成功
        """
        if item_id in self._schedules:
            del self._schedules[item_id]
            logger.info(f"取消复习: {item_id[:8]}")
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        total_schedules = len(self._schedules)
        due_count = len(self.get_due_items(limit=100))

        total_sessions = len(self._review_history)
        avg_accuracy = 0.0
        if total_sessions > 0:
            avg_accuracy = sum(s.accuracy for s in self._review_history) / total_sessions

        return {
            "total_scheduled": total_schedules,
            "due_now": due_count,
            "total_sessions": total_sessions,
            "avg_accuracy": avg_accuracy,
            "total_reviews": sum(s.total_count for s in self._review_history)
        }

    def send_reminders(self) -> int:
        """发送复习提醒

        Returns:
            int: 发送的提醒数量
        """
        due_items = self.get_due_items(limit=50)

        if not due_items:
            return 0

        if self.notification_callback:
            for item in due_items:
                try:
                    self.notification_callback(item)
                except Exception as e:
                    logger.error(f"发送提醒失败: {e}")

        logger.info(f"发送了 {len(due_items)} 个复习提醒")
        return len(due_items)


# 便捷函数
def create_spaced_repetition(callback: Optional[Callable] = None) -> SpacedRepetitionSystem:
    """创建间隔重复系统"""
    return SpacedRepetitionSystem(notification_callback=callback)


def calculate_next_interval(current_interval: int,
                             ease_factor: float,
                             quality: ReviewQuality) -> int:
    """计算下次复习间隔

    Args:
        current_interval: 当前间隔
        ease_factor: 容易度因子
        quality: 复习质量

    Returns:
        int: 下次间隔（天）
    """
    q = quality.value

    if q < 2:
        return 1

    if current_interval == 1:
        return 1
    elif current_interval < 6:
        return 6

    return int(current_interval * ease_factor)