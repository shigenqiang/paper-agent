"""
Rewrite Validator - 重写验证器

验证查询改写的质量和正确性。
"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..workflow.routing.intent_classifier import IntentType


class RewriteType(str, Enum):
    """改写类型"""
    EXPANSION = "expansion"           # 扩展
    RESTRICTION = "restriction"       # 限制
    REFORMULATION = "reformulation"   # 重构
    DECOMPOSITION = "decomposition"   # 分解


@dataclass
class RewriteResult:
    """改写结果"""
    original_query: str
    rewritten_query: str
    rewrite_type: RewriteType
    confidence: float = 1.0
    valid: bool = True
    error_message: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "rewritten_query": self.rewritten_query,
            "rewrite_type": self.rewrite_type.value if isinstance(self.rewrite_type, Enum) else self.rewrite_type,
            "confidence": self.confidence,
            "valid": self.valid,
            "error_message": self.error_message,
            "suggestions": self.suggestions,
            "metadata": self.metadata
        }


class RewriteValidator:
    """
    查询改写验证器

    功能:
    - 验证改写后的查询语法
    - 检查语义一致性
    - 评估改写质量

    使用示例:
        validator = RewriteValidator()

        result = validator.validate(
            original="machine learning",
            rewritten="machine learning neural network deep learning",
            rewrite_type=RewriteType.EXPANSION
        )

        if not result.valid:
            print(result.error_message)
    """

    # 最大查询长度
    MAX_QUERY_LENGTH = 500

    # 最小查询长度
    MIN_QUERY_LENGTH = 2

    # 最大术语数量
    MAX_TERMS = 20

    def __init__(self, strict_mode: bool = False):
        """
        初始化验证器

        Args:
            strict_mode: 严格模式（更严格的验证）
        """
        self.strict_mode = strict_mode

    def validate(
        self,
        original_query: str,
        rewritten_query: str,
        rewrite_type: RewriteType
    ) -> RewriteResult:
        """
        验证改写结果

        Args:
            original_query: 原始查询
            rewritten_query: 改写后查询
            rewrite_type: 改写类型

        Returns:
            RewriteResult: 验证结果
        """
        # 基础验证
        if not rewritten_query or not rewritten_query.strip():
            return RewriteResult(
                original_query=original_query,
                rewritten_query=rewritten_query,
                rewrite_type=rewrite_type,
                confidence=0.0,
                valid=False,
                error_message="Rewritten query is empty"
            )

        # 语法验证
        syntax_valid, syntax_error = self._validate_syntax(rewritten_query)
        if not syntax_valid:
            return RewriteResult(
                original_query=original_query,
                rewritten_query=rewritten_query,
                rewrite_type=rewrite_type,
                confidence=0.0,
                valid=False,
                error_message=syntax_error
            )

        # 长度验证
        length_valid, length_error = self._validate_length(rewritten_query)
        if not length_valid:
            return RewriteResult(
                original_query=original_query,
                rewritten_query=rewritten_query,
                rewrite_type=rewrite_type,
                confidence=0.5,
                valid=False,
                error_message=length_error
            )

        # 语义一致性检查
        semantic_score = self._check_semantic_similarity(original_query, rewritten_query)

        # 类型特定验证
        type_valid, type_suggestions = self._validate_by_type(
            original_query, rewritten_query, rewrite_type
        )

        confidence = semantic_score if type_valid else semantic_score * 0.8

        return RewriteResult(
            original_query=original_query,
            rewritten_query=rewritten_query,
            rewrite_type=rewrite_type,
            confidence=confidence,
            valid=type_valid and semantic_score > 0.3,
            suggestions=type_suggestions
        )

    def _validate_syntax(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证语法"""
        # 检查括号匹配
        open_parens = query.count('(')
        close_parens = query.count(')')
        if open_parens != close_parens:
            return False, "Unbalanced parentheses"

        # 检查引号匹配
        open_quotes = query.count('"')
        if open_quotes % 2 != 0:
            return False, "Unbalanced quotes"

        return True, None

    def _validate_length(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证长度"""
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {self.MAX_QUERY_LENGTH})"

        if len(query) < self.MIN_QUERY_LENGTH:
            return False, f"Query too short (min {self.MIN_QUERY_LENGTH})"

        return True, None

    def _check_semantic_similarity(self, original: str, rewritten: str) -> float:
        """检查语义相似度"""
        orig_terms = set(original.lower().split())
        new_terms = set(rewritten.lower().split())

        # 计算重叠率
        if not orig_terms or not new_terms:
            return 0.5

        overlap = len(orig_terms & new_terms)
        total = len(orig_terms | new_terms)

        return overlap / total if total > 0 else 0.5

    def _validate_by_type(
        self,
        original: str,
        rewritten: str,
        rewrite_type: RewriteType
    ) -> Tuple[bool, List[str]]:
        """根据类型验证"""
        suggestions = []
        valid = True

        if rewrite_type == RewriteType.EXPANSION:
            # 扩展应该包含更多术语
            if len(rewritten.split()) <= len(original.split()):
                valid = False
                suggestions.append("Expansion should add more terms")

        elif rewrite_type == RewriteType.RESTRICTION:
            # 限制应该减少术语
            if len(rewritten.split()) >= len(original.split()):
                valid = False
                suggestions.append("Restriction should reduce terms")

        elif rewrite_type == RewriteType.DECOMPOSITION:
            # 分解应该产生多个独立查询
            if ';' not in rewritten and ',' not in rewritten:
                suggestions.append("Consider using semicolons to separate sub-queries")

        return valid, suggestions

    def batch_validate(
        self,
        queries: List[Tuple[str, str, RewriteType]]
    ) -> List[RewriteResult]:
        """批量验证"""
        return [self.validate(orig, rewritten, rtype) for orig, rewritten, rtype in queries]


def validate_rewrite(
    original: str,
    rewritten: str,
    rewrite_type: RewriteType
) -> RewriteResult:
    """便捷函数：验证改写"""
    validator = RewriteValidator()
    return validator.validate(original, rewritten, rewrite_type)