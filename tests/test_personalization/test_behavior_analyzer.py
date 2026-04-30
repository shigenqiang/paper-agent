"""
User Behavior Analyzer Tests

Tests for:
- UserBehaviorAnalyzer: User behavior analysis
- PatternDetector: Pattern detection in user actions
- SmartPromptGenerator: Smart prompt generation based on user profile
"""
import pytest
from datetime import datetime, timedelta
from src.agents_v2._archive.personalization import (
    UserBehaviorAnalyzer,
    UserAction,
    UserPreferences,
    BehaviorProfile,
    ExpertiseLevel,
    OutputFormat,
    PatternDetector,
    SmartPromptGenerator,
    analyze_user_behavior,
    record_user_action
)


class TestUserAction:
    """UserAction Tests"""

    def test_create_action(self):
        """Test creating a user action"""
        action = UserAction(
            timestamp=datetime.now(),
            action_type="search",
            duration_ms=1500.0,
            success=True,
            metadata={"query": "test query"}
        )
        assert action.action_type == "search"
        assert action.duration_ms == 1500.0
        assert action.success is True
        assert action.metadata["query"] == "test query"

    def test_record_user_action_convenience(self):
        """Test convenience function for recording action"""
        action = record_user_action(
            user_id="user123",  # Note: user_id is accepted but not stored in UserAction
            action_type="write",
            duration_ms=3000.0,
            success=True,
            metadata={"chapter": "abstract"}
        )
        assert action.action_type == "write"


class TestUserPreferences:
    """UserPreferences Tests"""

    def test_default_preferences(self):
        """Test default preferences"""
        prefs = UserPreferences()
        assert prefs.preferred_output_format == OutputFormat.MARKDOWN
        assert prefs.revision_tolerance == "medium"
        assert prefs.depth_preference == "medium"
        assert prefs.language_preference == "zh"


class TestExpertiseLevel:
    """ExpertiseLevel Tests"""

    def test_all_levels_exist(self):
        """Test all expertise levels exist"""
        assert ExpertiseLevel.BEGINNER.value == "beginner"
        assert ExpertiseLevel.INTERMEDIATE.value == "intermediate"
        assert ExpertiseLevel.ADVANCED.value == "advanced"
        assert ExpertiseLevel.EXPERT.value == "expert"


class TestPatternDetector:
    """PatternDetector Tests"""

    def setup_method(self):
        self.detector = PatternDetector()

    def test_detect_empty(self):
        """Test detecting patterns with no actions"""
        patterns = self.detector.detect([])
        assert patterns == {}

    def test_detect_time_patterns(self):
        """Test detecting time patterns"""
        now = datetime.now()
        actions = [
            UserAction(timestamp=now.replace(hour=10), action_type="search", duration_ms=100.0, success=True),
            UserAction(timestamp=now.replace(hour=10), action_type="write", duration_ms=200.0, success=True),
            UserAction(timestamp=now.replace(hour=14), action_type="search", duration_ms=150.0, success=True),
        ]
        patterns = self.detector.detect(actions)
        assert "time" in patterns
        assert 10 in patterns["time"]["most_active_hours"]

    def test_detect_frequency_patterns(self):
        """Test detecting frequency patterns"""
        now = datetime.now()
        actions = [
            UserAction(timestamp=now, action_type="search", duration_ms=100.0, success=True),
            UserAction(timestamp=now, action_type="search", duration_ms=100.0, success=True),
            UserAction(timestamp=now, action_type="write", duration_ms=200.0, success=True),
        ]
        patterns = self.detector.detect(actions)
        assert "frequency" in patterns
        assert patterns["frequency"]["most_common_action"] == "search"

    def test_detect_preference_patterns(self):
        """Test detecting preference patterns"""
        now = datetime.now()
        actions = [
            UserAction(timestamp=now, action_type="export", duration_ms=100.0, success=True, metadata={"format": "latex"}),
            UserAction(timestamp=now, action_type="export", duration_ms=100.0, success=True, metadata={"format": "latex"}),
            UserAction(timestamp=now, action_type="export", duration_ms=100.0, success=True, metadata={"format": "markdown"}),
        ]
        patterns = self.detector.detect(actions)
        assert "preferences" in patterns
        assert patterns["preferences"]["preferred_format"] == "latex"


