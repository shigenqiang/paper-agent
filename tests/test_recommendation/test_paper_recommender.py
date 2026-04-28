"""
推荐系统 单元测试
"""
import pytest
import time
from collections import defaultdict

from src.agents_v2.recommendation import (
    UserInteraction,
    PaperProfile,
    UserProfile,
    RecommendationEngine,
    get_recommender
)


class TestUserInteraction:
    """UserInteraction 测试"""

    def test_create_interaction(self):
        """测试创建交互"""
        interaction = UserInteraction(
            user_id="user_001",
            paper_id="paper_001",
            interaction_type="view",
            timestamp=time.time(),
            duration=120
        )
        assert interaction.user_id == "user_001"
        assert interaction.interaction_type == "view"
        assert interaction.duration == 120


class TestPaperProfile:
    """PaperProfile 测试"""

    def test_create_profile(self):
        """测试创建论文画像"""
        profile = PaperProfile(
            paper_id="paper_001",
            title="Test Paper",
            keywords={"ML", "DL"},
            topics={"NLP"},
            authors={"Author A"}
        )
        assert profile.paper_id == "paper_001"
        assert "ML" in profile.keywords
        assert "NLP" in profile.topics


class TestUserProfile:
    """UserProfile 测试"""

    def test_create_profile(self):
        """测试创建用户画像"""
        profile = UserProfile(
            user_id="user_001",
            interested_topics={"ML", "NLP"},
            interested_keywords={"deep learning"}
        )
        assert profile.user_id == "user_001"
        assert "ML" in profile.interested_topics


class TestRecommendationEngine:
    """RecommendationEngine 测试"""

    def setup_method(self):
        self.engine = RecommendationEngine()

    def test_record_interaction(self):
        """测试记录交互"""
        self.engine.record_interaction(
            user_id="user_001",
            paper_id="paper_001",
            interaction_type="view"
        )
        assert len(self.engine._interactions) == 1

    def test_update_paper_profile(self):
        """测试更新论文画像"""
        self.engine.update_paper_profile(
            paper_id="paper_001",
            title="ML Paper",
            keywords=["machine learning", "neural network"],
            topics=["deep learning"],
            authors=["Author A", "Author B"]
        )
        assert "paper_001" in self.engine._paper_profiles
        profile = self.engine._paper_profiles["paper_001"]
        assert profile.title == "ML Paper"
        assert "machine learning" in profile.keywords

    def test_increment_paper_stat(self):
        """测试增加论文统计"""
        self.engine.update_paper_profile("paper_001", "Test")
        self.engine.increment_paper_stat("paper_001", "view")
        self.engine.increment_paper_stat("paper_001", "like")

        profile = self.engine._paper_profiles["paper_001"]
        assert profile.view_count == 1
        assert profile.like_count == 1

    @pytest.mark.asyncio
    async def test_recommend_for_new_user(self):
        """测试新用户推荐"""
        # 新用户应返回热门推荐
        recs = await self.engine.recommend_for_user("new_user_xyz", limit=5)
        assert isinstance(recs, list)

    @pytest.mark.asyncio
    async def test_recommend_with_content(self):
        """测试基于内容的推荐"""
        # 添加论文
        self.engine.update_paper_profile(
            "paper_1", "ML Paper",
            keywords=["machine learning"],
            topics={"ML"}
        )
        self.engine.update_paper_profile(
            "paper_2", "NLP Paper",
            keywords=["NLP"],
            topics={"NLP"}
        )

        # 用户查看ML论文
        self.engine.record_interaction("user_1", "paper_1", "view")

        # 推荐
        recs = await self.engine.recommend_for_user("user_1", limit=5)
        assert isinstance(recs, list)

    @pytest.mark.asyncio
    async def test_recommend_hot(self):
        """测试热门推荐"""
        # 添加论文
        self.engine.update_paper_profile("paper_1", "Popular Paper")
        self.engine.update_paper_profile("paper_2", "Another Paper")

        # 增加热门度
        self.engine.increment_paper_stat("paper_1", "view")
        self.engine.increment_paper_stat("paper_1", "like")
        self.engine.increment_paper_stat("paper_1", "save")

        recs = await self.engine.recommend_hot(limit=5)
        assert len(recs) > 0
        assert recs[0]["paper_id"] == "paper_1"

    @pytest.mark.asyncio
    async def test_recommend_trending(self):
        """测试趋势推荐"""
        self.engine.update_paper_profile("paper_1", "Trending Paper")
        self.engine.update_paper_profile("paper_2", "Normal Paper")

        # 模拟最近交互
        self.engine.record_interaction("user_1", "paper_1", "view")
        self.engine.record_interaction("user_2", "paper_1", "view")
        self.engine.record_interaction("user_3", "paper_1", "like")

        recs = await self.engine.recommend_trending(limit=5, time_window_hours=24)
        assert len(recs) > 0

    def test_calculate_hot_score(self):
        """测试热门分数计算"""
        profile = PaperProfile(
            paper_id="test",
            title="Test",
            view_count=50,
            like_count=10,
            save_count=5
        )
        score = self.engine._calculate_hot_score(profile)
        assert 0 <= score <= 1

    def test_get_user_stats(self):
        """测试获取用户统计"""
        self.engine.record_interaction("user_1", "paper_1", "view")
        self.engine.record_interaction("user_1", "paper_1", "like")
        self.engine.record_interaction("user_1", "paper_1", "save")

        stats = self.engine.get_user_stats("user_1")
        assert stats["user_id"] == "user_1"
        assert stats["interaction_count"] == 3

    def test_get_paper_stats(self):
        """测试获取论文统计"""
        self.engine.update_paper_profile("paper_1", "Test Paper")
        self.engine.increment_paper_stat("paper_1", "view")
        self.engine.increment_paper_stat("paper_1", "view")
        self.engine.increment_paper_stat("paper_1", "like")

        stats = self.engine.get_paper_stats("paper_1")
        assert stats["paper_id"] == "paper_1"
        assert stats["stats"]["view_count"] == 2
        assert stats["stats"]["like_count"] == 1


