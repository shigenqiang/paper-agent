"""
分层记忆系统 v4.0 - 基于"记忆系统与数据存储融合方案 v3.0"

核心模块:
- UnifiedMemoryManager: 统一记忆管理器 (v4.0 新增 recall_with_decay)
- MemoryConfig: 配置
- MemoryType, MemoryEntry, ImportanceLevel: 类型定义

五级重要性体系:
- CRITICAL (1.0): 永不遗忘
- HIGH (0.8): 7天保留
- MEDIUM (0.5): 1天保留
- LOW (0.3): 1小时保留
- FORGOTTEN (<0.1): 已删除

核心公式:
- retention = importance * e^(-t/S)  (Ebbinghaus遗忘曲线)
- score = relevance×0.3 + explicit×0.4 + recency×0.2 + access_boost×0.1
"""

from .types import (
    MemoryType,
    ImportanceLevel,
    MemoryEntry,
    EpisodicEntry,
    UserPreference,
    ProcedureEntry
)
from .unified import (
    UnifiedMemoryManager,
    MemoryConfig,
    ShortTermMemory,
    SessionMemory,
    LongTermMemory,
    EpisodicMemory,
    UserProfileMemory,
    ForgettingController,
    get_memory_manager,
    init_memory_for_task
)
from .flow_controller import (
    MemoryFlowController,
    FlowConfig,
    SessionPersistenceManager
)

__all__ = [
    # 类型定义
    "MemoryType",
    "ImportanceLevel",
    "MemoryEntry",
    "EpisodicEntry",
    "UserPreference",
    "ProcedureEntry",
    # 核心管理器
    "UnifiedMemoryManager",
    "MemoryConfig",
    "get_memory_manager",
    "init_memory_for_task",
    # 各层记忆
    "ShortTermMemory",
    "SessionMemory",
    "LongTermMemory",
    "EpisodicMemory",
    "UserProfileMemory",
    # 控制器
    "ForgettingController",
    "MemoryFlowController",
    "FlowConfig",
    "SessionPersistenceManager",
]

# 版本信息
__version__ = "4.0"
