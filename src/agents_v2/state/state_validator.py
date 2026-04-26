"""
State Validator - 状态验证器

验证PaperState的有效性。
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from .state_model import PaperState, PaperPhase, StateStatus, StateValidationResult, StateValidationError


class StateValidator:
    """
    状态验证器

    功能:
    - 验证状态转换
    - 检查必填字段
    - 验证数据一致性

    使用示例:
        validator = StateValidator()

        state = PaperState()
        result = validator.validate(state)

        if not result.valid:
            for error in result.errors:
                print(f"{error.field}: {error.message}")
    """

    # 各阶段的必填字段
    PHASE_REQUIRED_FIELDS = {
        PaperPhase.DIAGNOSTIC: [],
        PaperPhase.TOPIC: ["topic"],
        PaperPhase.LITERATURE: ["topic"],
        PaperPhase.METHODOLOGY: ["topic", "references"],
        PaperPhase.WRITING: ["topic", "outline"],
        PaperPhase.POLISH: ["title", "content"],
        PaperPhase.COMPLETED: ["title", "content", "abstract"],
        PaperPhase.FAILED: [],
    }

    # 有效状态转换
    VALID_TRANSITIONS = {
        PaperPhase.DIAGNOSTIC: [PaperPhase.TOPIC, PaperPhase.FAILED],
        PaperPhase.TOPIC: [PaperPhase.LITERATURE, PaperPhase.FAILED],
        PaperPhase.LITERATURE: [PaperPhase.METHODOLOGY, PaperPhase.FAILED],
        PaperPhase.METHODOLOGY: [PaperPhase.WRITING, PaperPhase.FAILED],
        PaperPhase.WRITING: [PaperPhase.POLISH, PaperPhase.FAILED],
        PaperPhase.POLISH: [PaperPhase.COMPLETED, PaperPhase.FAILED],
        PaperPhase.COMPLETED: [],
        PaperPhase.FAILED: [PaperPhase.DIAGNOSTIC],  # 允许重试
    }

    def __init__(self):
        self._custom_validators: List[Callable] = []

    def add_validator(self, validator: Callable[[PaperState], Optional[str]]):
        """添加自定义验证器"""
        self._custom_validators.append(validator)

    def validate(self, state: PaperState) -> StateValidationResult:
        """
        验证状态

        Args:
            state: 要验证的状态

        Returns:
            StateValidationResult: 验证结果
        """
        result = StateValidationResult(valid=True)

        # 1. 检查必填字段
        self._validate_required_fields(state, result)

        # 2. 检查状态转换
        self._validate_transitions(state, result)

        # 3. 检查数据一致性
        self._validate_consistency(state, result)

        # 4. 运行自定义验证器
        self._run_custom_validators(state, result)

        # 5. 检查警告（非致命问题）
        self._check_warnings(state, result)

        return result

    def _validate_required_fields(
        self,
        state: PaperState,
        result: StateValidationResult
    ):
        """验证必填字段"""
        required_fields = self.PHASE_REQUIRED_FIELDS.get(state.phase, [])

        for field_name in required_fields:
            if not self._has_field_value(state, field_name):
                result.errors.append(StateValidationError(
                    field=field_name,
                    message=f"Required field '{field_name}' is missing in phase {state.phase.value}",
                    code="REQUIRED_FIELD_MISSING"
                ))

    def _has_field_value(self, state: PaperState, field_name: str) -> bool:
        """检查字段是否有值"""
        field_map = {
            "topic": state.topic,
            "title": state.title,
            "outline": state.outline,
            "content": state.content,
            "abstract": state.abstract,
            "references": state.references,
        }
        value = field_map.get(field_name)
        if value is None:
            return False
        if isinstance(value, list):
            return len(value) > 0
        return bool(value)

    def _validate_transitions(
        self,
        state: PaperState,
        result: StateValidationResult
    ):
        """验证状态转换"""
        # 如果是终态，不需要检查转换
        if state.status in (StateStatus.COMPLETED, StateStatus.CANCELLED):
            return

        # 检查阶段转换是否有效
        valid_next_phases = self.VALID_TRANSITIONS.get(state.phase, [])

        # 对于FAILED状态，允许重试
        if state.phase == PaperPhase.FAILED:
            if state.retry_count > 5:
                result.errors.append(StateValidationError(
                    field="retry_count",
                    message="Maximum retry count exceeded",
                    code="MAX_RETRY_EXCEEDED"
                ))

    def _validate_consistency(
        self,
        state: PaperState,
        result: StateValidationResult
    ):
        """验证数据一致性"""
        # 检查如果阶段是COMPLETED，则必须有content
        if state.phase == PaperPhase.COMPLETED:
            if not state.content or len(state.content) < 100:
                result.warnings.append(
                    "Completed paper should have substantial content"
                )

        # 检查如果引用了论文，但没有参考文献列表
        if state.cited_papers and not state.references:
            result.warnings.append(
                "Cited papers but no references provided"
            )

        # 检查如果论文有标题但没有摘要
        if state.title and not state.abstract:
            result.warnings.append(
                "Title present but no abstract"
            )

    def _run_custom_validators(
        self,
        state: PaperState,
        result: StateValidationResult
    ):
        """运行自定义验证器"""
        for validator in self._custom_validators:
            try:
                error_message = validator(state)
                if error_message:
                    result.errors.append(StateValidationError(
                        field="custom",
                        message=error_message,
                        code="CUSTOM_VALIDATION_FAILED"
                    ))
            except Exception as e:
                result.errors.append(StateValidationError(
                    field="custom",
                    message=f"Custom validator error: {str(e)}",
                    code="VALIDATOR_ERROR"
                ))

    def _check_warnings(
        self,
        state: PaperState,
        result: StateValidationResult
    ):
        """检查警告"""
        # 检查重试次数过多
        if state.retry_count > 3:
            result.warnings.append(
                f"High retry count: {state.retry_count}"
            )

        # 检查如果没有诊断结果
        if state.phase == PaperPhase.LITERATURE and not state.diagnostic_result:
            result.warnings.append(
                "No diagnostic result found before literature phase"
            )

    def validate_transition(
        self,
        from_state: PaperState,
        to_state: PaperState
    ) -> StateValidationResult:
        """
        验证状态转换

        Args:
            from_state: 原始状态
            to_state: 目标状态

        Returns:
            StateValidationResult: 验证结果
        """
        result = StateValidationResult(valid=True)

        # 检查是否可以转换
        if not from_state.can_transition_to(to_state.phase):
            result.errors.append(StateValidationError(
                field="phase",
                message=f"Invalid phase transition from {from_state.phase.value} to {to_state.phase.value}",
                code="INVALID_TRANSITION"
            ))

        # 检查目标状态的必填字段
        self._validate_required_fields(to_state, result)

        return result

    def get_validation_summary(self, state: PaperState) -> str:
        """获取验证摘要"""
        result = self.validate(state)
        if result.valid:
            return f"State is valid (phase: {state.phase.value})"
        else:
            return f"State has {len(result.errors)} error(s)"


def validate_state(state: PaperState) -> StateValidationResult:
    """便捷函数：验证状态"""
    validator = StateValidator()
    return validator.validate(state)