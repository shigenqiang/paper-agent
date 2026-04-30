"""
Personalization模块测试

测试:
- ForgettingCurveMemory: 遗忘曲线记忆
- PreferenceLearner: 偏好学习
- SpacedRepetitionSystem: 间隔重复
- UserProfileManager: 用户画像
- CrossSessionKnowledge: 跨会话知识
"""
import pytest
import time
from src.agents_v2._archive.personalization import (
    ForgettingCurveMemory,
    MemoryStrength,
    MemoryItem,
    ReviewResult,
    calculate_retention,
    get_review_intervals,
    PreferenceLearner,
    PreferenceProfile,
    InteractionRecord,
    create_learner,
    SpacedRepetitionSystem,
    ReviewQuality,
    ReviewSchedule,
    ReviewSession,
    create_spaced_repetition,
    calculate_next_interval,
    UserProfileManager,
    UserProfile,
    UserKnowledge,
    create_profile_manager,
    CrossSessionKnowledge,
    KnowledgeEntry,
    SessionContext,
    create_cross_session_knowledge
)


class TestForgettingCurveMemory:
    """ForgettingCurveMemory测试"""

    def test_init(self):
        """测试初始化"""
        memory = ForgettingCurveMemory()
        assert memory is not None
        assert memory.retention_threshold == 0.3

    def test_add_memory(self):
        """测试添加记忆"""
        memory = ForgettingCurveMemory()
        item = memory.add("测试内容", importance=7.0)

        assert item is not None
        assert item.id is not None
        assert item.content == "测试内容"
        assert item.importance == 7.0
        assert item.strength == 5.0  # default base_strength

    def test_get_memory(self):
        """测试获取记忆"""
        memory = ForgettingCurveMemory()
        item = memory.add("测试内容")

        retrieved = memory.get(item.id)
        assert retrieved is not None
        assert retrieved.id == item.id

    def test_retention_calculation(self):
        """测试保留度计算"""
        memory = ForgettingCurveMemory()
        item = memory.add("测试内容", importance=5.0)

        # 新添加的记忆保留度应该很高
        assert item.retention > 0.9

        # 模拟时间流逝
        old_item = MemoryItem(
            id="old",
            content="old content",
            importance=5.0,
            strength=1.0,
            last_accessed=time.time() - 30 * 24 * 3600  # 30天前
        )

        # 30天后保留度应该很低
        retention = calculate_retention(30, 1.0)
        assert retention < 0.3

    def test_needs_reinforcement(self):
        """测试是否需要强化"""
        memory = ForgettingCurveMemory()
        item = memory.add("测试内容")

        # 新记忆不需要强化
        assert not item.needs_reinforcement

        # 模拟旧记忆
        old_item = MemoryItem(
            id="old",
            content="old content",
            importance=5.0,
            strength=1.0,
            last_accessed=time.time() - 30 * 24 * 3600
        )
        assert old_item.needs_reinforcement

    def test_search(self):
        """测试搜索"""
        memory = ForgettingCurveMemory()
        memory.add("Python编程语言")
        memory.add("Java编程语言")
        memory.add("机器学习算法")

        results = memory.search("Python")
        assert len(results) >= 1
        assert any("Python" in r.content for r in results)

    def test_get_needing_review(self):
        """测试获取需要复习的记忆"""
        memory = ForgettingCurveMemory()

        # 添加一些记忆
        memory.add("新记忆1")
        memory.add("新记忆2")

        # 模拟需要复习的记忆
        old_item = MemoryItem(
            id="old1",
            content="旧记忆",
            importance=5.0,
            strength=1.0,
            last_accessed=time.time() - 30 * 24 * 3600
        )
        memory._memory_store["old1"] = old_item

        needing_review = memory.get_needing_review()
        assert len(needing_review) >= 1

    @pytest.mark.asyncio
    async def test_review(self):
        """测试复习"""
        memory = ForgettingCurveMemory()
        item = memory.add("测试内容")
        original_strength = item.strength

        # 执行复习
        result = await memory.review(item.id, recall_quality=0.8)

        assert result is not None
        assert result.memory_id == item.id
        assert result.was_recalled is True

        # 成功复习后强度应该增加
        updated_item = memory.get(item.id)
        assert updated_item.strength >= original_strength

    def test_stats(self):
        """测试统计"""
        memory = ForgettingCurveMemory()
        memory.add("内容1")
        memory.add("内容2")

        stats = memory.get_stats()
        assert stats["total_memories"] == 2
        assert "avg_retention" in stats
        assert "avg_strength" in stats


