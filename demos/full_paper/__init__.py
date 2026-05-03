"""
全链路论文生成模块

将完整论文生成流程拆分为独立的小模块，每个模块输出文本与全链路一致
"""
from .phases import (
    DiagnosticPhase,
    TopicPhase,
    LiteraturePhase,
    MethodologyPhase,
    WritingPhase,
    PolishPhase,
)

from .runner import FullPaperRunner

__all__ = [
    "DiagnosticPhase",
    "TopicPhase",
    "LiteraturePhase",
    "MethodologyPhase",
    "WritingPhase",
    "PolishPhase",
    "FullPaperRunner",
]