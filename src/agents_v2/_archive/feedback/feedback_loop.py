"""
反馈闭环处理器

功能:
1. 分类反馈类型
2. 提取引用可操作项
3. 执行改进
4. 更新用户偏好

设计原则:
- 快速响应用户反馈
- 从反馈中学习并改进系统
- 保持透明的用户沟通
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """反馈类型"""
    QUALITY_ISSUE = "quality_issue"     # 质量问题
    FORMAT_ISSUE = "format_issue"       # 格式问题
    MISSING_CONTENT = "missing_content"  # 内容缺失
    ACCURACY_ISSUE = "accuracy_issue"   # 准确性问题
    USABILITY_ISSUE = "usability_issue"  # 可用性问题
    FEATURE_REQUEST = "feature_request"  # 功能请求
    OTHER = "other"


@dataclass
class UserFeedback:
    """用户反馈"""
    feedback_id: str
    user_id: str
    feedback_type: FeedbackType
    content: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    attachment: Optional[str] = None  # 可能的附件


@dataclass
class ActionableItem:
    """可操作项"""
    item_id: str
    category: FeedbackType
    description: str
    suggested_action: str
    priority: str  # "high", "medium", "low"
    confidence: float


@dataclass
class SystemImprovement:
    """系统改进"""
    improvement_id: str
    category: FeedbackType
    description: str
    implemented: bool
    timestamp: datetime
    success_metric: Optional[float] = None


@dataclass
class FeedbackResult:
    """反馈处理结果"""
    feedback_id: str
    category: FeedbackType
    actionable_items: List[ActionableItem]
    improvements: List[SystemImprovement]
    acknowledgment: str
    processed_at: datetime


class FeedbackClassifier:
    """反馈分类器"""

    # 分类关键词
    CLASSIFICATION_KEYWORDS = {
        FeedbackType.QUALITY_ISSUE: [
            "质量", "差", "不好", "low quality", "poor",
            "不正确", "错误", "inaccurate", "wrong"
        ],
        FeedbackType.FORMAT_ISSUE: [
            "格式", "样式", "排版", "format", "style",
            "字体", "layout", "外观"
        ],
        FeedbackType.MISSING_CONTENT: [
            "缺少", "没有", "缺失", "missing", "lack",
            "不完整", "不够", "incomplete"
        ],
        FeedbackType.ACCURACY_ISSUE: [
            "准确", "错误", "factual", "incorrect",
            "事实错误", "事实不符", "error"
        ],
        FeedbackType.USABILITY_ISSUE: [
            "难用", "不方便", "复杂", "difficult", "complex",
            "不清楚", "confusing", "unclear"
        ],
        FeedbackType.FEATURE_REQUEST: [
            "希望", "想要", "添加", "功能", "feature",
            "建议", "suggest", "want", "need"
        ],
    }

    def classify(self, feedback: UserFeedback) -> FeedbackType:
        """分类反馈

        Args:
            feedback: 用户反馈

        Returns:
            FeedbackType: 反馈类型
        """
        content_lower = feedback.content.lower()

        # 检查每个类型的关键词
        for ftype, keywords in self.CLASSIFICATION_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                return ftype

        return FeedbackType.OTHER

    def extract_context(self, feedback: UserFeedback) -> Dict[str, Any]:
        """提取引用上下文

        用于后续分析和改进
        """
        context = feedback.context.copy()

        # 添加时间信息
        context["hour"] = feedback.timestamp.hour
        context["day_of_week"] = feedback.timestamp.weekday()

        # 提取关键信息
        if feedback.context.get("phase"):
            context["phase"] = feedback.context.get("phase")

        if feedback.context.get("draft_length"):
            context["draft_length_category"] = self._categorize_length(
                feedback.context.get("draft_length", 0)
            )

        return context

    def _categorize_length(self, length: int) -> str:
        """分类长度"""
        if length < 500:
            return "short"
        elif length < 2000:
            return "medium"
        else:
            return "long"


class ActionableExtractor:
    """可操作项提取器"""

    def __init__(self):
        self._extractors = {
            FeedbackType.QUALITY_ISSUE: self._extract_quality_items,
            FeedbackType.FORMAT_ISSUE: self._extract_format_items,
            FeedbackType.MISSING_CONTENT: self._extract_content_items,
            FeedbackType.ACCURACY_ISSUE: self._extract_accuracy_items,
        }

    def extract(self, feedback: UserFeedback) -> List[ActionableItem]:
        """提取引用可操作项

        Args:
            feedback: 用户反馈

        Returns:
            List[ActionableItem]: 可操作项列表
        """
        extractor = self._extractors.get(feedback.feedback_type)
        if extractor:
            return extractor(feedback)

        # 默认返回通用项
        return [ActionableItem(
            item_id=f"generic_{feedback.feedback_id}",
            category=feedback.feedback_type,
            description=feedback.content[:100],
            suggested_action="需要人工审核",
            priority="medium",
            confidence=0.5
        )]

    def _extract_quality_items(self, feedback: UserFeedback) -> List[ActionableItem]:
        """提取质量问题项"""
        items = []

        content = feedback.content.lower()

        if any(kw in content for kw in ["逻辑", "logic", "不连贯", "incoherent"]):
            items.append(ActionableItem(
                item_id=f"logic_{feedback.feedback_id}",
                category=FeedbackType.QUALITY_ISSUE,
                description="逻辑不连贯问题",
                suggested_action="增强逻辑检查器",
                priority="high",
                confidence=0.8
            ))

        if any(kw in content for kw in ["重复", "repeat", "冗余", "redundant"]):
            items.append(ActionableItem(
                item_id=f"redundancy_{feedback.feedback_id}",
                category=FeedbackType.QUALITY_ISSUE,
                description="内容重复问题",
                suggested_action="增强重复检测",
                priority="medium",
                confidence=0.7
            ))

        if any(kw in content for kw in ["模糊", "不清楚", "unclear", "vague"]):
            items.append(ActionableItem(
                item_id=f"clarity_{feedback.feedback_id}",
                category=FeedbackType.QUALITY_ISSUE,
                description="表达不清楚",
                suggested_action="增强语言清晰度检查",
                priority="medium",
                confidence=0.7
            ))

        return items

    def _extract_format_items(self, feedback: UserFeedback) -> List[ActionableItem]:
        """提取格式问题项"""
        items = []

        content = feedback.content.lower()

        if any(kw in content for kw in ["引用", "citation", "格式"]):
            items.append(ActionableItem(
                item_id=f"citation_{feedback.feedback_id}",
                category=FeedbackType.FORMAT_ISSUE,
                description="引用格式问题",
                suggested_action="检查引用格式转换器",
                priority="medium",
                confidence=0.8
            ))

        if any(kw in content for kw in ["表格", "table", "图表"]):
            items.append(ActionableItem(
                item_id=f"table_{feedback.feedback_id}",
                category=FeedbackType.FORMAT_ISSUE,
                description="表格格式问题",
                suggested_action="检查表格导出器",
                priority="low",
                confidence=0.6
            ))

        return items

    def _extract_content_items(self, feedback: UserFeedback) -> List[ActionableItem]:
        """提取内容缺失项"""
        items = []

        content = feedback.content.lower()

        if any(kw in content for kw in ["文献", "reference", "论文"]):
            items.append(ActionableItem(
                item_id=f"ref_{feedback.feedback_id}",
                category=FeedbackType.MISSING_CONTENT,
                description="缺少相关文献",
                suggested_action="增强文献检索能力",
                priority="high",
                confidence=0.7
            ))

        if any(kw in content for kw in ["数据", "data", "实验"]):
            items.append(ActionableItem(
                item_id=f"experiment_{feedback.feedback_id}",
                category=FeedbackType.MISSING_CONTENT,
                description="缺少实验数据",
                suggested_action="增强实验数据生成",
                priority="medium",
                confidence=0.6
            ))

        return items

    def _extract_accuracy_items(self, feedback: UserFeedback) -> List[ActionableItem]:
        """提取准确性问题项"""
        items = []

        items.append(ActionableItem(
            item_id=f"accuracy_{feedback.feedback_id}",
            category=FeedbackType.ACCURACY_ISSUE,
            description="事实性错误",
            suggested_action="增强事实核查",
            priority="high",
            confidence=0.8
        ))

        return items


class ImprovementEngine:
    """改进引擎

    根据反馈生成和实施系统改进
    """

    def __init__(self):
        self._improvements: List[SystemImprovement] = []

    async def suggest_improvement(
        self,
        item: ActionableItem
    ) -> Optional[SystemImprovement]:
        """建议改进

        Args:
            item: 可操作项

        Returns:
            Optional[SystemImprovement]: 改进建议
        """
        improvement = SystemImprovement(
            improvement_id=f"imp_{item.item_id}",
            category=item.category,
            description=f"根据'{item.description}'建议: {item.suggested_action}",
            implemented=False,
            timestamp=datetime.now(),
            success_metric=None
        )

        self._improvements.append(improvement)

        return improvement

    async def implement_improvement(
        self,
        improvement: SystemImprovement
    ) -> bool:
        """实施改进

        Args:
            improvement: 改进

        Returns:
            bool: 是否成功
        """
        # 简单的实施逻辑
        try:
            # 实际应该调用相关模块进行改进
            logger.info(f"Implementing improvement: {improvement.description}")

            improvement.implemented = True
            return True

        except Exception as e:
            logger.error(f"Implementation failed: {e}")
            return False

    def get_pending_improvements(self) -> List[SystemImprovement]:
        """获取待实施的改进"""
        return [i for i in self._improvements if not i.implemented]


class FeedbackLoopProcessor:
    """反馈闭环处理器

    整合分类、提取、改进功能
    """

    def __init__(self):
        self.classifier = FeedbackClassifier()
        self.extractor = ActionableExtractor()
        self.improvement_engine = ImprovementEngine()
        self._feedback_store: List[UserFeedback] = []

    async def process(
        self,
        feedback: UserFeedback
    ) -> FeedbackResult:
        """处理反馈

        Args:
            feedback: 用户反馈

        Returns:
            FeedbackResult: 处理结果
        """
        # 1. 分类反馈
        category = self.classifier.classify(feedback)

        # 2. 提取上下文
        context = self.classifier.extract_context(feedback)

        # 3. 提取引用可操作项
        actionable = self.extractor.extract(feedback)

        # 4. 建议改进
        improvements = []
        for item in actionable:
            improvement = await self.improvement_engine.suggest_improvement(item)
            if improvement:
                improvements.append(improvement)

        # 5. 生成确认消息
        acknowledgment = self._generate_acknowledgment(feedback, category, actionable)

        # 6. 记录反馈
        self._feedback_store.append(feedback)

        return FeedbackResult(
            feedback_id=feedback.feedback_id,
            category=category,
            actionable_items=actionable,
            improvements=improvements,
            acknowledgment=acknowledgment,
            processed_at=datetime.now()
        )

    def _generate_acknowledgment(
        self,
        feedback: UserFeedback,
        category: FeedbackType,
        actionable: List[ActionableItem]
    ) -> str:
        """生成确认消息"""
        acknowledgments = {
            FeedbackType.QUALITY_ISSUE: "感谢您的质量反馈，我们将重点改进写作质量。",
            FeedbackType.FORMAT_ISSUE: "感谢您指出格式问题，我们已记录并会改进。",
            FeedbackType.MISSING_CONTENT: "感谢您的反馈，我们会增强内容完整性。",
            FeedbackType.ACCURACY_ISSUE: "感谢您指出准确性问题，我们非常重视事实核查。",
            FeedbackType.USABILITY_ISSUE: "感谢您的可用性反馈，我们会优化用户体验。",
            FeedbackType.FEATURE_REQUEST: "感谢您的功能建议，我们会认真评估。",
            FeedbackType.OTHER: "感谢您的反馈，我们会持续改进。"
        }

        base_msg = acknowledgments.get(category, acknowledgments[FeedbackType.OTHER])

        # 添加具体信息
        if actionable:
            count = len(actionable)
            base_msg += f" 已识别出{count}个可改进点。"

        return base_msg

    def get_feedback_summary(self) -> Dict[str, Any]:
        """获取反馈摘要"""
        if not self._feedback_store:
            return {"total": 0, "by_type": {}}

        type_counts = {}
        for feedback in self._feedback_store:
            ftype = feedback.feedback_type.value
            type_counts[ftype] = type_counts.get(ftype, 0) + 1

        return {
            "total": len(self._feedback_store),
            "by_type": type_counts,
            "recent": [
                {"id": f.feedback_id, "type": f.feedback_type.value, "content": f.content[:50]}
                for f in self._feedback_store[-5:]
            ]
        }

    def get_improvement_stats(self) -> Dict[str, Any]:
        """获取改进统计"""
        improvements = self.improvement_engine._improvements

        return {
            "total_improvements": len(improvements),
            "implemented": sum(1 for i in improvements if i.implemented),
            "pending": sum(1 for i in improvements if not i.implemented)
        }


# 便捷函数
async def process_user_feedback(
    feedback: UserFeedback
) -> FeedbackResult:
    """处理用户反馈的便捷函数"""
    processor = FeedbackLoopProcessor()
    return await processor.process(feedback)


def create_feedback(
    user_id: str,
    content: str,
    feedback_type: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> UserFeedback:
    """创建反馈的便捷函数"""
    feedback_id = f"fb_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 分类
    classifier = FeedbackClassifier()

    inferred_type = FeedbackType.QUALITY_ISSUE
    if feedback_type:
        try:
            inferred_type = FeedbackType(feedback_type)
        except ValueError:
            pass

    return UserFeedback(
        feedback_id=feedback_id,
        user_id=user_id,
        feedback_type=inferred_type,
        content=content,
        timestamp=datetime.now(),
        context=context or {}
    )