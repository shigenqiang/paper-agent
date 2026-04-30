"""
输入验证器单元测试

测试输入验证功能
"""
import pytest
from src.agents_v2._archive.validation.input_validator import (
    InputValidator,
    ValidationRule,
    ValidationResult,
    ValidationType,
    ValidationLevel,
    validate_dict,
    validate_required_fields,
)


class TestValidationType:
    """ValidationType 枚举测试"""

    def test_all_validation_types_exist(self):
        """测试所有验证类型存在"""
        assert ValidationType.STRING.value == "string"
        assert ValidationType.INTEGER.value == "integer"
        assert ValidationType.EMAIL.value == "email"
        assert ValidationType.URL.value == "url"
        assert ValidationType.PHONE.value == "phone"
        assert ValidationType.UUID.value == "uuid"


class TestValidationResult:
    """ValidationResult 测试"""

    def test_empty_result(self):
        """测试空结果"""
        result = ValidationResult()
        assert result.is_valid
        assert not result.has_warnings
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error(self):
        """测试添加错误"""
        result = ValidationResult()
        result.add_error("name", "Name is required", "REQUIRED")
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "name"
        assert result.errors[0].code == "REQUIRED"

    def test_add_warning(self):
        """测试添加警告"""
        result = ValidationResult()
        result.add_warning("email", "Email format could be improved", "FORMAT")
        assert result.is_valid
        assert result.has_warnings
        assert len(result.warnings) == 1

    def test_to_dict(self):
        """测试转换为字典"""
        result = ValidationResult()
        result.add_error("name", "Required", "REQUIRED")
        d = result.to_dict()
        assert d["valid"] is False
        assert len(d["errors"]) == 1


