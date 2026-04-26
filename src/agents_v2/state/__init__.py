"""
State Management - 状态管理模块

提供PaperState、状态验证和状态持久化功能。
"""
from .state_model import (
    PaperState,
    StateMetadata,
    StateValidationResult,
    PaperPhase,
    StateStatus,
    create_initial_state,
)
from .state_validator import (
    StateValidator,
    validate_state,
)
from .state_persistence import (
    StatePersistence,
    StateStore,
)

__all__ = [
    "PaperState",
    "StateMetadata",
    "StateValidationResult",
    "PaperPhase",
    "StateStatus",
    "StateValidator",
    "validate_state",
    "StatePersistence",
    "StateStore",
]