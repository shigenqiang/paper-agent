"""
单元测试 - 验证器和日志
"""
import pytest


class TestInputValidator:
    """测试输入验证器"""

    def test_validate_required_string(self):
        """测试必填字符串验证"""
        from src.agents_v2.core.validators import InputValidator, ValidationType

        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, required=True)

        # 有效数据
        result = validator.validate({"name": "张三"})
        assert result.valid

        # 空数据
        result = validator.validate({})
        assert not result.valid
        assert "name is required" in result.errors[0]

    def test_validate_string_length(self):
        """测试字符串长度验证"""
        from src.agents_v2.core.validators import InputValidator, ValidationType

        validator = InputValidator()
        validator.add_rule("name", ValidationType.STRING, min_length=2, max_length=10)

        # 太短
        result = validator.validate({"name": "张"})
        assert not result.valid

        # 太长
        result = validator.validate({"name": "张三四五六七八九十甲乙丙丁"})
        assert not result.valid

        # 有效
        result = validator.validate({"name": "张三"})
        assert result.valid

    def test_validate_integer_range(self):
        """测试整数范围验证"""
        from src.agents_v2.core.validators import InputValidator, ValidationType

        validator = InputValidator()
        validator.add_rule("age", ValidationType.INTEGER, min_value=0, max_value=150)

        # 太小
        result = validator.validate({"age": -1})
        assert not result.valid

        # 太大
        result = validator.validate({"age": 200})
        assert not result.valid

        # 有效
        result = validator.validate({"age": 25})
        assert result.valid

    def test_validate_list(self):
        """测试列表验证"""
        from src.agents_v2.core.validators import InputValidator, ValidationType

        validator = InputValidator()
        validator.add_rule("tags", ValidationType.LIST, min_length=1, max_length=5)

        # 空列表
        result = validator.validate({"tags": []})
        assert not result.valid

        # 有效
        result = validator.validate({"tags": ["python", "ai"]})
        assert result.valid

    def test_validate_pattern(self):
        """测试正则验证"""
        from src.agents_v2.core.validators import InputValidator, ValidationType

        validator = InputValidator()
        validator.add_rule("email", ValidationType.PATTERN,
                          pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')

        # 无效邮箱
        result = validator.validate({"email": "invalid"})
        assert not result.valid

        # 有效邮箱
        result = validator.validate({"email": "test@example.com"})
        assert result.valid


class TestOutputFormatter:
    """测试输出格式化器"""

    def test_format_success(self):
        """测试格式化成功响应"""
        from src.agents_v2.core.validators import OutputFormatter

        result = OutputFormatter.format_success(
            data={"result": "test"},
            message="Success"
        )

        assert result["success"] is True
        assert result["message"] == "Success"
        assert result["data"] == {"result": "test"}

    def test_format_error(self):
        """测试格式化错误响应"""
        from src.agents_v2.core.validators import OutputFormatter

        result = OutputFormatter.format_error(
            error="Something went wrong",
            code="ERROR_001"
        )

        assert result["success"] is False
        assert result["error"]["message"] == "Something went wrong"
        assert result["error"]["code"] == "ERROR_001"

    def test_format_paginated(self):
        """测试格式化分页响应"""
        from src.agents_v2.core.validators import OutputFormatter

        result = OutputFormatter.format_paginated(
            data=[1, 2, 3],
            total=100,
            page=1,
            page_size=10
        )

        assert result["success"] is True
        assert len(result["data"]) == 3
        assert result["pagination"]["total"] == 100
        assert result["pagination"]["total_pages"] == 10

    def test_format_agent_result(self):
        """测试格式化Agent结果"""
        from src.agents_v2.core.validators import OutputFormatter

        class MockResult:
            success = True
            result = {"key": "value"}
            quality_score = 0.85
            reasoning = "Test reasoning"
            error = None

        result = OutputFormatter.format_agent_result(MockResult(), "test_agent")

        assert result["success"] is True
        assert result["agent"] == "test_agent"
        assert result["quality_score"] == 0.85


class TestValidationRule:
    """测试验证规则"""

    def test_validation_rule_creation(self):
        """测试验证规则创建"""
        from src.agents_v2.core.validators import ValidationRule, ValidationType

        rule = ValidationRule(
            name="test_field",
            validation_type=ValidationType.STRING,
            required=True,
            min_length=1,
            max_length=100
        )

        assert rule.name == "test_field"
        assert rule.validation_type == ValidationType.STRING
        assert rule.required is True
        assert rule.min_length == 1
        assert rule.max_length == 100


class TestValidationResult:
    """测试验证结果"""

    def test_add_error(self):
        """测试添加错误"""
        from src.agents_v2.core.validators import ValidationResult

        result = ValidationResult()
        result.add_error("Field is required")

        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0] == "Field is required"

    def test_add_warning(self):
        """测试添加警告"""
        from src.agents_v2.core.validators import ValidationResult

        result = ValidationResult()
        result.add_warning("Consider using a stronger password")

        assert result.valid
        assert len(result.warnings) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