class TestGlobalInstance:
    """全局实例测试"""

    def test_get_recommender_singleton(self):
        """测试推荐引擎单例"""
        engine1 = get_recommender()
        engine2 = get_recommender()
        assert engine1 is engine2


class TestIntegration:
    """集成测试"""

    def setup_method(self):
        self.engine = RecommendationEngine()

    @pytest.mark.asyncio
    async def test_full_recommendation_flow(self):
        """测试完整推荐流程"""
        # 1. 添加论文
        papers = [
            ("p1", "Machine Learning Basics", ["machine learning"], ["ML"]),
            ("p2", "Deep Learning Guide", ["deep learning", "neural network"], ["DL"]),
            ("p3", "NLP Fundamentals", ["NLP", "text mining"], ["NLP"]),
            ("p4", "Computer Vision", ["CV", "image processing"], ["CV"]),
        ]

        for pid, title, keywords, topics in papers:
            self.engine.update_paper_profile(
                pid, title,
                keywords=keywords,
                topics=set(topics)
            )

        # 2. 增加热门度（让这些论文被推荐）
        for i in range(5):
            self.engine.increment_paper_stat("p1", "view")
            self.engine.increment_paper_stat("p2", "view")
            self.engine.increment_paper_stat("p3", "view")
        self.engine.increment_paper_stat("p4", "like")

        # 3. 模拟用户交互
        self.engine.record_interaction("user_1", "p1", "view")
        self.engine.record_interaction("user_1", "p1", "like")
        self.engine.record_interaction("user_1", "p2", "view")

        # 4. 获取热门推荐（应该返回论文）
        hot_recs = await self.engine.recommend_hot(limit=3)
        assert len(hot_recs) > 0, f"Expected hot recommendations, got {hot_recs}"

        # 5. 获取趋势推荐
        trending_recs = await self.engine.recommend_trending(limit=3)
        # 趋势推荐需要时间窗口内的交互，可能为空

        # 6. 为用户推荐（应该基于内容+协同过滤）
        recs = await self.engine.recommend_for_user("user_1", limit=5)
        # 用户看过p1和p2，可能推荐其他论文


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
