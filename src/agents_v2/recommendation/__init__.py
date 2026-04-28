"""推荐模块 - 论文推荐系统"""
from .paper_recommender import (
    UserInteraction,
    PaperProfile,
    UserProfile,
    RecommendationEngine,
    get_recommender
)

__all__ = [
    "UserInteraction",
    "PaperProfile",
    "UserProfile",
    "RecommendationEngine",
    "get_recommender",
]