class TestInputValidator:
    """InputValidator 测试"""

    def test_basic_string_validation(self):
        """测试基本字符串验证"""
        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, required=True)

        result = validator.validate({"name": "John"})
        assert result.is_valid

    def test_required_field_missing(self):
        """测试必填字段缺失"""
        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, required=True)

        result = validator.validate({})
        assert not result.is_valid
        assert any("required" in e.message.lower() for e in result.errors)

    def test_string_min_length(self):
        """测试字符串最小长度"""
        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, min_length=3)

        result = validator.validate({"name": "Jo"})
        assert not result.is_valid

    def test_string_max_length(self):
        """测试字符串最大长度"""
        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, max_length=5)

        result = validator.validate({"name": "John Doe"})
        assert not result.is_valid

    def test_integer_validation(self):
        """测试整数验证"""
        validator = InputValidator()
        validator.add_rule("age", ValidationType.INTEGER)

        result = validator.validate({"age": 25})
        assert result.is_valid
        assert result.get_validated_data()["age"] == 25

    def test_integer_from_string(self):
        """测试字符串转整数"""
        validator = InputValidator()
        validator.add_rule("age", ValidationType.INTEGER)

        result = validator.validate({"age": "25"})
        assert result.is_valid
        assert result.get_validated_data()["age"] == 25

    def test_integer_min_max(self):
        """测试整数范围"""
        validator = InputValidator()
        validator.add_rule("age", ValidationType.INTEGER, min_value=0, max_value=150)

        result = validator.validate({"age": 200})
        assert not result.is_valid

    def test_float_validation(self):
        """测试浮点数验证"""
        validator = InputValidator()
        validator.add_rule("price", ValidationType.FLOAT)

        result = validator.validate({"price": 19.99})
        assert result.is_valid

    def test_boolean_validation(self):
        """测试布尔验证"""
        validator = InputValidator()
        validator.add_rule("active", ValidationType.BOOLEAN)

        result = validator.validate({"active": "true"})
        assert result.is_valid
        assert result.get_validated_data()["active"] is True

    def test_list_validation(self):
        """测试列表验证"""
        validator = InputValidator()
        validator.add_rule("tags", ValidationType.LIST)

        result = validator.validate({"tags": ["a", "b", "c"]})
        assert result.is_valid

    def test_list_from_string(self):
        """测试字符串转列表"""
        validator = InputValidator()
        validator.add_rule("tags", ValidationType.LIST)

        result = validator.validate({"tags": "a, b, c"})
        assert result.is_valid
        assert result.get_validated_data()["tags"] == ["a", "b", "c"]

    def test_list_max_items(self):
        """测试列表最大项数"""
        validator = InputValidator()
        validator.add_rule("tags", ValidationType.LIST, max_items=2)

        result = validator.validate({"tags": ["a", "b", "c"]})
        assert not result.is_valid

    def test_email_validation(self):
        """测试邮箱验证"""
        validator = InputValidator()
        validator.add_rule("email", ValidationType.EMAIL)

        result = validator.validate({"email": "test@example.com"})
        assert result.is_valid

        result = validator.validate({"email": "invalid-email"})
        assert not result.is_valid

    def test_url_validation(self):
        """测试URL验证"""
        validator = InputValidator()
        validator.add_rule("url", ValidationType.URL)

        result = validator.validate({"url": "https://example.com"})
        assert result.is_valid

        result = validator.validate({"url": "not-a-url"})
        assert not result.is_valid

    def test_phone_validation(self):
        """测试电话号码验证"""
        validator = InputValidator()
        validator.add_rule("phone", ValidationType.PHONE)

        result = validator.validate({"phone": "13812345678"})
        assert result.is_valid

        result = validator.validate({"phone": "12345"})
        assert not result.is_valid

    def test_date_validation(self):
        """测试日期验证"""
        validator = InputValidator()
        validator.add_rule("date", ValidationType.DATE)

        result = validator.validate({"date": "2024-01-15"})
        assert result.is_valid

        result = validator.validate({"date": "2024/01/15"})
        assert not result.is_valid

    def test_uuid_validation(self):
        """测试UUID验证"""
        validator = InputValidator()
        validator.add_rule("uuid", ValidationType.UUID)

        result = validator.validate({"uuid": "550e8400-e29b-41d4-a716-446655440000"})
        assert result.is_valid

        result = validator.validate({"uuid": "not-a-uuid"})
        assert not result.is_valid

    def test_pattern_validation(self):
        """测试正则验证"""
        validator = InputValidator()
        validator.add_rule("code", ValidationType.PATTERN, pattern=r'^[A-Z]{3}-\d{4}$')

        result = validator.validate({"code": "ABC-1234"})
        assert result.is_valid

        result = validator.validate({"code": "abc-1234"})
        assert not result.is_valid

    def test_enum_validation(self):
        """测试枚举验证"""
        validator = InputValidator()
        validator.add_rule("status", ValidationType.ENUM, allowed_values=["active", "inactive", "pending"])

        result = validator.validate({"status": "active"})
        assert result.is_valid

        result = validator.validate({"status": "unknown"})
        assert not result.is_valid

    def test_custom_validator(self):
        """测试自定义验证器"""
        def positive_number(value, data):
            return value > 0, f"Expected positive number, got {value}"

        validator = InputValidator()
        validator.add_rule("count", ValidationType.INTEGER, custom_validator=positive_number)

        result = validator.validate({"count": 5})
        assert result.is_valid

        result = validator.validate({"count": -1})
        assert not result.is_valid

    def test_chainable_api(self):
        """测试链式API"""
        validator = (
            InputValidator()
            .add_rule("name", ValidationType.STRING, required=True)
            .add_rule("email", ValidationType.EMAIL)
            .add_rule("age", ValidationType.INTEGER, min_value=0)
        )

        result = validator.validate({"name": "John", "email": "john@example.com", "age": 25})
        assert result.is_valid

    def test_default_value(self):
        """测试默认值"""
        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, default="Anonymous")

        result = validator.validate({})
        assert result.is_valid
        assert result.get_validated_data()["name"] == "Anonymous"

    def test_callable_default(self):
        """测试函数默认值"""
        validator = InputValidator()
        validator.add_rule("id", ValidationType.INTEGER, default=lambda: 42)

        result = validator.validate({})
        assert result.is_valid
        assert result.get_validated_data()["id"] == 42


class TestValidateDict:
    """validate_dict 便捷函数测试"""

    def test_validate_dict_basic(self):
        """测试基本功能"""
        rules = {
            "name": ValidationRule("name", ValidationType.STRING, required=True),
            "age": ValidationRule("age", ValidationType.INTEGER),
        }

        result = validate_dict({"name": "John", "age": 25}, rules)
        assert result.is_valid


class TestValidateRequiredFields:
    """validate_required_fields 便捷函数测试"""

    def test_validate_required_fields(self):
        """测试必填字段检查"""
        result = validate_required_fields({"name": "John"}, ["name", "email"])
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "email"


class TestCreditCardValidation:
    """信用卡验证测试"""

    def test_valid_card(self):
        """测试有效信用卡"""
        validator = InputValidator()
        validator.add_rule("card", ValidationType.CREDIT_CARD)

        # 有效Visa卡号
        result = validator.validate({"card": "4111111111111111"})
        assert result.is_valid

    def test_invalid_card(self):
        """测试无效信用卡"""
        validator = InputValidator()
        validator.add_rule("card", ValidationType.CREDIT_CARD)

        result = validator.validate({"card": "1234567890123456"})
        assert not result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])