class TestPreferenceLearner:
    """PreferenceLearner测试"""

    def test_init(self):
        """测试初始化"""
        learner = PreferenceLearner(user_id="test_user")
        assert learner.user_id == "test_user"
        assert isinstance(learner.profile, PreferenceProfile)

    def test_record_interaction(self):
        """测试记录交互"""
        learner = PreferenceLearner()
        learner.record_interaction("query", "我想写一篇关于AI的论文", "accepted")
        learner.record_interaction("revision", "简化这段文字", "accepted")

        assert len(learner._interaction_history) == 2

    def test_update_from_feedback(self):
        """测试从反馈学习"""
        learner = PreferenceLearner()
        learner.update_from_feedback("positive", "这个标题很好")

        assert len(learner._interaction_history) >= 1

    def test_infer_writing_style(self):
        """测试推断写作风格"""
        learner = PreferenceLearner()

        # 模拟多次简洁偏好信号
        for _ in range(5):
            learner.record_interaction("revision", "简化这段", "accepted")

        style, confidence = learner.infer_writing_style()
        assert style in ["concise", "balanced", "detailed"]
        assert 0 <= confidence <= 1

    def test_infer_depth_preference(self):
        """测试推断深度偏好"""
        learner = PreferenceLearner()

        # 添加一些查询
        learner.record_interaction("query", "深度学习在医学影像中的应用" * 5, "accepted")
        learner.record_interaction("query", "AI", "accepted")

        depth, confidence = learner.infer_depth_preference()
        assert depth in ["shallow", "medium", "deep"]
        assert 0 <= confidence <= 1

    def test_infer_topics(self):
        """测试推断主题"""
        learner = PreferenceLearner()

        learner.record_interaction("query", "人工智能和机器学习的研究", "accepted")
        learner.record_interaction("query", "深度学习算法", "accepted")
        learner.record_interaction("query", "机器学习算法", "accepted")

        topics = learner.infer_topics(top_k=3)
        assert len(topics) <= 3

    def test_build_profile(self):
        """测试构建完整画像"""
        learner = PreferenceLearner()
        learner.record_interaction("query", "测试查询", "accepted")

        profile = learner.build_profile()
        assert isinstance(profile, PreferenceProfile)
        assert profile.writing_style in ["concise", "balanced", "detailed"]
        assert profile.depth_preference in ["shallow", "medium", "deep"]

    def test_get_recommendation(self):
        """测试获取推荐"""
        learner = PreferenceLearner()
        learner.record_interaction("query", "AI论文写作", "accepted")

        rec = learner.get_recommendation("论文写作")
        assert "writing_style" in rec
        assert "depth" in rec
        assert "confidence" in rec


