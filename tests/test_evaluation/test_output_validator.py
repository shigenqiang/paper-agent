"""
Output Validator Tests

Tests for:
- OutputValidator: Validates output quality and format
- SchemaValidator: Schema validation
- QualityVerifier: Quality verification
"""
import pytest
from src.agents_v2.evaluation.output_validator import (
    OutputValidator,
    SchemaValidator,
    QualityVerifier,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    validate_output,
    verify_quality
)


class TestValidationIssue:
    """ValidationIssue Tests"""

    def test_create_issue(self):
        """Test creating a validation issue"""
        issue = ValidationIssue(
            issue_id="test_issue",
            severity=ValidationSeverity.ERROR,
            category="test",
            message="Test error message",
            location="line 10",
            suggestion="Fix this"
        )
        assert issue.issue_id == "test_issue"
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.category == "test"
        assert issue.message == "Test error message"
        assert issue.location == "line 10"
        assert issue.suggestion == "Fix this"


class TestValidationResult:
    """ValidationResult Tests"""

    def test_valid_result(self):
        """Test valid validation result"""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.issues == []
        assert result.score == 1.0

    def test_add_error_issue(self):
        """Test adding an error issue"""
        result = ValidationResult(is_valid=True)
        issue = ValidationIssue(
            issue_id="error",
            severity=ValidationSeverity.ERROR,
            category="test",
            message="Error message"
        )
        result.add_issue(issue)

        assert result.is_valid is False
        assert len(result.issues) == 1

    def test_add_warning_issue(self):
        """Test adding a warning issue"""
        result = ValidationResult(is_valid=True)
        issue = ValidationIssue(
            issue_id="warning",
            severity=ValidationSeverity.WARNING,
            category="test",
            message="Warning message"
        )
        result.add_issue(issue)

        assert result.is_valid is True
        assert len(result.issues) == 1

    def test_compute_score_no_issues(self):
        """Test computing score with no issues"""
        result = ValidationResult(is_valid=True)
        result.compute_score()
        assert result.score == 1.0

    def test_compute_score_with_errors(self):
        """Test computing score with errors"""
        result = ValidationResult(is_valid=True)
        result.add_issue(ValidationIssue(
            issue_id="e1",
            severity=ValidationSeverity.ERROR,
            category="test",
            message="Error 1"
        ))
        result.add_issue(ValidationIssue(
            issue_id="e2",
            severity=ValidationSeverity.ERROR,
            category="test",
            message="Error 2"
        ))
        result.compute_score()
        # 2 errors: 1.0 - 2*0.2 = 0.6
        assert result.score == 0.6

    def test_compute_score_with_warnings(self):
        """Test computing score with warnings"""
        result = ValidationResult(is_valid=True)
        result.add_issue(ValidationIssue(
            issue_id="w1",
            severity=ValidationSeverity.WARNING,
            category="test",
            message="Warning 1"
        ))
        result.add_issue(ValidationIssue(
            issue_id="w2",
            severity=ValidationSeverity.WARNING,
            category="test",
            message="Warning 2"
        ))
        result.compute_score()
        # 2 warnings: 1.0 - 2*0.05 = 0.9
        assert result.score == 0.9


