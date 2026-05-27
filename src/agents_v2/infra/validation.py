"""
输入验证器 - 增强输入验证

提供:
1. InputValidator: 输入验证器
2. OutputFormatter: 输出格式化器
3. 统一验证装饰器
"""
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.agents_v2.core.exceptions import ValidationError


class ValidationType(str, Enum):
    """验证类型"""
    REQUIRED = "required"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    EMAIL = "email"
    URL = "url"
    LENGTH = "length"
    RANGE = "range"
    PATTERN = "pattern"


@dataclass
class ValidationRule:
    """验证规则"""
    name: str
    validation_type: ValidationType
    required: bool = True
    default: Any = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    error_message: Optional[str] = None


class ValidationResult:
    """验证结果"""
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.valid: bool = True

    def add_error(self, message: str):
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str):
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


class InputValidator:
    """
    输入验证器

    使用方式:
        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, min_length=1, max_length=100)
        validator.add_rule("age", ValidationType.INTEGER, min_value=0, max_value=150)

        result = validator.validate({"name": "张三", "age": 25})
        if not result.valid:
            print(result.errors)
    """

    def __init__(self):
        self.rules: Dict[str, ValidationRule] = {}

    def add_rule(
        self,
        field_name: str,
        validation_type: ValidationType,
        required: bool = True,
        **kwargs
    ):
        """添加验证规则"""
        self.rules[field_name] = ValidationRule(
            name=field_name,
            validation_type=validation_type,
            required=required,
            **kwargs
        )

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """验证数据"""
        result = ValidationResult()

        for field_name, rule in self.rules.items():
            value = data.get(field_name)

            # 检查必填
            if value is None:
                if rule.required:
                    result.add_error(f"{field_name} is required")
                continue

            # 类型验证
            try:
                validated_value = self._validate_type(value, rule)
                data[field_name] = validated_value
            except Exception as e:
                result.add_error(f"{field_name}: {str(e)}")

        return result

    def _validate_type(self, value: Any, rule: ValidationRule) -> Any:
        """验证类型"""
        if rule.validation_type == ValidationType.STRING:
            return self._validate_string(value, rule)
        elif rule.validation_type == ValidationType.INTEGER:
            return self._validate_integer(value, rule)
        elif rule.validation_type == ValidationType.FLOAT:
            return self._validate_float(value, rule)
        elif rule.validation_type == ValidationType.LIST:
            return self._validate_list(value, rule)
        elif rule.validation_type == ValidationType.DICT:
            return self._validate_dict(value, rule)
        elif rule.validation_type == ValidationType.PATTERN:
            return self._validate_pattern(value, rule)
        return value

    def _validate_string(self, value: Any, rule: ValidationRule) -> str:
        """验证字符串"""
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")

        if rule.min_length and len(value) < rule.min_length:
            raise ValueError(f"Length must be at least {rule.min_length}")

        if rule.max_length and len(value) > rule.max_length:
            raise ValueError(f"Length must be at most {rule.max_length}")

        return value

    def _validate_integer(self, value: Any, rule: ValidationRule) -> int:
        """验证整数"""
        if isinstance(value, bool):
            raise ValueError("Boolean is not allowed for integer")

        int_value = int(value)

        if rule.min_value is not None and int_value < rule.min_value:
            raise ValueError(f"Value must be at least {rule.min_value}")

        if rule.max_value is not None and int_value > rule.max_value:
            raise ValueError(f"Value must be at most {rule.max_value}")

        return int_value

    def _validate_float(self, value: Any, rule: ValidationRule) -> float:
        """验证浮点数"""
        float_value = float(value)

        if rule.min_value is not None and float_value < rule.min_value:
            raise ValueError(f"Value must be at least {rule.min_value}")

        if rule.max_value is not None and float_value > rule.max_value:
            raise ValueError(f"Value must be at most {rule.max_value}")

        return float_value

    def _validate_list(self, value: Any, rule: ValidationRule) -> list:
        """验证列表"""
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value).__name__}")

        if rule.min_length and len(value) < rule.min_length:
            raise ValueError(f"List must have at least {rule.min_length} items")

        if rule.max_length and len(value) > rule.max_length:
            raise ValueError(f"List must have at most {rule.max_length} items")

        return value

    def _validate_dict(self, value: Any, rule: ValidationRule) -> dict:
        """验证字典"""
        if not isinstance(value, dict):
            raise ValueError(f"Expected dict, got {type(value).__name__}")
        return value

    def _validate_pattern(self, value: Any, rule: ValidationRule) -> str:
        """验证正则模式"""
        if not isinstance(value, str):
            raise ValueError(f"Expected string for pattern validation")

        if rule.pattern and not re.match(rule.pattern, value):
            error_msg = rule.error_message or f"Value does not match pattern {rule.pattern}"
            raise ValueError(error_msg)

        return value


class OutputFormatter:
    """
    输出格式化器 - 统一输出格式

    使用方式:
        formatter = OutputFormatter()

        # 格式化成功响应
        result = formatter.format_success(
            data={"result": "..."},
            message="Success"
        )

        # 格式化错误响应
        result = formatter.format_error(
            error="Some error",
            code="ERROR_001"
        )
    """

    @staticmethod
    def format_success(
        data: Any = None,
        message: str = "Success",
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """格式化成功响应"""
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": None  # 会在API层添加
        }
        if meta:
            response["meta"] = meta
        return response

    @staticmethod
    def format_error(
        error: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """格式化错误响应"""
        response = {
            "success": False,
            "error": {
                "message": error,
                "code": code or "UNKNOWN_ERROR"
            }
        }
        if details:
            response["error"]["details"] = details
        return response

    @staticmethod
    def format_paginated(
        data: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """格式化分页响应"""
        return {
            "success": True,
            "data": data,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }

    @staticmethod
    def format_agent_result(result: Any, agent_name: str) -> Dict[str, Any]:
        """格式化Agent执行结果"""
        return {
            "success": getattr(result, 'success', True),
            "agent": agent_name,
            "result": getattr(result, 'result', None),
            "quality_score": getattr(result, 'quality_score', 0.0),
            "reasoning": getattr(result, 'reasoning', None),
            "error": getattr(result, 'error', None)
        }


def validate_input(rules: Dict[str, ValidationRule]):
    """输入验证装饰器"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # 从kwargs获取data参数（通常是第一个或命名参数）
            data = kwargs.get('data') or (args[1] if len(args) > 1 else {})

            validator = InputValidator()
            for field_name, rule in rules.items():
                validator.add_rule(field_name, rule.validation_type,
                                 required=rule.required,
                                 min_length=rule.min_length,
                                 max_length=rule.max_length,
                                 min_value=rule.min_value,
                                 max_value=rule.max_value)

            result = validator.validate(data)
            if not result.valid:
                raise ValidationError(f"Validation failed: {result.errors}")

            return func(*args, **kwargs)
        return wrapper
    return decorator