"""
Feedback Loop Processor Tests

Tests for:
- FeedbackClassifier: Feedback type classification
- ActionableExtractor: Extract actionable items from feedback
- ImprovementEngine: System improvement generation
- FeedbackLoopProcessor: Integrated feedback processing
"""
import pytest
from datetime import datetime
from src.agents_v2._archive.feedback.feedback_loop import (
    FeedbackLoopProcessor,
    FeedbackClassifier,
    ActionableExtractor,
    ImprovementEngine,
    UserFeedback,
    ActionableItem,
    SystemImprovement,
    FeedbackResult,
    FeedbackType,
    process_user_feedback,
    create_feedback
)


class TestFeedbackType:
    """FeedbackType Tests"""

    def test_all_types_exist(self):
        """Test all feedback types exist"""
        assert FeedbackType.QUALITY_ISSUE.value == "quality_issue"
        assert FeedbackType.FORMAT_ISSUE.value == "format_issue"
        assert FeedbackType.MISSING_CONTENT.value == "missing_content"
        assert FeedbackType.ACCURACY_ISSUE.value == "accuracy_issue"
        assert FeedbackType.USABILITY_ISSUE.value == "usability_issue"
        assert FeedbackType.FEATURE_REQUEST.value == "feature_request"
        assert FeedbackType.OTHER.value == "other"


class TestFeedbackClassifier:
    """FeedbackClassifier Tests"""

    def setup_method(self):
        self.classifier = FeedbackClassifier()

    def test_classify_quality_issue(self):
        """Test classifying quality issue"""
        feedback = UserFeedback(
            feedback_id="fb1",
            user_id="user1",
            feedback_type=FeedbackType.QUALITY_ISSUE,
            content="论文质量太差，内容不连贯",
            timestamp=datetime.now()
        )
        result = self.classifier.classify(feedback)
        assert result == FeedbackType.QUALITY_ISSUE

    def test_classify_format_issue(self):
        """Test classifying format issue"""
        feedback = UserFeedback(
            feedback_id="fb2",
            user_id="user1",
            feedback_type=FeedbackType.FORMAT_ISSUE,
            content="引用样式和排版需要检查",
            timestamp=datetime.now()
        )
        result = self.classifier.classify(feedback)
        assert result == FeedbackType.FORMAT_ISSUE

    def test_classify_missing_content(self):
        """Test classifying missing content"""
        feedback = UserFeedback(
            feedback_id="fb3",
            user_id="user1",
            feedback_type=FeedbackType.MISSING_CONTENT,
            content="缺少相关文献和参考资料",
            timestamp=datetime.now()
        )
        result = self.classifier.classify(feedback)
        assert result == FeedbackType.MISSING_CONTENT

    def test_classify_accuracy_issue(self):
        """Test classifying accuracy issue"""
        feedback = UserFeedback(
            feedback_id="fb4",
            user_id="user1",
            feedback_type=FeedbackType.ACCURACY_ISSUE,
            content="这篇论文的准确性问题需要关注",
            timestamp=datetime.now()
        )
        result = self.classifier.classify(feedback)
        assert result == FeedbackType.ACCURACY_ISSUE

    def test_classify_usability_issue(self):
        """Test classifying usability issue"""
        feedback = UserFeedback(
            feedback_id="fb5",
            user_id="user1",
            feedback_type=FeedbackType.USABILITY_ISSUE,
            content="系统太难用了",
            timestamp=datetime.now()
        )
        result = self.classifier.classify(feedback)
        assert result == FeedbackType.USABILITY_ISSUE

    def test_classify_feature_request(self):
        """Test classifying feature request"""
        feedback = UserFeedback(
            feedback_id="fb6",
            user_id="user1",
            feedback_type=FeedbackType.FEATURE_REQUEST,
            content="希望添加批量处理功能",
            timestamp=datetime.now()
        )
        result = self.classifier.classify(feedback)
        assert result == FeedbackType.FEATURE_REQUEST

    def test_classify_other(self):
        """Test classifying unknown type"""
        feedback = UserFeedback(
            feedback_id="fb7",
            user_id="user1",
            feedback_type=FeedbackType.OTHER,
            content="一些无关内容xyz",
            timestamp=datetime.now()
        )
        result = self.classifier.classify(feedback)
        assert result == FeedbackType.OTHER

    def test_extract_context(self):
        """Test extracting context from feedback"""
        feedback = UserFeedback(
            feedback_id="fb8",
            user_id="user1",
            feedback_type=FeedbackType.QUALITY_ISSUE,
            content="质量问题",
            timestamp=datetime.now(),
            context={"phase": "writing", "draft_length": 1500}
        )
        context = self.classifier.extract_context(feedback)
        assert "hour" in context
        assert "day_of_week" in context
        assert context["phase"] == "writing"

    def test_categorize_length_short(self):
        """Test categorizing short length"""
        result = self.classifier._categorize_length(300)
        assert result == "short"

    def test_categorize_length_medium(self):
        """Test categorizing medium length"""
        result = self.classifier._categorize_length(1000)
        assert result == "medium"

    def test_categorize_length_long(self):
        """Test categorizing long length"""
        result = self.classifier._categorize_length(3000)
        assert result == "long"


