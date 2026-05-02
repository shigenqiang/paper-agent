"""
Pydantic 校验工具 - 统一处理 LLM 返回的 JSON

提供健壮的 JSON 解析和 Pydantic 模型校验功能。
"""

from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field, ValidationError
import json
import re

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)

T = TypeVar('T', bound=BaseModel)


def _clean_json_markdown(text: str) -> str:
    """清理JSON markdown格式"""
    if not text:
        return ""

    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^```\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = text.strip()

    if not text:
        return ""

    if not text.startswith('{'):
        match = re.search(r'\{', text)
        if match:
            text = text[match.start():]

    if text.startswith('{'):
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            start = text.index('{')
            depth = 0
            end_pos = -1
            for i, c in enumerate(text[start:], start):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            if end_pos > 0:
                return text[start:end_pos]

    return text


def parse_json(text: str) -> Optional[Dict[str, Any]]:
    """解析 JSON 文本，返回字典或 None"""
    try:
        cleaned = _clean_json_markdown(text)
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON parse failed in parse_json: {e}, raw_input={text[:500] if text else 'empty'}")
        # 尝试正则提取
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError as e2:
                logger.warning(f"Regex extraction also failed in parse_json: {e2}")
                pass
        return None


def parse_with_pydantic(
    text: str,
    model_class: Type[T],
    default_value: Optional[T] = None,
    strict: bool = False
) -> T:
    """使用 Pydantic 模型解析 JSON 文本

    Args:
        text: LLM 返回的文本
        model_class: Pydantic 模型类
        default_value: 解析失败时的默认值（如果为 None，返回模型实例的默认值）
        strict: 是否严格模式（严格模式下验证失败会抛出异常）

    Returns:
        解析后的 Pydantic 模型实例
    """
    try:
        cleaned = _clean_json_markdown(text)
        data = json.loads(cleaned)
        return model_class.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Pydantic parse failed: {e}, raw_input={text[:500] if text else 'empty'}, trying regex extraction")

        # 尝试正则提取
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return model_class.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e2:
                logger.warning(f"Regex extraction also failed: {e2}, raw_input={text[:500] if text else 'empty'}")

        if strict:
            raise

        # 返回默认值
        if default_value is not None:
            return default_value

        # 如果没有提供默认值，尝试用模型类的默认值
        try:
            return model_class()
        except Exception:
            # 最后兜底：返回从字典构造的实例
            return model_class.model_validate({})


def parse_list_with_pydantic(
    text: str,
    item_class: Type[BaseModel],
    list_key: Optional[str] = None,
    default_count: int = 0
) -> List[BaseModel]:
    """解析 JSON 数组文本，返回 Pydantic 模型列表

    Args:
        text: LLM 返回的文本
        item_class: 数组元素的 Pydantic 模型类
        list_key: 如果 JSON 是对象，指定包含数组的键名
        default_count: 如果解析失败，返回多少个默认实例

    Returns:
        Pydantic 模型实例列表
    """
    data = parse_json(text)
    if data is None:
        return [item_class() for _ in range(default_count)]

    items = []
    if list_key and isinstance(data, dict):
        raw_items = data.get(list_key, [])
    elif isinstance(data, list):
        raw_items = data
    else:
        raw_items = []

    for item_data in raw_items:
        try:
            if isinstance(item_data, dict):
                items.append(item_class.model_validate(item_data))
            else:
                items.append(item_class())
        except ValidationError as e:
            logger.debug(f"Item validation failed: {e}")
            items.append(item_class())

    return items if items else [item_class() for _ in range(default_count)]


# ==================== 通用模型定义 ====================

class ChapterOutline(BaseModel):
    """章节大纲"""
    name: str = Field(default="", description="章节名称")
    purpose: str = Field(default="", description="章节目的")
    content_guidance: str = Field(default="", description="内容指导")
    main_points: List[str] = Field(default_factory=list, description="主要论点")
    citations_needed: List[str] = Field(default_factory=list, description="需要引用的内容")
    order: int = Field(default=0, ge=0, description="章节顺序")


class PaperStructure(BaseModel):
    """论文结构"""
    title: str = Field(default="", description="论文标题")
    paper_type: str = Field(default="empirical", description="论文类型")
    chapters: List[ChapterOutline] = Field(default_factory=list)
    total_chapters: int = Field(default=5, ge=1, le=20)
    word_count_estimate: int = Field(default=8000, ge=1000)


class LiteratureAnalysis(BaseModel):
    """文献分析"""
    paper_id: str = Field(default="", description="论文ID")
    title: str = Field(default="", description="论文标题")
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = Field(default=None, description="发表年份")
    venue: str = Field(default="", description="发表场所")
    summary: str = Field(default="", description="摘要/总结")
    methodology: str = Field(default="", description="研究方法")
    findings: List[str] = Field(default_factory=list, description="主要发现")
    limitations: List[str] = Field(default_factory=list, description="局限性")


class ReviewResult(BaseModel):
    """审稿结果"""
    aspect: str = Field(default="", description="评价方面")
    strength: str = Field(default="", description="优点")
    weakness: str = Field(default="", description="缺点/问题")
    severity: str = Field(default="medium", description="严重程度: minor/major/critical")
    suggestion: str = Field(default="", description="修改建议")


class ReviewResponse(BaseModel):
    """完整审稿响应"""
    overall: str = Field(default="", description="总体评价")
    summary: str = Field(default="", description="审稿摘要")
    reviews: List[ReviewResult] = Field(default_factory=list)
    recommendation: str = Field(default="revision", description="建议: accept/revision/reject")


class QualityScore(BaseModel):
    """质量评分"""
    score: float = Field(default=0.7, ge=0, le=10, description="评分 0-10")
    confidence: float = Field(default=0.8, ge=0, le=1, description="置信度")
    reasoning: str = Field(default="", description="评分理由")


class ThesisProposal(BaseModel):
    """论文提案"""
    title: str = Field(default="", description="论文标题")
    research_question: str = Field(default="", description="研究问题")
    hypothesis: str = Field(default="", description="假设")
    significance: str = Field(default="", description="研究意义")
    methodology: str = Field(default="", description="研究方法")
    expected_outcome: str = Field(default="", description="预期成果")
