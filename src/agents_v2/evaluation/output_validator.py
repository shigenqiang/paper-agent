"""
输出验证器 - Output Validator

功能:
1. 结构完整性验证
2. 内容质量验证
3. 格式规范验证
4. Schema验证

设计原则:
- 多维度验证
- 可配置的验证规则
- 详细的验证报告
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """验证严重级别"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """验证问题"""
    issue_id: str
    severity: ValidationSeverity
    category: str
    message: str
    location: str = ""  # 如 "line 42", "section 3.2"
    suggestion: str = ""


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    score: float = 1.0  # 0.0 - 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue):
        """添加问题"""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.is_valid = False

    def compute_score(self):
        """计算验证分数"""
        if not self.issues:
            self.score = 1.0
            return

        error_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

        # 分数计算：每个error扣0.2，每个warning扣0.05
        self.score = max(0.0, 1.0 - (error_count * 0.2) - (warning_count * 0.05))


class SchemaValidator:
    """Schema验证器"""

    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        self.schema = schema

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """验证数据是否符合Schema"""
        result = ValidationResult(is_valid=True)

        if not self.schema:
            return result

        # 检查必需字段
        required_fields = self.schema.get("required", [])
        for field in required_fields:
            if field not in data:
                result.add_issue(ValidationIssue(
                    issue_id=f"missing_field_{field}",
                    severity=ValidationSeverity.ERROR,
                    category="schema",
                    message=f"必需字段缺失: {field}",
                    location="root"
                ))

        # 检查字段类型
        properties = self.schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in data:
                expected_type = field_schema.get("type")
                actual_type = type(data[field]).__name__

                if expected_type and not self._check_type(data[field], expected_type):
                    result.add_issue(ValidationIssue(
                        issue_id=f"type_mismatch_{field}",
                        severity=ValidationSeverity.ERROR,
                        category="schema",
                        message=f"字段类型不匹配: {field} (期望: {expected_type}, 实际: {actual_type})",
                        location=f"field: {field}"
                    ))

        result.compute_score()
        return result

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查类型匹配"""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True

        return isinstance(value, expected)


class OutputValidator:
    """输出验证器"""

    def __init__(self):
        self.schema_validator = SchemaValidator()
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认验证规则"""
        self.min_length = 100  # 最小内容长度
        self.max_length = 100000  # 最大内容长度
        self.required_sections = ["abstract", "introduction", "conclusion"]
        self.forbidden_patterns = [
            r"lorem ipsum",
            r"fake content",
            r"test test test"
        ]

    def validate(self, output: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """验证输出

        Args:
            output: 待验证的输出内容
            context: 可选的上下文信息

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True)
        context = context or {}

        # 1. 基本验证
        self._validate_basic(output, result)

        # 2. 内容质量验证
        self._validate_quality(output, result)

        # 3. 格式规范验证
        self._validate_format(output, result, context)

        # 4. Schema验证（如果提供了schema）
        if "schema" in context:
            self.schema_validator.schema = context["schema"]
            schema_result = self.schema_validator.validate(context.get("data", {}))
            result.issues.extend(schema_result.issues)

        result.compute_score()
        return result

    def _validate_basic(self, output: str, result: ValidationResult):
        """验证基本属性"""
        # 空内容检查
        if not output or not output.strip():
            result.add_issue(ValidationIssue(
                issue_id="empty_content",
                severity=ValidationSeverity.ERROR,
                category="basic",
                message="输出内容为空",
                suggestion="请提供有效的输出内容"
            ))
            return

        # 长度验证
        length = len(output)
        if length < self.min_length:
            result.add_issue(ValidationIssue(
                issue_id="too_short",
                severity=ValidationSeverity.WARNING,
                category="basic",
                message=f"输出内容过短 ({length} < {self.min_length}字符)",
                suggestion="考虑添加更多详细说明"
            ))

        if length > self.max_length:
            result.add_issue(ValidationIssue(
                issue_id="too_long",
                severity=ValidationSeverity.WARNING,
                category="basic",
                message=f"输出内容过长 ({length} > {self.max_length}字符)",
                suggestion="考虑精简内容或分段输出"
            ))

    def _validate_quality(self, output: str, result: ValidationResult):
        """验证内容质量"""
        output_lower = output.lower()

        # 禁止内容检查
        for pattern in self.forbidden_patterns:
            if re.search(pattern, output_lower):
                result.add_issue(ValidationIssue(
                    issue_id="forbidden_content",
                    severity=ValidationSeverity.ERROR,
                    category="quality",
                    message=f"检测到禁止内容: {pattern}",
                    suggestion="请提供真实、有效的内容"
                ))

        # 重复内容检查
        lines = [l.strip() for l in output.split('\n') if l.strip()]
        if len(lines) > 5:
            unique_lines = len(set(lines))
            repeat_ratio = 1 - (unique_lines / len(lines))
            if repeat_ratio > 0.5:
                result.add_issue(ValidationIssue(
                    issue_id="high_repetition",
                    severity=ValidationSeverity.WARNING,
                    category="quality",
                    message=f"内容重复率过高 ({repeat_ratio:.1%})",
                    suggestion="考虑去除重复内容或重新组织结构"
                ))

        # 句子完整性检查
        sentences = re.split(r'[.!?。！？]', output)
        incomplete_count = sum(1 for s in sentences if s.strip() and len(s.strip()) < 10)
        if incomplete_count > len(sentences) * 0.3:
            result.add_issue(ValidationIssue(
                issue_id="incomplete_sentences",
                severity=ValidationSeverity.WARNING,
                category="quality",
                message="存在较多不完整的句子",
                suggestion="请确保句子完整，没有被意外截断"
            ))

    def _validate_format(self, output: str, result: ValidationResult, context: Dict[str, Any]):
        """验证格式规范"""
        # 检查必需章节
        if context.get("require_sections", True):
            output_lower = output.lower()
            for section in self.required_sections:
                if section not in output_lower:
                    result.add_issue(ValidationIssue(
                        issue_id=f"missing_section_{section}",
                        severity=ValidationSeverity.WARNING,
                        category="format",
                        message=f"缺少必需的章节: {section}",
                        suggestion=f"考虑添加 {section} 章节"
                    ))

        # Markdown格式检查
        if context.get("check_markdown", False):
            self._validate_markdown_format(output, result)

        # 引用格式检查
        if context.get("check_citations", False):
            self._validate_citations(output, result)

    def _validate_markdown_format(self, output: str, result: ValidationResult):
        """验证Markdown格式"""
        lines = output.split('\n')

        # 检查标题层级
        heading_levels = []
        for i, line in enumerate(lines):
            if re.match(r'^#+ ', line):
                level = len(re.match(r'^(#+)', line).group(1))
                heading_levels.append((i + 1, level))

        # 检查标题层级是否连续
        if len(heading_levels) > 1:
            for i in range(1, len(heading_levels)):
                prev_level = heading_levels[i - 1][1]
                curr_level = heading_levels[i][1]
                if curr_level > prev_level + 1:
                    result.add_issue(ValidationIssue(
                        issue_id="heading_level_skip",
                        severity=ValidationSeverity.WARNING,
                        category="markdown",
                        message=f"标题层级跳跃: 第{heading_levels[i][0]}行",
                        suggestion="建议使用连续的标题层级（如：# -> ## -> ###）"
                    ))

        # 检查列表格式一致性
        ul_count = len(re.findall(r'^\s*-\s+', output, re.MULTILINE))
        ol_count = len(re.findall(r'^\s*\d+\.\s+', output, re.MULTILINE))
        if ul_count > 0 and ol_count > 0:
            # 如果混用，需要确保有明确区分
            pass

    def _validate_citations(self, output: str, result: ValidationResult):
        """验证引用格式"""
        # 检查引用标记格式
        citation_patterns = [
            r'\[\d+\]',           # [1], [2,3]
            r'\[\w+ et al\., \d+\]',  # [Smith et al., 2020]
        ]

        has_citations = False
        for pattern in citation_patterns:
            if re.search(pattern, output):
                has_citations = True
                break

        if not has_citations:
            result.add_issue(ValidationIssue(
                issue_id="no_citations",
                severity=ValidationSeverity.INFO,
                category="citations",
                message="未检测到引用标记",
                suggestion="如果引用了外部资源，请添加适当的引用"
            ))