class TestSchemaValidator:
    """SchemaValidator Tests"""

    def test_validate_without_schema(self):
        """Test validation without schema"""
        validator = SchemaValidator()
        result = validator.validate({"key": "value"})
        assert result.is_valid is True

    def test_validate_missing_required_field(self):
        """Test validation with missing required field"""
        schema = {
            "required": ["name", "age"]
        }
        validator = SchemaValidator(schema)
        result = validator.validate({"name": "John"})

        assert result.is_valid is False
        assert any("age" in issue.message for issue in result.issues)

    def test_validate_correct_type(self):
        """Test validation with correct type"""
        schema = {
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
        validator = SchemaValidator(schema)
        result = validator.validate({"name": "John", "age": 25})

        assert result.is_valid is True

    def test_validate_incorrect_type(self):
        """Test validation with incorrect type"""
        schema = {
            "properties": {
                "age": {"type": "integer"}
            }
        }
        validator = SchemaValidator(schema)
        result = validator.validate({"age": "twenty-five"})

        assert result.is_valid is False
        assert any("age" in issue.message for issue in result.issues)


class TestOutputValidator:
    """OutputValidator Tests"""

    def setup_method(self):
        self.validator = OutputValidator()

    def test_validate_empty_output(self):
        """Test validating empty output"""
        result = self.validator.validate("")
        assert result.is_valid is False
        # The empty content check issues "empty" or "空" message
        assert len(result.issues) > 0

    def test_validate_whitespace_output(self):
        """Test validating whitespace-only output"""
        result = self.validator.validate("   \n\t  ")
        assert result.is_valid is False

    def test_validate_short_output(self):
        """Test validating short output"""
        result = self.validator.validate("Short content")
        # Should have issues for short content
        assert len(result.issues) > 0

    def test_validate_long_output(self):
        """Test validating very long output"""
        long_content = "A" * 150000
        result = self.validator.validate(long_content)
        # Should have a warning about length
        assert any(issue.severity == ValidationSeverity.WARNING for issue in result.issues)

    def test_validate_normal_output(self):
        """Test validating normal output"""
        normal_content = """
        This is a normal academic paper section.
        It contains multiple sentences with proper content.
        The abstract should be here.
        The introduction follows.
        """
        result = self.validator.validate(normal_content)
        # Should be valid with no errors
        assert result.is_valid is True

    def test_validate_with_forbidden_content(self):
        """Test detecting forbidden content"""
        result = self.validator.validate("This is lorem ipsum content")
        # Should detect the forbidden content
        assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)

    def test_validate_missing_sections(self):
        """Test detecting missing sections"""
        content = "Just some random content without proper structure."
        context = {"require_sections": True}
        result = self.validator.validate(content, context)
        assert any("missing_section" in issue.issue_id for issue in result.issues)

    def test_validate_complete_sections(self):
        """Test with complete sections"""
        content = """
        abstract: This is the abstract.
        introduction: This is the introduction.
        conclusion: This is the conclusion.
        """
        context = {"require_sections": True}
        result = self.validator.validate(content, context)
        # Should not have missing section warnings
        missing_section_issues = [i for i in result.issues if "missing_section" in i.issue_id]
        assert len(missing_section_issues) == 0

    def test_validate_markdown_format(self):
        """Test Markdown format validation"""
        content = """
        # Title
        ## Section 1
        ### Subsection 1.1
        content here
        """
        context = {"check_markdown": True}
        result = self.validator.validate(content, context)
        # Should be valid
        assert result.is_valid is True

    def test_validate_citations(self):
        """Test citation validation"""
        content = "This paper cites [1] and [2,3] for evidence."
        context = {"check_citations": True}
        result = self.validator.validate(content, context)
        # Should not have no_citations issue
        assert not any("no_citations" in issue.issue_id for issue in result.issues)


class TestQualityVerifier:
    """QualityVerifier Tests"""

    def setup_method(self):
        self.verifier = QualityVerifier()

    def test_verify_complete_paper(self):
        """Test verifying a complete paper"""
        content = """
        abstract: This paper presents research on machine learning.
        introduction: We introduce the problem of classification.
        method: We propose a novel approach using deep neural networks.
        result: Our method achieves state-of-the-art results.
        conclusion: In conclusion, we have demonstrated the effectiveness.
        """
        scores = self.verifier.verify(content)
        assert "accuracy" in scores
        assert "completeness" in scores
        assert "coherence" in scores
        assert "total" in scores

    def test_verify_partial_paper(self):
        """Test verifying a partial paper"""
        content = "Just a small bit of content."
        scores = self.verifier.verify(content)
        assert scores["completeness"] < 1.0

    def test_verify_with_error_markers(self):
        """Test accuracy check with error markers"""
        content = "The answer might be 42, but this is uncertain."
        scores = self.verifier.verify(content)
        # Should detect uncertainty
        assert scores["accuracy"] < 1.0


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_validate_output_function(self):
        """Test validate_output convenience function"""
        result = validate_output("Valid content here")
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    def test_verify_quality_function(self):
        """Test verify_quality convenience function"""
        scores = verify_quality("Content to verify")
        assert "accuracy" in scores
        assert "total" in scores


if __name__ == "__main__":
    pytest.main([__file__, "-v"])