class TestActionableExtractor:
    """ActionableExtractor Tests"""

    def setup_method(self):
        self.extractor = ActionableExtractor()

    def test_extract_quality_items_logic(self):
        """Test extracting logic-related quality items"""
        feedback = UserFeedback(
            feedback_id="fb1",
            user_id="user1",
            feedback_type=FeedbackType.QUALITY_ISSUE,
            content="论文逻辑不连贯",
            timestamp=datetime.now()
        )
        items = self.extractor.extract(feedback)
        assert len(items) > 0
        assert any("logic" in item.item_id for item in items)

    def test_extract_quality_items_redundancy(self):
        """Test extracting redundancy-related quality items"""
        feedback = UserFeedback(
            feedback_id="fb2",
            user_id="user1",
            feedback_type=FeedbackType.QUALITY_ISSUE,
            content="内容有重复",
            timestamp=datetime.now()
        )
        items = self.extractor.extract(feedback)
        assert len(items) > 0
        assert any("redundancy" in item.item_id for item in items)

    def test_extract_format_items_citation(self):
        """Test extracting citation format items"""
        feedback = UserFeedback(
            feedback_id="fb3",
            user_id="user1",
            feedback_type=FeedbackType.FORMAT_ISSUE,
            content="引用格式有问题",
            timestamp=datetime.now()
        )
        items = self.extractor.extract(feedback)
        assert len(items) > 0
        assert any("citation" in item.item_id for item in items)

    def test_extract_content_items_reference(self):
        """Test extracting reference-related content items"""
        feedback = UserFeedback(
            feedback_id="fb4",
            user_id="user1",
            feedback_type=FeedbackType.MISSING_CONTENT,
            content="缺少相关文献",
            timestamp=datetime.now()
        )
        items = self.extractor.extract(feedback)
        assert len(items) > 0
        assert any("ref" in item.item_id for item in items)

    def test_extract_content_items_experiment(self):
        """Test extracting experiment-related content items"""
        feedback = UserFeedback(
            feedback_id="fb5",
            user_id="user1",
            feedback_type=FeedbackType.MISSING_CONTENT,
            content="缺少实验数据",
            timestamp=datetime.now()
        )
        items = self.extractor.extract(feedback)
        assert len(items) > 0
        assert any("experiment" in item.item_id for item in items)

    def test_extract_accuracy_items(self):
        """Test extracting accuracy items"""
        feedback = UserFeedback(
            feedback_id="fb6",
            user_id="user1",
            feedback_type=FeedbackType.ACCURACY_ISSUE,
            content="有事实错误",
            timestamp=datetime.now()
        )
        items = self.extractor.extract(feedback)
        assert len(items) > 0
        assert items[0].category == FeedbackType.ACCURACY_ISSUE

    def test_extract_default_for_unknown_type(self):
        """Test default extraction for unknown type"""
        feedback = UserFeedback(
            feedback_id="fb7",
            user_id="user1",
            feedback_type=FeedbackType.OTHER,
            content="一些无关内容",
            timestamp=datetime.now()
        )
        items = self.extractor.extract(feedback)
        assert len(items) == 1
        assert items[0].priority == "medium"


class TestImprovementEngine:
    """ImprovementEngine Tests"""

    def setup_method(self):
        self.engine = ImprovementEngine()

    @pytest.mark.asyncio
    async def test_suggest_improvement(self):
        """Test suggesting improvement"""
        item = ActionableItem(
            item_id="test_item",
            category=FeedbackType.QUALITY_ISSUE,
            description="测试问题",
            suggested_action="执行测试",
            priority="high",
            confidence=0.8
        )
        improvement = await self.engine.suggest_improvement(item)
        assert improvement is not None
        assert improvement.category == FeedbackType.QUALITY_ISSUE
        assert improvement.implemented is False

    @pytest.mark.asyncio
    async def test_implement_improvement(self):
        """Test implementing improvement"""
        improvement = SystemImprovement(
            improvement_id="imp1",
            category=FeedbackType.QUALITY_ISSUE,
            description="测试改进",
            implemented=False,
            timestamp=datetime.now()
        )
        result = await self.engine.implement_improvement(improvement)
        assert result is True
        assert improvement.implemented is True

    @pytest.mark.asyncio
    async def test_get_pending_improvements(self):
        """Test getting pending improvements"""
        item = ActionableItem(
            item_id="test_item",
            category=FeedbackType.QUALITY_ISSUE,
            description="测试",
            suggested_action="测试",
            priority="high",
            confidence=0.8
        )
        await self.engine.suggest_improvement(item)
        pending = self.engine.get_pending_improvements()
        assert len(pending) == 1