class TestSpacedRepetitionSystem:
    """SpacedRepetitionSystem测试"""

    def test_init(self):
        """测试初始化"""
        srs = SpacedRepetitionSystem()
        assert srs is not None

    def test_schedule_review(self):
        """测试安排复习"""
        srs = SpacedRepetitionSystem()
        schedule = srs.schedule_review("item1", "memory", initial_interval=1)

        assert schedule is not None
        assert schedule.item_id == "item1"
        assert schedule.interval_days == 1

    def test_get_due_items(self):
        """测试获取到期项"""
        srs = SpacedRepetitionSystem()
        srs.schedule_review("item1", "memory", initial_interval=0)  # 立即到期

        due = srs.get_due_items()
        assert len(due) >= 1
        assert due[0].item_id == "item1"

    def test_start_end_session(self):
        """测试会话管理"""
        srs = SpacedRepetitionSystem()

        session = srs.start_session()
        assert session is not None
        assert session.total_count == 0

        ended = srs.end_session()
        assert ended is not None
        assert ended.end_time is not None

    def test_record_review_good(self):
        """测试记录好的复习"""
        srs = SpacedRepetitionSystem()
        srs.schedule_review("item1", "memory")

        # 模拟成功回忆
        schedule = srs.record_review("item1", ReviewQuality.GOOD)

        assert schedule.consecutive_correct >= 1
        assert schedule.interval_days >= 1

    def test_record_review_fail(self):
        """测试记录失败的复习"""
        srs = SpacedRepetitionSystem()
        srs.schedule_review("item1", "memory")

        # 模拟失败回忆
        schedule = srs.record_review("item1", ReviewQuality.FAIL)

        assert schedule.consecutive_correct == 0
        assert schedule.interval_days == 1  # 重新开始

    def test_calculate_next_interval(self):
        """测试计算下次间隔"""
        interval = calculate_next_interval(6, 2.5, ReviewQuality.EASY)
        assert interval > 6

        interval_fail = calculate_next_interval(6, 2.5, ReviewQuality.FAIL)
        assert interval_fail == 1

    def test_get_stats(self):
        """测试统计"""
        srs = SpacedRepetitionSystem()
        srs.schedule_review("item1", "memory")

        stats = srs.get_stats()
        assert "total_scheduled" in stats
        assert "due_now" in stats


class TestUserProfileManager:
    """UserProfileManager测试"""

    def test_init(self):
        """测试初始化"""
        manager = UserProfileManager()
        assert manager is not None

    def test_create_profile(self):
        """测试创建画像"""
        manager = UserProfileManager()
        profile = manager.create_profile(
            user_id="user1",
            name="张三",
            email="zhang@example.com",
            role="researcher"
        )

        assert profile is not None
        assert profile.user_id == "user1"
        assert profile.name == "张三"
        assert profile.role == "researcher"

    def test_get_profile(self):
        """测试获取画像"""
        manager = UserProfileManager()
        manager.create_profile(user_id="user1", name="张三")

        profile = manager.get_profile("user1")
        assert profile is not None
        assert profile.name == "张三"

    def test_update_profile(self):
        """测试更新画像"""
        manager = UserProfileManager()
        manager.create_profile(user_id="user1", name="张三")

        updated = manager.update_profile("user1", name="李四", institution="清华大学")
        assert updated.name == "李四"
        assert updated.institution == "清华大学"

    def test_delete_profile(self):
        """测试删除画像"""
        manager = UserProfileManager()
        manager.create_profile(user_id="user1", name="张三")

        result = manager.delete_profile("user1")
        assert result is True

        profile = manager.get_profile("user1")
        assert profile is None

    def test_set_get_preference(self):
        """测试偏好设置"""
        manager = UserProfileManager()
        manager.create_profile(user_id="user1")

        manager.set_preference("user1", "theme", "dark")
        theme = manager.get_preference("user1", "theme")

        assert theme == "dark"

    def test_update_knowledge(self):
        """测试更新知识"""
        manager = UserProfileManager()
        manager.create_profile(user_id="user1")

        manager.update_knowledge("user1", "机器学习", 0.8, source="论文阅读")
        knowledge = manager.get_knowledge("user1", "机器学习")

        assert knowledge is not None
        assert knowledge.expertise_level >= 0.7

    def test_list_profiles(self):
        """测试列出画像"""
        manager = UserProfileManager()
        manager.create_profile(user_id="user1", name="张三")
        manager.create_profile(user_id="user2", name="李四")

        profiles = manager.list_profiles()
        assert len(profiles) == 2


