"""推荐系统 - 基于用户行为的论文推荐"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import hashlib
import json

from ..cache import MemoryCache

logger = logging.getLogger(__name__)


@dataclass
class UserInteraction:
    """用户交互记录"""
    user_id: str
    paper_id: str
    interaction_type: str  # view, click, save, share, like, search
    timestamp: float
    duration: int = 0  # 阅读时长(秒)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaperProfile:
    """论文画像"""
    paper_id: str
    title: str
    keywords: Set[str] = field(default_factory=set)
    topics: Set[str] = field(default_factory=set)
    authors: Set[str] = field(default_factory=set)
    cited_papers: Set[str] = field(default_factory=set)
    view_count: int = 0
    like_count: int = 0
    save_count: int = 0


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    interested_topics: Set[str] = field(default_factory=set)
    interested_keywords: Set[str] = field(default_factory=set)
    followed_authors: Set[str] = field(default_factory=set)
    interaction_count: int = 0
    viewed_papers: Set[str] = field(default_factory=set)
    liked_papers: Set[str] = field(default_factory=set)
    saved_papers: Set[str] = field(default_factory=set)
    last_updated: float = 0


class RecommendationEngine:
    """
    推荐引擎

    功能：
    - 基于内容的推荐
    - 协同过滤推荐
    - 热门推荐
    - 趋势推荐
    """

    def __init__(self):
        self._user_profiles: Dict[str, UserProfile] = {}
        self._paper_profiles: Dict[str, PaperProfile] = {}
        self._interactions: List[UserInteraction] = []
        self._cache = MemoryCache(default_ttl=3600)

    # ========== 用户交互 ==========

    def record_interaction(
        self,
        user_id: str,
        paper_id: str,
        interaction_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录用户交互"""
        interaction = UserInteraction(
            user_id=user_id,
            paper_id=paper_id,
            interaction_type=interaction_type,
            timestamp=datetime.now().timestamp(),
            metadata=metadata or {}
        )
        self._interactions.append(interaction)

        # 更新用户画像
        self._update_user_profile(user_id, paper_id, interaction_type)

        logger.debug(f"Recorded interaction: {user_id} - {paper_id} - {interaction_type}")

    def _update_user_profile(
        self,
        user_id: str,
        paper_id: str,
        interaction_type: str
    ):
        """更新用户画像"""
        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = UserProfile(user_id=user_id)

        profile = self._user_profiles[user_id]
        profile.interaction_count += 1
        profile.last_updated = datetime.now().timestamp()

        # 获取论文画像
        paper = self._paper_profiles.get(paper_id)
        if paper:
            if interaction_type == "view":
                profile.viewed_papers.add(paper_id)
                profile.interested_topics.update(paper.topics)
                profile.interested_keywords.update(paper.keywords)
                profile.followed_authors.update(paper.authors)
            elif interaction_type == "like":
                profile.liked_papers.add(paper_id)
            elif interaction_type == "save":
                profile.saved_papers.add(paper_id)

    # ========== 论文画像 ==========

    def update_paper_profile(
        self,
        paper_id: str,
        title: str,
        keywords: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        authors: Optional[List[str]] = None
    ):
        """更新论文画像"""
        if paper_id not in self._paper_profiles:
            self._paper_profiles[paper_id] = PaperProfile(paper_id=paper_id, title=title)

        profile = self._paper_profiles[paper_id]
        profile.title = title

        if keywords:
            profile.keywords.update(keywords)
        if topics:
            profile.topics.update(topics)
        if authors:
            profile.authors.update(authors)

    def increment_paper_stat(self, paper_id: str, stat_type: str):
        """增加论文统计"""
        if paper_id not in self._paper_profiles:
            return

        profile = self._paper_profiles[paper_id]
        if stat_type == "view":
            profile.view_count += 1
        elif stat_type == "like":
            profile.like_count += 1
        elif stat_type == "save":
            profile.save_count += 1

    # ========== 推荐算法 ==========

    async def recommend_for_user(
        self,
        user_id: str,
        limit: int = 10,
        exclude_viewed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        为用户推荐论文

        Args:
            user_id: 用户ID
            limit: 返回数量
            exclude_viewed: 是否排除已查看的论文

        Returns:
            推荐论文列表
        """
        # 检查缓存
        cache_key = f"rec:{user_id}:{limit}"
        cached = await self._cache.get(cache_key)
        if cached:
            return cached

        if user_id not in self._user_profiles:
            # 新用户，返回热门推荐
            return await self.recommend_hot(limit=limit)

        user_profile = self._user_profiles[user_id]
        scores: Dict[str, float] = defaultdict(float)

        # 1. 基于内容的推荐
        for paper_id, paper in self._paper_profiles.items():
            if exclude_viewed and paper_id in user_profile.viewed_papers:
                continue

            # 计算内容相似度
            content_score = self._calculate_content_score(user_profile, paper)
            if content_score > 0:
                scores[paper_id] += content_score * 0.4

        # 2. 协同过滤
        collaborative_score = await self._calculate_collaborative_score(user_id, user_profile)
        for paper_id, score in collaborative_score.items():
            if exclude_viewed and paper_id in user_profile.viewed_papers:
                continue
            scores[paper_id] += score * 0.3

        # 3. 热门加权
        for paper_id in scores:
            if paper_id in self._paper_profiles:
                hot_score = self._calculate_hot_score(self._paper_profiles[paper_id])
                scores[paper_id] += hot_score * 0.2

        # 4. 新颖性加权
        for paper_id, score in scores.items():
            if paper_id in self._paper_profiles:
                novelty = self._calculate_novelty(paper_id)
                scores[paper_id] += novelty * 0.1

        # 排序并返回top N
        sorted_papers = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        recommendations = []
        for paper_id, score in sorted_papers:
            paper = self._paper_profiles.get(paper_id)
            if paper:
                recommendations.append({
                    "paper_id": paper_id,
                    "title": paper.title,
                    "score": round(score, 3),
                    "reason": self._explain_recommendation(user_profile, paper)
                })

        # 缓存结果
        await self._cache.set(cache_key, recommendations, ttl=300)

        return recommendations

    def _calculate_content_score(self, user_profile: UserProfile, paper: PaperProfile) -> float:
        """计算内容相似度分数"""
        score = 0.0

        # 话题匹配
        topic_overlap = len(user_profile.interested_topics & paper.topics)
        if topic_overlap > 0:
            score += topic_overlap * 2.0

        # 关键词匹配
        keyword_overlap = len(user_profile.interested_keywords & paper.keywords)
        if keyword_overlap > 0:
            score += keyword_overlap * 1.0

        # 作者匹配
        author_overlap = len(user_profile.followed_authors & paper.authors)
        if author_overlap > 0:
            score += author_overlap * 1.5

        return score

    async def _calculate_collaborative_score(
        self,
        user_id: str,
        user_profile: UserProfile
    ) -> Dict[str, float]:
        """计算协同过滤分数"""
        # 找到与该用户相似的其他用户
        similar_users = self._find_similar_users(user_id, user_profile)

        scores: Dict[str, float] = defaultdict(float)

        # 根据相似用户的交互计算分数
        for other_user_id, similarity in similar_users:
            if other_user_id not in self._user_profiles:
                continue

            other_profile = self._user_profiles[other_user_id]

            # 推荐相似用户喜欢但当前用户未看过的论文
            for paper_id in other_profile.liked_papers | other_profile.saved_papers:
                if paper_id not in user_profile.viewed_papers:
                    # 相似用户喜欢且未看过，加分
                    scores[paper_id] += similarity * 2.0

        return scores

    def _find_similar_users(
        self,
        user_id: str,
        user_profile: UserProfile,
        top_n: int = 10
    ) -> List[tuple]:
        """找到相似用户"""
        similarities = []

        for other_id, other_profile in self._user_profiles.items():
            if other_id == user_id:
                continue

            # 计算Jaccard相似度
            similarity = self._calculate_user_similarity(user_profile, other_profile)
            if similarity > 0:
                similarities.append((other_id, similarity))

        # 返回top N相似用户
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]

    def _calculate_user_similarity(
        self,
        profile1: UserProfile,
        profile2: UserProfile
    ) -> float:
        """计算用户相似度（Jaccard）"""
        # 基于话题
        topics1 = profile1.interested_topics
        topics2 = profile2.interested_topics
        topic_sim = len(topics1 & topics2) / len(topics1 | topics2) if topics1 | topics2 else 0

        # 基于关键词
        keywords1 = profile1.interested_keywords
        keywords2 = profile2.interested_keywords
        keyword_sim = len(keywords1 & keywords2) / len(keywords1 | keywords2) if keywords1 | keywords2 else 0

        # 基于作者
        authors1 = profile1.followed_authors
        authors2 = profile2.followed_authors
        author_sim = len(authors1 & authors2) / len(authors1 | authors2) if authors1 | authors2 else 0

        return (topic_sim + keyword_sim + author_sim) / 3

    def _calculate_hot_score(self, paper: PaperProfile) -> float:
        """计算热门分数"""
        # 综合浏览、点赞、收藏计算热门分数
        hot = paper.view_count * 1.0 + paper.like_count * 3.0 + paper.save_count * 5.0
        return min(hot / 100, 1.0)  # 归一化到0-1

    def _calculate_novelty(self, paper_id: str) -> float:
        """计算新颖性分数"""
        # 论文越新，分数越高
        # 这里简化处理，实际应该用论文发布时间
        if paper_id not in self._paper_profiles:
            return 0.5

        paper = self._paper_profiles[paper_id]
        # 刚发布的论文新颖性高
        novelty = 1.0 - min(paper.view_count / 100, 1.0)
        return novelty

    def _explain_recommendation(self, user_profile: UserProfile, paper: PaperProfile) -> str:
        """解释推荐原因"""
        reasons = []

        topic_overlap = user_profile.interested_topics & paper.topics
        if topic_overlap:
            reasons.append(f"匹配您关注的话题: {', '.join(list(topic_overlap)[:2])}")

        author_overlap = user_profile.followed_authors & paper.authors
        if author_overlap:
            reasons.append(f"您关注的作者: {', '.join(list(author_overlap)[:2])}")

        if not reasons:
            reasons.append("热门论文推荐")

        return "; ".join(reasons)

    # ========== 热门和趋势 ==========

    async def recommend_hot(self, limit: int = 10) -> List[Dict[str, Any]]:
        """推荐热门论文"""
        papers = list(self._paper_profiles.values())
        sorted_papers = sorted(papers, key=lambda p: self._calculate_hot_score(p), reverse=True)

        return [
            {
                "paper_id": p.paper_id,
                "title": p.title,
                "score": round(self._calculate_hot_score(p), 3),
                "reason": "热门论文"
            }
            for p in sorted_papers[:limit]
        ]

    async def recommend_trending(
        self,
        limit: int = 10,
        time_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """推荐趋势上升的论文"""
        now = datetime.now().timestamp()
        window_start = now - time_window_hours * 3600

        # 统计时间窗口内的交互
        recent_interactions = [
            i for i in self._interactions
            if i.timestamp >= window_start and i.interaction_type in ["view", "like"]
        ]

        paper_scores: Dict[str, int] = defaultdict(int)
        for interaction in recent_interactions:
            paper_scores[interaction.paper_id] += 1

        # 排序
        sorted_papers = sorted(paper_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [
            {
                "paper_id": paper_id,
                "title": self._paper_profiles.get(paper_id, PaperProfile(paper_id=paper_id, title="Unknown")).title,
                "score": round(score / max(time_window_hours, 1), 2),
                "reason": f"近期热度上升 (+{score}次交互)"
            }
            for paper_id, score in sorted_papers
        ]

    # ========== 统计 ==========

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计"""
        if user_id not in self._user_profiles:
            return {
                "user_id": user_id,
                "interaction_count": 0,
                "topics": [],
                "keywords": []
            }

        profile = self._user_profiles[user_id]
        return {
            "user_id": user_id,
            "interaction_count": profile.interaction_count,
            "topics": list(profile.interested_topics)[:10],
            "keywords": list(profile.interested_keywords)[:20],
            "followed_authors": list(profile.followed_authors)[:10],
            "viewed_count": len(profile.viewed_papers),
            "liked_count": len(profile.liked_papers),
            "saved_count": len(profile.saved_papers)
        }

    def get_paper_stats(self, paper_id: str) -> Dict[str, Any]:
        """获取论文统计"""
        if paper_id not in self._paper_profiles:
            return {"paper_id": paper_id, "stats": {}}

        paper = self._paper_profiles[paper_id]
        return {
            "paper_id": paper_id,
            "title": paper.title,
            "stats": {
                "view_count": paper.view_count,
                "like_count": paper.like_count,
                "save_count": paper.save_count
            }
        }


# 全局推荐引擎实例
_global_recommender: Optional[RecommendationEngine] = None


def get_recommender() -> RecommendationEngine:
    """获取全局推荐引擎"""
    global _global_recommender
    if _global_recommender is None:
        _global_recommender = RecommendationEngine()
    return _global_recommender
