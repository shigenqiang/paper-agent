"""
Pydantic 校验工具 - 统一处理 LLM 返回的 JSON

提供健壮的 JSON 解析和 Pydantic 模型校验功能。

设计原则：多种策略并行尝试，智能降级
"""

from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field, ValidationError
import json
import re

from ..logging_config import get_logging_logger

logger = get_logging_logger(__name__)

T = TypeVar('T', bound=BaseModel)


def _clean_json_markdown(text: str) -> str:
    """清理JSON markdown格式，处理各种截断和格式问题

    策略（按优先级）：
    1. 直接解析（如果JSON完整）
    2. 移除尾随逗号后重试
    3. 逐步截断寻找有效JSON
    4. 正则提取完整对象
    5. 智能截断处理字符串内截断
    """
    if not text:
        return ""

    # 移除各种思考块格式
    text = _remove_thinking_blocks(text)

    # 移除 markdown 代码块
    text = re.sub(r'^```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^```\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text, flags=re.IGNORECASE)
    text = text.strip()

    if not text:
        return ""

    # 找到 JSON 开始位置
    if '{' in text:
        text = text[text.index('{'):]

    # 策略1：直接解析
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 策略2：移除尾随逗号
    cleaned = re.sub(r',\s*([}\]])$', r'\1', text)
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass

    # 策略3：移除尾随逗号（包括多个）
    cleaned = re.sub(r',\s*$', '', text)
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass

    # 策略4：尝试逐步截断从后向前
    truncated = _try_truncate_from_end(text)
    if truncated:
        return truncated

    # 策略5：处理字符串内截断的情况（最复杂）
    truncated = _handle_string_truncation(text)
    if truncated:
        return truncated

    # 策略6：正则提取任何完整对象
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            json.loads(match.group())
            return match.group()
        except json.JSONDecodeError:
            pass

    # 最终尝试：返回原文本让调用方处理
    return text


def _remove_thinking_blocks(text: str) -> str:
    """移除各种格式的思考块"""
    patterns = [
        r'<start_thinking>.*?<end_thinking>',
        r'<think>.*?\加成',
        r'<think>.*?',
    ]
    for p in patterns:
        text = re.sub(p, '', text, flags=re.DOTALL)
    return text


def _try_truncate_from_end(text: str) -> str:
    """从后向前逐步截断，找到最长的有效JSON"""
    # 从后向前找到所有可能的结束位置
    candidates = []
    for i, c in enumerate(text):
        if c in '}],':
            candidates.append(i)

    # 按位置从后向前排序，优先尝试更长的截断
    candidates.sort(reverse=True)

    for cutoff in candidates:
        # 跳过结尾的逗号
        if text[cutoff] == ',':
            truncated = text[:cutoff]
        else:
            truncated = text[:cutoff + 1]

        if not truncated.strip():
            continue

        try:
            json.loads(truncated)
            return truncated
        except json.JSONDecodeError:
            continue

    return ""


def _handle_string_truncation(text: str) -> str:
    """
    处理JSON在字符串中间被截断的情况

    例如：{"key": "value that gets cut off here",
    会在字符串中间截断。

    方法：找到最后一个完整的条目，截断到该位置
    """
    # 找到JSON开始
    start = text.index('{')

    # 分析文本，追踪字符串状态
    depth = 0
    in_string = False
    escape_next = False

    last_valid_pos = start  # 至少从开始
    valid_closes = []  # 记录所有有效的 } 位置

    for i in range(start, len(text)):
        c = text[i]

        if escape_next:
            escape_next = False
            continue

        if c == '\\':
            escape_next = True
            continue

        if c == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                # 这是一个有效的结束位置
                last_valid_pos = i + 1
                valid_closes.append(i + 1)

    # 尝试从最后一个有效的 } 位置截断
    for close_pos in reversed(valid_closes):
        truncated = text[:close_pos]
        try:
            json.loads(truncated)
            return truncated
        except json.JSONDecodeError:
            continue

    # 如果还是不行，尝试移除最后一个不完整的字符串
    if last_valid_pos > start:
        truncated = text[:last_valid_pos]
        try:
            json.loads(truncated)
            return truncated
        except json.JSONDecodeError:
            pass

    return ""


def parse_json(text: str) -> Optional[Dict[str, Any]]:
    """解析 JSON 文本，返回字典或 None"""
    try:
        cleaned = _clean_json_markdown(text)
        if not cleaned:
            return None
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON parse failed: {e}, raw_length={len(text) if text else 0}")
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
        if not cleaned:
            raise ValueError("Empty text after cleaning")
        data = json.loads(cleaned)
        return model_class.model_validate(data)
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        logger.warning(f"Pydantic parse failed: {e}")

        if strict:
            raise

        if default_value is not None:
            return default_value

        try:
            return model_class()
        except Exception:
            return model_class.model_validate({})


def parse_list_with_pydantic(
    text: str,
    item_class: Type[BaseModel],
    list_key: Optional[str] = None,
    default_count: int = 0
) -> List[BaseModel]:
    """解析 JSON 数组文本，返回 Pydantic 模型列表"""
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
        except ValidationError:
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