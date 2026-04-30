"""
Execution模块 - 长期任务执行与技能获取

包含:
- SkillAcquisitionEngine: 技能获取引擎
- LongTermTaskExecutor: 长期任务执行器
"""
from .skill_engine import (
    SkillAcquisitionEngine,
    Skill,
    SkillExecution,
    LongTermTaskExecutor,
    create_skill_engine,
    create_long_term_executor
)

__all__ = [
    "SkillAcquisitionEngine",
    "Skill",
    "SkillExecution",
    "LongTermTaskExecutor",
    "create_skill_engine",
    "create_long_term_executor"
]