class TestFeedbackLoopProcessor:
    """FeedbackLoopProcessor Tests"""

    def setup_method(self):
        self.processor = FeedbackLoopProcessor()

    @pytest.mark.asyncio
    async def test_process_feedback(self):
        """Test processing feedback"""
        feedback = UserFeedback(
            feedback_id="fb1",
            user_id="user1",
            feedback_type=FeedbackType.QUALITY_ISSUE,
            content="论文质量太差，内容重复较多",
            timestamp=datetime.now()
        )
        result = await self.processor.process(feedback)
        assert result.feedback_id == "fb1"
        assert result.category == FeedbackType.QUALITY_ISSUE
        assert len(result.actionable_items) > 0
        assert result.acknowledgment != ""

    @pytest.mark.asyncio
    async def test_process_and_store(self):
        """Test that feedback is stored"""
        feedback = UserFeedback(
            feedback_id="fb2",
            user_id="user1",
            feedback_type=FeedbackType.FORMAT_ISSUE,
            content="样式需要改进",
            timestamp=datetime.now()
        )
        await self.processor.process(feedback)
        summary = self.processor.get_feedback_summary()
        assert summary["total"] == 1

    def test_get_feedback_summary_empty(self):
        """Test getting summary with no feedback"""
        processor = FeedbackLoopProcessor()
        summary = processor.get_feedback_summary()
        assert summary["total"] == 0
        assert summary["by_type"] == {}

    @pytest.mark.asyncio
    async def test_get_feedback_summary_with_data(self):
        """Test getting summary with feedback"""
        for i in range(3):
            feedback = UserFeedback(
                feedback_id=f"fb{i}",
                user_id="user1",
                feedback_type=FeedbackType.QUALITY_ISSUE,
                content="质量问题",
                timestamp=datetime.now()
            )
            await self.processor.process(feedback)

        summary = self.processor.get_feedback_summary()
        assert summary["total"] == 3
        assert "quality_issue" in summary["by_type"]
        assert summary["by_type"]["quality_issue"] == 3

    @pytest.mark.asyncio
    async def test_get_improvement_stats(self):
        """Test getting improvement statistics"""
        item = ActionableItem(
            item_id="test_item",
            category=FeedbackType.QUALITY_ISSUE,
            description="测试",
            suggested_action="测试",
            priority="high",
            confidence=0.8
        )
        await self.processor.improvement_engine.suggest_improvement(item)

        stats = self.processor.get_improvement_stats()
        assert "total_improvements" in stats
        assert "implemented" in stats
        assert "pending" in stats

    def test_generate_acknowledgment_quality(self):
        """Test acknowledgment generation for quality issue"""
        feedback = UserFeedback(
            feedback_id="fb1",
            user_id="user1",
            feedback_type=FeedbackType.QUALITY_ISSUE,
            content="质量问题",
            timestamp=datetime.now()
        )
        acknowledgment = self.processor._generate_acknowledgment(
            feedback,
            FeedbackType.QUALITY_ISSUE,
            []
        )
        assert "质量" in acknowledgment

    def test_generate_acknowledgment_with_items(self):
        """Test acknowledgment generation with actionable items"""
        feedback = UserFeedback(
            feedback_id="fb1",
            user_id="user1",
            feedback_type=FeedbackType.QUALITY_ISSUE,
            content="质量问题",
            timestamp=datetime.now()
        )
        items = [
            ActionableItem("item1", FeedbackType.QUALITY_ISSUE, "desc", "action", "high", 0.8),
            ActionableItem("item2", FeedbackType.QUALITY_ISSUE, "desc2", "action2", "medium", 0.7),
        ]
        acknowledgment = self.processor._generate_acknowledgment(
            feedback,
            FeedbackType.QUALITY_ISSUE,
            items
        )
        assert "2" in acknowledgment  # Should mention 2 items


class TestCreateFeedbackConvenience:
    """Test create_feedback convenience function"""

    def test_create_feedback_basic(self):
        """Test basic feedback creation"""
        feedback = create_feedback(
            user_id="user1",
            content="测试反馈"
        )
        assert feedback.user_id == "user1"
        assert feedback.content == "测试反馈"
        assert feedback.feedback_id.startswith("fb_")

    def test_create_feedback_with_type(self):
        """Test feedback creation with type"""
        feedback = create_feedback(
            user_id="user1",
            content="格式问题",
            feedback_type="format_issue"
        )
        assert feedback.feedback_type == FeedbackType.FORMAT_ISSUE

    def test_create_feedback_with_context(self):
        """Test feedback creation with context"""
        feedback = create_feedback(
            user_id="user1",
            content="质量问题",
            context={"phase": "writing"}
        )
        assert feedback.context["phase"] == "writing"


class TestProcessUserFeedbackConvenience:
    """Test process_user_feedback convenience function"""

    @pytest.mark.asyncio
    async def test_process_user_feedback(self):
        """Test convenience function for processing feedback"""
        feedback = UserFeedback(
            feedback_id="fb1",
            user_id="user1",
            feedback_type=FeedbackType.QUALITY_ISSUE,
            content="测试",
            timestamp=datetime.now()
        )
        result = await process_user_feedback(feedback)
        assert result.feedback_id == "fb1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])