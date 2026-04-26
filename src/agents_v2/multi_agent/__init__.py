"""
MultiAgent模块 - 多Agent协作与自主学习

包含:
- MultiAgentDebate: 多Agent辩论系统
- HierarchicalOrchestrator: 层级编排器
- AgentSkillLibrary: Agent技能库
- SelfLearningEngine: 自主学习引擎
"""
from .debate import (
    MultiAgentDebate,
    HierarchicalOrchestrator,
    AgentSkillLibrary,
    DebateRole,
    DebateStatement,
    DebateResult,
    run_debate
)
from .self_learning_engine import (
    SelfLearningEngine,
    LearningEpisode,
    StrategyAdjustment,
    create_learning_engine
)

__all__ = [
    # 辩论系统
    "MultiAgentDebate",
    "HierarchicalOrchestrator",
    "AgentSkillLibrary",
    "DebateRole",
    "DebateStatement",
    "DebateResult",
    "run_debate",

    # 自主学习
    "SelfLearningEngine",
    "LearningEpisode",
    "StrategyAdjustment",
    "create_learning_engine"
]