class QualityVerifier:
    """质量验证器"""

    def __init__(self):
        self.dimensions = {
            "accuracy": 0.3,      # 准确性权重
            "completeness": 0.2,  # 完整性权重
            "coherence": 0.2,     # 连贯性权重
            "relevance": 0.3      # 相关性权重
        }

    def verify(self, output: str, reference: Optional[str] = None) -> Dict[str, float]:
        """验证质量

        Args:
            output: 输出内容
            reference: 参考内容（可选）

        Returns:
            Dict[str, float]: 各维度分数
        """
        scores = {
            "accuracy": self._check_accuracy(output),
            "completeness": self._check_completeness(output),
            "coherence": self._check_coherence(output),
            "relevance": self._check_relevance(output, reference) if reference else 0.8
        }

        # 计算加权总分
        total = sum(scores[dim] * weight for dim, weight in self.dimensions.items())

        return {
            **scores,
            "total": total
        }

    def _check_accuracy(self, output: str) -> float:
        """检查准确性"""
        # 简单的准确性检查：检查是否有明显的错误标记
        error_markers = ["错误", "不对", "可能有误", "不确定"]
        for marker in error_markers:
            if marker in output:
                return 0.7

        return 0.9

    def _check_completeness(self, output: str) -> float:
        """检查完整性"""
        sections = ["abstract", "introduction", "method", "result", "conclusion"]
        present = sum(1 for s in sections if s.lower() in output.lower())
        return min(1.0, present / 3)  # 至少需要3个核心章节

    def _check_coherence(self, output: str) -> float:
        """检查连贯性"""
        sentences = re.split(r'[.!?。！？]', output)
        if len(sentences) < 3:
            return 0.8

        # 检查段落过渡
        transitions = ["此外", "然而", "因此", "但是", "首先", "其次", "最后", "furthermore", "however", "therefore"]
        transition_count = sum(1 for t in transitions if t in output)

        if transition_count > 0:
            return min(1.0, 0.6 + (transition_count * 0.05))

        return 0.6

    def _check_relevance(self, output: str, reference: Optional[str]) -> float:
        """检查相关性"""
        if not reference:
            return 0.8

        # 简单的相关性检查：共同词汇比例
        output_words = set(output.lower().split())
        ref_words = set(reference.lower().split())

        if not output_words or not ref_words:
            return 0.5

        overlap = len(output_words & ref_words)
        ratio = overlap / len(ref_words)

        return min(1.0, ratio)


# 便捷函数
def validate_output(output: str, **kwargs) -> ValidationResult:
    """验证输出的便捷函数"""
    validator = OutputValidator()
    return validator.validate(output, kwargs)


def verify_quality(output: str, reference: Optional[str] = None) -> Dict[str, float]:
    """验证质量的便捷函数"""
    verifier = QualityVerifier()
    return verifier.verify(output, reference)