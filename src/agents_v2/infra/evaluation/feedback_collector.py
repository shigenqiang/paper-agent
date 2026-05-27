"""
反馈收集器 - Feedback Collector

功能:
1. 用户反馈收集
2. 反馈分类与优先级
3. 反馈分析
4. 改进建议生成

设计原则:
- 多维度反馈收集
- 自动分类与优先级判定
- 可配置的反馈处理流程
"""
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from datetime import datetime


class FeedbackType(str, Enum):
    """反馈类型"""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    USABILITY_ISSUE = "usability_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    CONTENT_QUALITY = "content_quality"
    OTHER = "other"


class FeedbackPriority(int, Enum):
    """反馈优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class FeedbackStatus(str, Enum):
    """反馈状态"""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Feedback:
    """反馈数据"""
    id: str
    type: FeedbackType
    title: str
    description: str
    priority: FeedbackPriority
    status: FeedbackStatus
    created_at: str
    updated_at: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    related_items: List[str] = field(default_factory=list)
    resolved_at: Optional[str] = None


@dataclass
class FeedbackSummary:
    """反馈摘要"""
    total: int
    by_type: Dict[str, int]
    by_priority: Dict[str, int]
    by_status: Dict[str, int]
    recent_trends: List[Dict[str, Any]]


class FeedbackCollector:
    """反馈收集器"""

    def __init__(self):
        self._feedbacks: Dict[str, Feedback] = {}
        self._handlers: Dict[FeedbackType, List[Callable]] = defaultdict(list)

    def add_feedback(
        self,
        feedback_type: FeedbackType,
        title: str,
        description: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        related_items: Optional[List[str]] = None
    ) -> Feedback:
        """添加反馈

        Args:
            feedback_type: 反馈类型
            title: 标题
            description: 描述
            user_id: 用户ID
            session_id: 会话ID
            metadata: 元数据
            tags: 标签
            related_items: 关联项目

        Returns:
            Feedback: 创建的反馈
        """
        feedback_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # 自动计算优先级
        priority = self._calculate_priority(feedback_type, title, description)

        feedback = Feedback(
            id=feedback_id,
            type=feedback_type,
            title=title,
            description=description,
            priority=priority,
            status=FeedbackStatus.NEW,
            created_at=now,
            updated_at=now,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
            related_items=related_items or []
        )

        self._feedbacks[feedback_id] = feedback

        # 触发处理程序
        self._trigger_handlers(feedback)

        return feedback

    def _calculate_priority(
        self,
        feedback_type: FeedbackType,
        title: str,
        description: str
    ) -> FeedbackPriority:
        """计算优先级"""
        # 类型基础优先级
        type_priority = {
            FeedbackType.BUG_REPORT: FeedbackPriority.HIGH,
            FeedbackType.PERFORMANCE_ISSUE: FeedbackPriority.HIGH,
            FeedbackType.FEATURE_REQUEST: FeedbackPriority.MEDIUM,
            FeedbackType.USABILITY_ISSUE: FeedbackPriority.MEDIUM,
            FeedbackType.CONTENT_QUALITY: FeedbackPriority.LOW,
            FeedbackType.OTHER: FeedbackPriority.LOW
        }

        priority = type_priority.get(feedback_type, FeedbackPriority.MEDIUM)

        # 关键词调整
        critical_keywords = ["crash", "error", "fail", "broken", "无法", "错误", "崩溃"]
        high_keywords = ["slow", "delay", "问题", "性能"]

        desc_lower = (title + description).lower()

        for keyword in critical_keywords:
            if keyword in desc_lower:
                priority = FeedbackPriority.CRITICAL
                break

        for keyword in high_keywords:
            if keyword in desc_lower and priority < FeedbackPriority.HIGH:
                priority = FeedbackPriority.HIGH

        return priority

    def update_status(
        self,
        feedback_id: str,
        status: FeedbackStatus
    ) -> bool:
        """更新反馈状态

        Args:
            feedback_id: 反馈ID
            status: 新状态

        Returns:
            bool: 是否成功
        """
        if feedback_id not in self._feedbacks:
            return False

        feedback = self._feedbacks[feedback_id]
        feedback.status = status
        feedback.updated_at = datetime.now().isoformat()

        if status == FeedbackStatus.RESOLVED:
            feedback.resolved_at = datetime.now().isoformat()

        return True

    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        """获取反馈"""
        return self._feedbacks.get(feedback_id)

    def get_feedbacks(
        self,
        feedback_type: Optional[FeedbackType] = None,
        status: Optional[FeedbackStatus] = None,
        priority: Optional[FeedbackPriority] = None,
        limit: int = 100
    ) -> List[Feedback]:
        """获取反馈列表

        Args:
            feedback_type: 按类型筛选
            status: 按状态筛选
            priority: 按优先级筛选
            limit: 返回数量限制

        Returns:
            List[Feedback]: 反馈列表
        """
        results = list(self._feedbacks.values())

        if feedback_type:
            results = [f for f in results if f.type == feedback_type]

        if status:
            results = [f for f in results if f.status == status]

        if priority:
            results = [f for f in results if f.priority == priority]

        # 按创建时间倒序
        results.sort(key=lambda x: x.created_at, reverse=True)

        return results[:limit]

    def get_summary(self) -> FeedbackSummary:
        """获取反馈摘要

        Returns:
            FeedbackSummary: 反馈摘要
        """
        feedbacks = list(self._feedbacks.values())

        by_type = defaultdict(int)
        by_priority = defaultdict(int)
        by_status = defaultdict(int)

        for f in feedbacks:
            by_type[f.type.value] += 1
            by_priority[f.priority.name] += 1
            by_status[f.status.value] += 1

        return FeedbackSummary(
            total=len(feedbacks),
            by_type=dict(by_type),
            by_priority=dict(by_priority),
            by_status=dict(by_status),
            recent_trends=self._calculate_trends()
        )

    def _calculate_trends(self) -> List[Dict[str, Any]]:
        """计算趋势"""
        # 按天统计反馈数量
        daily_counts = defaultdict(int)

        for f in self._feedbacks.values():
            day = f.created_at[:10]  # YYYY-MM-DD
            daily_counts[day] += 1

        trends = [
            {"date": date, "count": count}
            for date, count in sorted(daily_counts.items())[-7:]
        ]

        return trends

    def register_handler(
        self,
        feedback_type: FeedbackType,
        handler: Callable[[Feedback], None]
    ) -> None:
        """注册反馈处理程序

        Args:
            feedback_type: 反馈类型
            handler: 处理函数
        """
        self._handlers[feedback_type].append(handler)

    def _trigger_handlers(self, feedback: Feedback) -> None:
        """触发处理程序"""
        for handler in self._handlers[feedback.type]:
            try:
                handler(feedback)
            except Exception:
                pass

    def delete_feedback(self, feedback_id: str) -> bool:
        """删除反馈"""
        if feedback_id in self._feedbacks:
            del self._feedbacks[feedback_id]
            return True
        return False

    def add_comment(
        self,
        feedback_id: str,
        comment: str,
        user_id: Optional[str] = None
    ) -> bool:
        """添加评论

        Args:
            feedback_id: 反馈ID
            comment: 评论内容
            user_id: 用户ID

        Returns:
            bool: 是否成功
        """
        if feedback_id not in self._feedbacks:
            return False

        feedback = self._feedbacks[feedback_id]
        feedback.metadata.setdefault("comments", []).append({
            "text": comment,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        feedback.updated_at = datetime.now().isoformat()

        return True


class FeedbackAnalyzer:
    """反馈分析器"""

    def __init__(self, collector: FeedbackCollector):
        self.collector = collector

    def analyze_common_issues(self) -> Dict[str, Any]:
        """分析常见问题"""
        feedbacks = self.collector.get_feedbacks(limit=1000)

        # 按类型统计
        type_counts = defaultdict(int)
        # 关键词统计
        keyword_counts = defaultdict(int)

        critical_keywords = ["crash", "error", "慢", "卡", "无响应"]

        for f in feedbacks:
            type_counts[f.type.value] += 1

            text = (f.title + " " + f.description).lower()
            for keyword in critical_keywords:
                if keyword in text:
                    keyword_counts[keyword] += 1

        return {
            "type_distribution": dict(type_counts),
            "keyword_frequency": dict(keyword_counts),
            "total_feedbacks": len(feedbacks)
        }

    def get_improvement_suggestions(self) -> List[str]:
        """生成改进建议"""
        suggestions = []
        summary = self.collector.get_summary()

        # 基于优先级生成建议
        high_priority_count = summary.by_priority.get("HIGH", 0)
        critical_count = summary.by_priority.get("CRITICAL", 0)

        if critical_count > 0:
            suggestions.append(f"有 {critical_count} 个关键问题需要立即处理")

        if high_priority_count > 5:
            suggestions.append("高优先级问题较多，建议优先处理")

        # 基于类型生成建议
        bug_count = summary.by_type.get("bug_report", 0)
        if bug_count > 10:
            suggestions.append("Bug报告较多，建议进行系统性代码审查")

        performance_count = summary.by_type.get("performance_issue", 0)
        if performance_count > 5:
            suggestions.append("性能问题频繁出现，建议优化关键路径")

        return suggestions


# 便捷函数
def collect_feedback(
    feedback_type: FeedbackType,
    title: str,
    description: str,
    **kwargs
) -> Feedback:
    """便捷反馈收集函数"""
    collector = FeedbackCollector()
    return collector.add_feedback(feedback_type, title, description, **kwargs)
