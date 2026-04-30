"""
Input Validator - 输入验证器

提供用户输入的全面验证功能。
支持必填检查、类型验证、长度限制、范围限制、正则验证等。
"""
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from ...core.exceptions import ValidationError


class ValidationType(str, Enum):
    """验证类型枚举"""
    REQUIRED = "required"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    JSON = "json"
    HTML = "html"
    LENGTH = "length"
    RANGE = "range"
    PATTERN = "pattern"
    ENUM = "enum"
    IP_ADDRESS = "ip_address"
    CREDIT_CARD = "credit_card"


class ValidationLevel(str, Enum):
    """验证级别"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationRule:
    """验证规则定义"""
    name: str
    validation_type: ValidationType
    required: bool = False
    default: Any = None

    # 字符串相关
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    pattern_flags: int = 0

    # 数值相关
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    # 列表相关
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: bool = False
    item_type: Optional[ValidationType] = None

    # 枚举相关
    allowed_values: Optional[List[Any]] = None

    # 自定义验证
    custom_validator: Optional[callable] = None

    # 错误信息
    error_message: Optional[str] = None
    warning_message: Optional[str] = None

    # 验证级别
    level: ValidationLevel = ValidationLevel.ERROR


@dataclass
class ValidationError:
    """单个验证错误"""
    field: str
    message: str
    code: str
    level: ValidationLevel = ValidationLevel.ERROR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
            "code": self.code,
            "level": self.level.value if isinstance(self.level, Enum) else self.level
        }


@dataclass
class ValidationWarning:
    """验证警告（非致命错误）"""
    field: str
    message: str
    code: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
            "code": self.code
        }


class ValidationResult:
    """验证结果容器"""

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationWarning] = []
        self._validated_data: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

    @property
    def is_valid(self) -> bool:
        """是否有致命错误"""
        return not any(e.level == ValidationLevel.ERROR for e in self.errors)

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    def add_error(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        """添加错误"""
        self.errors.append(ValidationError(
            field=field,
            message=message,
            code=code,
            level=ValidationLevel.ERROR
        ))

    def add_warning(self, field: str, message: str, code: str = "VALIDATION_WARNING"):
        """添加警告"""
        self.warnings.append(ValidationWarning(
            field=field,
            message=message,
            code=code
        ))

    def set_validated_data(self, field: str, value: Any):
        """设置验证后的数据"""
        self._validated_data[field] = value

    def get_validated_data(self) -> Dict[str, Any]:
        """获取验证后的数据"""
        return self._validated_data.copy()

    def get_error_messages(self) -> List[str]:
        """获取所有错误消息"""
        return [e.message for e in self.errors]

    def get_warning_messages(self) -> List[str]:
        """获取所有警告消息"""
        return [w.message for w in self.warnings]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "data": self._validated_data,
            "metadata": self.metadata
        }

    def __repr__(self) -> str:
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        return f"ValidationResult(valid={self.is_valid}, errors={error_count}, warnings={warning_count})"


class InputValidator:
    """
    输入验证器

    支持的验证类型:
    - 必填检查 (required)
    - 字符串验证 (string)
    - 整数验证 (integer)
    - 浮点数验证 (float)
    - 布尔验证 (boolean)
    - 列表验证 (list)
    - 字典验证 (dict)
    - 邮箱验证 (email)
    - URL验证 (url)
    - 电话号码验证 (phone)
    - 日期验证 (date)
    - 日期时间验证 (datetime)
    - UUID验证 (uuid)
    - JSON验证 (json)
    - HTML验证 (html)
    - 长度验证 (length)
    - 范围验证 (range)
    - 正则验证 (pattern)
    - 枚举验证 (enum)

    使用示例:
        validator = InputValidator()

        # 添加规则
        validator.add_rule("username", ValidationType.STRING,
                          required=True, min_length=3, max_length=20)
        validator.add_rule("email", ValidationType.EMAIL, required=True)
        validator.add_rule("age", ValidationType.INTEGER,
                          min_value=0, max_value=150)
        validator.add_rule("tags", ValidationType.LIST,
                          max_items=5, unique_items=True)

        # 验证数据
        data = {"username": "john", "email": "john@example.com", "age": 25}
        result = validator.validate(data)

        if not result.is_valid:
            for error in result.errors:
                print(f"{error.field}: {error.message}")
    """

    # 内置正则模式
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    URL_PATTERN = r'^https?://[^\s/$.?#].[^\s]*$'
    PHONE_PATTERN = r'^1[3-9]\d{9}$'
    DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'
    DATETIME_PATTERN = r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
    UUID_PATTERN = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
    IP_PATTERN = r'^(\d{1,3}\.){3}\d{1,3}$'
    HTML_TAG_PATTERN = r'<[^>]+>'

    def __init__(self):
        self.rules: Dict[str, ValidationRule] = {}
        self._validated_count = 0

    def add_rule(
        self,
        field_name: str,
        validation_type: Union[ValidationType, str],
        required: bool = False,
        **kwargs
    ) -> "InputValidator":
        """添加验证规则（支持链式调用）"""
        if isinstance(validation_type, str):
            try:
                validation_type = ValidationType(validation_type)
            except ValueError:
                raise ValueError(f"Invalid validation type: {validation_type}")

        # 处理 allowed_values 参数，确保是列表
        if 'allowed_values' in kwargs:
            allowed = kwargs['allowed_values']
            if not isinstance(allowed, list):
                allowed = [allowed]
            kwargs['allowed_values'] = allowed

        self.rules[field_name] = ValidationRule(
            name=field_name,
            validation_type=validation_type,
            required=required,
            **kwargs
        )
        return self

    def add_rules(self, rules: Dict[str, ValidationRule]) -> "InputValidator":
        """批量添加规则"""
        for field_name, rule in rules.items():
            self.rules[field_name] = rule
        return self

    def remove_rule(self, field_name: str) -> bool:
        """移除规则"""
        if field_name in self.rules:
            del self.rules[field_name]
            return True
        return False

    def clear_rules(self):
        """清除所有规则"""
        self.rules.clear()

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """验证数据"""
        result = ValidationResult()
        self._validated_count += 1

        # 如果没有规则，直接返回成功
        if not self.rules:
            result.metadata["note"] = "No validation rules defined"
            return result

        # 遍历所有规则进行验证
        for field_name, rule in self.rules.items():
            value = data.get(field_name)
            field_result = self._validate_field(field_name, value, rule, data)
            result.errors.extend(field_result.errors)
            result.warnings.extend(field_result.warnings)

            # 如果验证成功，保存转换后的值
            if not any(e.field == field_name for e in field_result.errors):
                if field_result.validated_value is not None:
                    result.set_validated_data(field_name, field_result.validated_value)
                elif value is not None:
                    result.set_validated_data(field_name, value)

        # 添加元数据
        result.metadata["rules_count"] = len(self.rules)
        result.metadata["validated_fields"] = list(self.rules.keys())

        return result

    def _validate_field(
        self,
        field_name: str,
        value: Any,
        rule: ValidationRule,
        full_data: Dict[str, Any]
    ) -> ValidationResult:
        """验证单个字段"""
        result = ValidationResult()

        # 处理默认值
        if value is None and rule.default is not None:
            value = rule.default if not callable(rule.default) else rule.default()

        # 必填检查
        if rule.required and (value is None or value == ""):
            result.add_error(
                field_name,
                rule.error_message or f"{field_name} is required",
                "REQUIRED_FIELD_MISSING"
            )
            return result

        # 如果字段不是必填且值为空，直接通过
        if value is None or value == "":
            return result

        # 类型验证
        validated_value = value
        try:
            validated_value = self._validate_type(value, rule)
        except ValueError as e:
            result.add_error(
                field_name,
                str(e),
                "TYPE_VALIDATION_FAILED"
            )
            return result

        # 字符串长度验证
        if rule.validation_type in [ValidationType.STRING, ValidationType.PATTERN]:
            if isinstance(validated_value, str):
                if rule.min_length and len(validated_value) < rule.min_length:
                    result.add_error(
                        field_name,
                        rule.error_message or f"{field_name} must be at least {rule.min_length} characters",
                        "STRING_TOO_SHORT"
                    )
                if rule.max_length and len(validated_value) > rule.max_length:
                    result.add_error(
                        field_name,
                        rule.error_message or f"{field_name} must be at most {rule.max_length} characters",
                        "STRING_TOO_LONG"
                    )

        # 数值范围验证
        if rule.validation_type in [ValidationType.INTEGER, ValidationType.FLOAT, ValidationType.RANGE]:
            if rule.min_value is not None and validated_value < rule.min_value:
                result.add_error(
                    field_name,
                    rule.error_message or f"{field_name} must be at least {rule.min_value}",
                    "VALUE_TOO_SMALL"
                )
            if rule.max_value is not None and validated_value > rule.max_value:
                result.add_error(
                    field_name,
                    rule.error_message or f"{field_name} must be at most {rule.max_value}",
                    "VALUE_TOO_LARGE"
                )

        # 列表长度验证
        if rule.validation_type == ValidationType.LIST:
            if isinstance(validated_value, list):
                if rule.min_items and len(validated_value) < rule.min_items:
                    result.add_error(
                        field_name,
                        rule.error_message or f"{field_name} must have at least {rule.min_items} items",
                        "LIST_TOO_SHORT"
                    )
                if rule.max_items and len(validated_value) > rule.max_items:
                    result.add_error(
                        field_name,
                        rule.error_message or f"{field_name} must have at most {rule.max_items} items",
                        "LIST_TOO_LONG"
                    )
                if rule.unique_items and len(validated_value) != len(set(str(i) for i in validated_value)):
                    result.add_warning(
                        field_name,
                        f"{field_name} contains duplicate items",
                        "DUPLICATE_ITEMS"
                    )

        # 枚举验证
        if rule.allowed_values is not None:
            if validated_value not in rule.allowed_values:
                result.add_error(
                    field_name,
                    rule.error_message or f"{field_name} must be one of {rule.allowed_values}",
                    "INVALID_ENUM_VALUE"
                )

        # 正则验证
        if rule.pattern is not None:
            try:
                flags = rule.pattern_flags if hasattr(rule, 'pattern_flags') else 0
                if not re.match(rule.pattern, str(validated_value), flags):
                    result.add_error(
                        field_name,
                        rule.error_message or f"{field_name} does not match required pattern",
                        "PATTERN_MISMATCH"
                    )
            except re.error as e:
                result.add_error(field_name, f"Invalid regex pattern: {e}", "INVALID_PATTERN")

        # 自定义验证器
        if rule.custom_validator is not None:
            try:
                custom_result = rule.custom_validator(validated_value, full_data)
                if isinstance(custom_result, bool):
                    if not custom_result:
                        result.add_error(
                            field_name,
                            rule.error_message or f"{field_name} failed custom validation",
                            "CUSTOM_VALIDATION_FAILED"
                        )
                elif isinstance(custom_result, tuple):
                    is_valid, message = custom_result
                    if not is_valid:
                        result.add_error(
                            field_name,
                            message or f"{field_name} failed custom validation",
                            "CUSTOM_VALIDATION_FAILED"
                        )
                elif isinstance(custom_result, ValidationResult):
                    result.errors.extend(custom_result.errors)
                    result.warnings.extend(custom_result.warnings)
            except Exception as e:
                result.add_error(
                    field_name,
                    f"Custom validation error: {str(e)}",
                    "CUSTOM_VALIDATION_ERROR"
                )

        # 保存验证后的值
        result.validated_value = validated_value

        return result

    def _validate_type(self, value: Any, rule: ValidationRule) -> Any:
        """根据规则验证类型并转换值"""
        validation_type = rule.validation_type

        # 字符串验证
        if validation_type == ValidationType.STRING:
            return str(value)

        # 整数验证
        if validation_type == ValidationType.INTEGER:
            if isinstance(value, bool):
                raise ValueError("Boolean is not allowed for integer field")
            if isinstance(value, float):
                if value != int(value):
                    raise ValueError(f"Expected integer, got float {value}")
                return int(value)
            return int(value)

        # 浮点数验证
        if validation_type == ValidationType.FLOAT:
            return float(value)

        # 布尔验证
        if validation_type == ValidationType.BOOLEAN:
            if isinstance(value, str):
                if value.lower() in ('true', '1', 'yes', 'on'):
                    return True
                elif value.lower() in ('false', '0', 'no', 'off'):
                    return False
                raise ValueError(f"Invalid boolean string: {value}")
            return bool(value)

        # 列表验证
        if validation_type == ValidationType.LIST:
            if isinstance(value, str):
                return [v.strip() for v in value.split(',')]
            if not isinstance(value, list):
                return [value]
            return list(value)

        # 字典验证
        if validation_type == ValidationType.DICT:
            if isinstance(value, str):
                import json
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON string: {value}")
            if not isinstance(value, dict):
                raise ValueError(f"Expected dict, got {type(value).__name__}")
            return value

        # 邮箱验证
        if validation_type == ValidationType.EMAIL:
            str_value = str(value)
            if not re.match(self.EMAIL_PATTERN, str_value):
                raise ValueError(f"Invalid email format: {str_value}")
            return str_value.lower()

        # URL验证
        if validation_type == ValidationType.URL:
            str_value = str(value)
            if not re.match(self.URL_PATTERN, str_value):
                raise ValueError(f"Invalid URL format: {str_value}")
            return str_value

        # 电话号码验证
        if validation_type == ValidationType.PHONE:
            str_value = str(value).replace(' ', '').replace('-', '')
            if not re.match(self.PHONE_PATTERN, str_value):
                raise ValueError(f"Invalid phone number: {str_value}")
            return str_value

        # 日期验证
        if validation_type == ValidationType.DATE:
            str_value = str(value)
            if not re.match(self.DATE_PATTERN, str_value):
                raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {str_value}")
            from datetime import datetime
            datetime.strptime(str_value, '%Y-%m-%d')
            return str_value

        # 日期时间验证
        if validation_type == ValidationType.DATETIME:
            str_value = str(value)
            if not re.match(self.DATETIME_PATTERN, str_value):
                raise ValueError(f"Invalid datetime format: {str_value}")
            from datetime import datetime
            # 尝试多种格式
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M']:
                try:
                    datetime.strptime(str_value, fmt)
                    break
                except ValueError:
                    continue
            return str_value

        # UUID验证
        if validation_type == ValidationType.UUID:
            str_value = str(value)
            if not re.match(self.UUID_PATTERN, str_value.lower()):
                raise ValueError(f"Invalid UUID format: {str_value}")
            return str_value.lower()

        # JSON验证
        if validation_type == ValidationType.JSON:
            if isinstance(value, dict):
                return value
            import json
            return json.loads(str(value))

        # HTML验证
        if validation_type == ValidationType.HTML:
            str_value = str(value)
            if re.search(self.HTML_TAG_PATTERN, str_value):
                raise ValueError(f"{field_name} contains HTML tags which are not allowed")
            return str_value

        # IP地址验证
        if validation_type == ValidationType.IP_ADDRESS:
            str_value = str(value)
            parts = str_value.split('.')
            if len(parts) != 4:
                raise ValueError(f"Invalid IP address: {str_value}")
            for part in parts:
                try:
                    num = int(part)
                    if num < 0 or num > 255:
                        raise ValueError(f"Invalid IP address: {str_value}")
                except ValueError:
                    raise ValueError(f"Invalid IP address: {str_value}")
            return str_value

        # 信用卡验证 (使用 Luhn 算法)
        if validation_type == ValidationType.CREDIT_CARD:
            str_value = re.sub(r'\D', '', str(value))
            if not self._luhn_check(str_value):
                raise ValueError(f"Invalid credit card number: {str_value}")
            return str_value

        # 默认返回原值
        return value

    def _luhn_check(self, card_number: str) -> bool:
        """Luhn算法验证信用卡号码"""
        if not card_number.isdigit():
            return False

        digits = [int(d) for d in card_number]
        checksum = 0

        # 从右往左
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def validate_multiple(
        self,
        data_list: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """验证多个数据项"""
        return [self.validate(data) for data in data_list]

    def get_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        return {
            "total_rules": len(self.rules),
            "validated_count": self._validated_count,
            "rule_types": {
                rule.validation_type.value: sum(
                    1 for r in self.rules.values() if r.validation_type == rule.validation_type
                )
                for rule in self.rules.values()
            }
        }


def validate_dict(data: Dict[str, Any], rules: Dict[str, ValidationRule]) -> ValidationResult:
    """便捷函数：使用规则字典验证数据"""
    validator = InputValidator()
    validator.add_rules(rules)
    return validator.validate(data)


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> ValidationResult:
    """便捷函数：检查必填字段"""
    result = ValidationResult()
    for field_name in required_fields:
        if field_name not in data or data[field_name] is None or data[field_name] == "":
            result.add_error(field_name, f"{field_name} is required", "REQUIRED_FIELD_MISSING")
    return result