class TestCrossSessionKnowledge:
    """CrossSessionKnowledge测试"""

    def test_init(self):
        """测试初始化"""
        cs = CrossSessionKnowledge(user_id="user1")
        assert cs.user_id == "user1"

    def test_start_end_session(self):
        """测试会话管理"""
        cs = CrossSessionKnowledge()

        session = cs.start_session("session1", topic="AI研究")
        assert session is not None
        assert session.session_id == "session1"

        ended = cs.end_session()
        assert ended is not None
        assert ended.end_time is not None

    def test_add_knowledge(self):
        """测试添加知识"""
        cs = CrossSessionKnowledge()
        cs.start_session("session1")
        cs.add_knowledge("Transformer架构", importance=8.0, tags=["AI", "深度学习"])

        assert len(cs._knowledge_store) == 1

    def test_get_knowledge(self):
        """测试获取知识"""
        cs = CrossSessionKnowledge()
        cs.start_session("session1")
        entry = cs.add_knowledge("测试知识")

        retrieved = cs.get_knowledge(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id

    def test_search_knowledge(self):
        """测试搜索知识"""
        cs = CrossSessionKnowledge()
        cs.start_session("session1")
        cs.add_knowledge("Python是一种编程语言")
        cs.add_knowledge("JavaScript用于Web开发")

        results = cs.search_knowledge("Python")
        assert len(results) >= 1
        assert any("Python" in r.content for r in results)

    def test_search_with_tags(self):
        """测试带标签搜索"""
        cs = CrossSessionKnowledge()
        cs.start_session("session1")
        cs.add_knowledge("机器学习知识", tags=["AI"])
        cs.add_knowledge("Python知识", tags=["编程"])

        results = cs.search_knowledge("知识", tags=["AI"])
        assert len(results) >= 1
        assert "AI" in results[0].tags

    def test_link_knowledge(self):
        """测试链接知识"""
        cs = CrossSessionKnowledge()
        cs.start_session("session1")
        entry1 = cs.add_knowledge("深度学习")
        entry2 = cs.add_knowledge("神经网络")

        cs.link_knowledge(entry1.id, entry2.id)

        # 验证链接
        e1 = cs.get_knowledge(entry1.id)
        assert entry2.id in e1.related_entries

    def test_build_knowledge_graph(self):
        """测试构建知识图谱"""
        cs = CrossSessionKnowledge()
        cs.start_session("session1")
        cs.add_knowledge("知识1")
        cs.add_knowledge("知识2")

        graph = cs.build_knowledge_graph()
        assert "nodes" in graph
        assert "edges" in graph
        assert graph["node_count"] == 2

    def test_get_recent_context(self):
        """测试获取最近上下文"""
        cs = CrossSessionKnowledge()
        cs.start_session("session1")
        cs.end_session()
        cs.start_session("session2")

        recent = cs.get_recent_context(hours=24)
        assert len(recent) >= 1

    def test_consolidate_knowledge(self):
        """测试整合知识"""
        cs = CrossSessionKnowledge()
        cs.start_session("session1")

        # 添加低重要性知识
        cs.add_knowledge("低重要性知识", importance=1.0)
        cs.add_knowledge("高重要性知识", importance=8.0)

        removed = cs.consolidate_knowledge(min_importance=3.0)
        assert removed >= 1


class TestCalculateRetention:
    """calculate_retention函数测试"""

    def test_new_memory(self):
        """测试新记忆"""
        retention = calculate_retention(0, 5.0)
        assert retention == pytest.approx(1.0)

    def test_old_memory(self):
        """测试旧记忆"""
        retention = calculate_retention(30, 5.0)
        assert 0 < retention < 0.5


class TestGetReviewIntervals:
    """get_review_intervals函数测试"""

    def test_intervals(self):
        """测试间隔序列"""
        intervals = get_review_intervals(0)
        assert intervals[0] == 1

        intervals_3 = get_review_intervals(3)
        assert len(intervals_3) >= 4


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_learner(self):
        """测试创建学习器"""
        learner = create_learner("test")
        assert learner.user_id == "test"

    def test_create_spaced_repetition(self):
        """测试创建SRS"""
        srs = create_spaced_repetition()
        assert srs is not None

    def test_create_profile_manager(self):
        """测试创建画像管理器"""
        manager = create_profile_manager()
        assert manager is not None

    def test_create_cross_session_knowledge(self):
        """测试创建跨会话知识"""
        cs = create_cross_session_knowledge("user1")
        assert cs.user_id == "user1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])