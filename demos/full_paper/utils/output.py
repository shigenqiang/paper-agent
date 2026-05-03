"""
阶段输出管理 - 与全链路输出一致
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime


@dataclass
class PhaseOutput:
    """阶段输出结果"""
    phase_name: str
    success: bool = False
    status: str = "pending"
    text: str = ""  # 主要输出文本
    result: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    quality_level: str = "poor"
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "phase_name": self.phase_name,
            "success": self.success,
            "status": self.status,
            "text": self.text,
            "result": self.result,
            "quality_score": self.quality_score,
            "quality_level": self.quality_level,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "execution_time": self.execution_time,
            "error": self.error,
            "timestamp": self.timestamp
        }


class OutputManager:
    """输出管理器 - 管理所有阶段的输出"""

    def __init__(self):
        self.phase_outputs: Dict[str, PhaseOutput] = {}
        self._final_text: str = ""

    def add_output(self, phase_name: str, output: PhaseOutput):
        """添加阶段输出"""
        self.phase_outputs[phase_name] = output

    def get_output(self, phase_name: str) -> Optional[PhaseOutput]:
        """获取阶段输出"""
        return self.phase_outputs.get(phase_name)

    def get_text(self, phase_name: str) -> str:
        """获取阶段输出文本"""
        output = self.get_output(phase_name)
        return output.text if output else ""

    def get_all_texts(self) -> Dict[str, str]:
        """获取所有阶段的文本"""
        return {name: out.text for name, out in self.phase_outputs.items()}

    def set_final_text(self, text: str):
        """设置最终文本"""
        self._final_text = text

    def get_final_text(self) -> str:
        """获取最终文本"""
        return self._final_text

    def compile_result(self) -> Dict[str, Any]:
        """编译最终结果"""
        phases_completed = [name for name, out in self.phase_outputs.items() if out.success]
        quality_scores = [out.quality_score for out in self.phase_outputs.values() if out.success]

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        if avg_quality >= 9.0:
            quality_level = "excellent"
        elif avg_quality >= 7.0:
            quality_level = "good"
        elif avg_quality >= 5.0:
            quality_level = "acceptable"
        else:
            quality_level = "poor"

        return {
            "success": len(phases_completed) > 0,
            "phases_completed": phases_completed,
            "final_paper": self._final_text,
            "final_quality": avg_quality,
            "quality_level": quality_level,
            "phase_outputs": {name: out.to_dict() for name, out in self.phase_outputs.items()}
        }
