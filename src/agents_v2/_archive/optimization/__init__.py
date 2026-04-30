"""
Optimization模块 - 性能优化

包含:
- PerformanceOptimizer: 全面性能优化器
"""
from .performance_optimizer import (
    PerformanceOptimizer,
    PerformanceMetrics,
    ObjectPool,
    LazyLoader,
    VectorCache,
    AsyncBatchExecutor,
    create_optimizer
)

__all__ = [
    "PerformanceOptimizer",
    "PerformanceMetrics",
    "ObjectPool",
    "LazyLoader",
    "VectorCache",
    "AsyncBatchExecutor",
    "create_optimizer"
]