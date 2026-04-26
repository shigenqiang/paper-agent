"""
工具规格定义 - 统一工具描述和验证规范

ToolSpec: 工具的完整规格定义
ParameterSpec: 单个参数的规格定义
ValidationResult: 参数验证结果
ToolResult: 工具执行结果
"""
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field


class ParameterType(str, Enum):
    """参数类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ValidationResult:
    """参数验证结果"""

    def __init__(self, success: bool, error: Optional[str] = None, validated_params: Optional[Dict] = None):
        self.success = success
        self.error = error
        self.validated_params = validated_params or {}


class ToolResult:
    """工具执行结果"""

    def __init__(self, success: bool, result: Any = None, error: Optional[str] = None, execution_time: float = 0.0):
        self.success = success
        self.result = result
        self.error = error
        self.execution_time = execution_time


class ToolSpec:
    """
    工具规格定义

    包含工具的完整元信息，用于注册、验证和执行
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: List["ParameterSpec"],
        handler: Callable,
        result_schema: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        examples: Optional[List[Dict]] = None,
        category: str = "general"
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.result_schema = result_schema
        self.tags = tags or []
        self.examples = examples or []
        self.category = category

    def to_openai_schema(self) -> Dict[str, Any]:
        """转换为OpenAI工具格式"""
        properties = {}
        required = []

        for param in self.parameters:
            param_dict = {
                "type": param.type.value if isinstance(param.type, ParameterType) else param.type,
                "description": param.description
            }

            if param.enum:
                param_dict["enum"] = param.enum

            if param.default is not None:
                param_dict["default"] = param.default

            properties[param.name] = param_dict

            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def validate(self, arguments: Dict) -> ValidationResult:
        """验证参数"""
        validated = {}

        for param in self.parameters:
            value = arguments.get(param.name)

            # 检查必需参数
            if value is None:
                if param.required:
                    return ValidationResult(success=False, error=f"Missing required parameter: {param.name}")
                if param.default is not None:
                    validated[param.name] = param.default
                continue

            # 类型检查
            expected_type = param.type.value if isinstance(param.type, ParameterType) else param.type
            if not self._check_type(value, expected_type):
                return ValidationResult(
                    success=False,
                    error=f"Invalid type for {param.name}: expected {expected_type}, got {type(value).__name__}"
                )

            # 枚举值检查
            if param.enum and value not in param.enum:
                return ValidationResult(
                    success=False,
                    error=f"Invalid value for {param.name}: must be one of {param.enum}"
                )

            validated[param.name] = value

        return ValidationResult(success=True, validated_params=validated)

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """检查值类型"""
        type_map = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True

        return isinstance(value, expected)


class ParameterSpec:
    """
    参数规格定义

    用于定义工具的参数schema
    """

    def __init__(
        self,
        name: str,
        type: ParameterType | str,
        description: str = "",
        required: bool = True,
        default: Any = None,
        enum: Optional[List[Any]] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ):
        self.name = name
        self.type = type
        self.description = description
        self.required = required
        self.default = default
        self.enum = enum
        self.min_value = min_value
        self.max_value = max_value

    def validate_value(self, value: Any) -> bool:
        """验证单个值"""
        if value is None:
            return not self.required

        # 范围检查
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False

        # 枚举检查
        if self.enum and value not in self.enum:
            return False

        return True