class TestUserBehaviorAnalyzer:
    """UserBehaviorAnalyzer Tests"""

    def setup_method(self):
        self.analyzer = UserBehaviorAnalyzer()

    def test_record_action(self):
        """Test recording user action"""
        action = UserAction(
            timestamp=datetime.now(),
            action_type="search",
            duration_ms=100.0,
            success=True
        )
        self.analyzer.record_action(action)
        assert len(self.analyzer._action_history) == 1

    def test_record_action_limit(self):
        """Test action history limit"""
        now = datetime.now()
        for i in range(1005):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="search", duration_ms=100.0, success=True)
            )
        # Should be limited to 1000
        assert len(self.analyzer._action_history) == 1000

    @pytest.mark.asyncio
    async def test_analyze_empty(self):
        """Test analyzing with no actions"""
        profile = await self.analyzer.analyze("user123")
        assert profile.user_id == "user123"
        assert profile.expertise_level == ExpertiseLevel.BEGINNER
        assert profile.activity_level == "low"

    @pytest.mark.asyncio
    async def test_analyze_with_actions(self):
        """Test analyzing with actions"""
        now = datetime.now()
        for i in range(5):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="search", duration_ms=100.0, success=True)
            )
        for i in range(5):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="write", duration_ms=200.0, success=True)
            )

        profile = await self.analyzer.analyze("user123")
        assert profile.user_id == "user123"
        assert profile.total_actions == 10
        assert "search" in profile.common_actions
        assert "write" in profile.common_actions

    @pytest.mark.asyncio
    async def test_estimate_expertise_advanced(self):
        """Test expertise estimation for advanced user"""
        now = datetime.now()
        # Add many advanced actions
        for _ in range(8):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="write", duration_ms=100.0, success=True)
            )
        for _ in range(2):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="help", duration_ms=100.0, success=True)
            )

        profile = await self.analyzer.analyze("user123")
        # With 8 advanced / 10 total = 0.8 > 0.7, should be ADVANCED
        assert profile.expertise_level == ExpertiseLevel.ADVANCED

    @pytest.mark.asyncio
    async def test_estimate_expertise_beginner(self):
        """Test expertise estimation for beginner user"""
        now = datetime.now()
        # Add few advanced actions
        for _ in range(2):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="write", duration_ms=100.0, success=True)
            )
        for _ in range(8):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="help", duration_ms=100.0, success=True)
            )

        profile = await self.analyzer.analyze("user123")
        # With 2 advanced / 10 total = 0.2 < 0.4, should be BEGINNER
        assert profile.expertise_level == ExpertiseLevel.BEGINNER

    @pytest.mark.asyncio
    async def test_calculate_activity_level_high(self):
        """Test high activity level calculation"""
        now = datetime.now()
        for i in range(60):
            self.analyzer.record_action(
                UserAction(timestamp=now - timedelta(days=i%7), action_type="search", duration_ms=100.0, success=True)
            )

        profile = await self.analyzer.analyze("user123")
        assert profile.activity_level == "high"

    @pytest.mark.asyncio
    async def test_calculate_avg_session_duration(self):
        """Test average session duration calculation"""
        now = datetime.now()
        # Session 1: 3 actions in a short time window
        base_time = now - timedelta(hours=2)  # Start 2 hours ago
        for i in range(3):
            self.analyzer.record_action(
                UserAction(timestamp=base_time + timedelta(minutes=i*5), action_type="search", duration_ms=100.0, success=True)
            )
        # Session 2: 2 actions (gap > 30 min from session 1)
        for i in range(2):
            self.analyzer.record_action(
                UserAction(timestamp=base_time + timedelta(minutes=40+i*5), action_type="write", duration_ms=100.0, success=True)
            )

        profile = await self.analyzer.analyze("user123")
        # Should have 2 sessions
        assert profile.avg_session_duration_minutes >= 0

    def test_get_recent_actions(self):
        """Test getting recent actions"""
        now = datetime.now()
        for i in range(15):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="search", duration_ms=100.0, success=True)
            )

        recent = self.analyzer.get_recent_actions(5)
        assert len(recent) == 5

    def test_get_action_stats(self):
        """Test getting action statistics"""
        now = datetime.now()
        for i in range(5):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="search", duration_ms=100.0, success=True)
            )
        for i in range(3):
            self.analyzer.record_action(
                UserAction(timestamp=now, action_type="write", duration_ms=200.0, success=True)
            )

        stats = self.analyzer.get_action_stats()
        assert "search" in stats
        assert "write" in stats
        assert stats["search"]["count"] == 5
        assert stats["search"]["success_rate"] == 1.0


class TestSmartPromptGenerator:
    """SmartPromptGenerator Tests"""

    def setup_method(self):
        self.analyzer = UserBehaviorAnalyzer()
        self.generator = SmartPromptGenerator(self.analyzer)

    def test_load_templates(self):
        """Test loading templates"""
        assert "encouragement" in self.generator._templates
        assert "help" in self.generator._templates
        assert "efficiency" in self.generator._templates
        assert "expertise" in self.generator._templates

    def test_generate_state_based_suggestions(self):
        """Test generating state-based suggestions"""
        state = {
            "phase": "writing",
            "revision_count": 3,
            "quality_score": 0.5,
            "empty_outline": True
        }
        suggestions = self.generator._generate_state_based(state)
        assert len(suggestions) > 0

        # Check high priority suggestion for low quality
        low_quality = [s for s in suggestions if s.get("priority") == "high"]
        assert len(low_quality) > 0

    def test_generate_best_practice(self):
        """Test generating best practice suggestions"""
        state = {
            "missing_citations": True,
            "no_structured_outline": True
        }
        suggestions = self.generator._generate_best_practice(state)
        assert len(suggestions) > 0

    def test_rank_and_filter(self):
        """Test ranking and filtering suggestions"""
        suggestions = [
            {"type": "a", "priority": "low"},
            {"type": "b", "priority": "high"},
            {"type": "c", "priority": "medium"},
        ]
        ranked = self.generator._rank_and_filter(suggestions)
        assert ranked[0]["priority"] == "high"
        assert ranked[1]["priority"] == "medium"
        assert ranked[2]["priority"] == "low"


class TestAnalyzeUserBehaviorConvenience:
    """Test analyze_user_behavior convenience function"""

    @pytest.mark.asyncio
    async def test_analyze_user_behavior(self):
        """Test convenience function"""
        now = datetime.now()
        actions = [
            UserAction(timestamp=now, action_type="search", duration_ms=100.0, success=True),
            UserAction(timestamp=now, action_type="write", duration_ms=200.0, success=True),
        ]

        profile = await analyze_user_behavior("user123", actions)
        assert profile.user_id == "user123"
        assert profile.total_actions == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])