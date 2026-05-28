"""JSON 提取与修复"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm_errors import JsonExtractionError


def extract_json(text: str) -> dict[str, Any] | list[Any]:
    """从 LLM 响应中提取 JSON 对象或数组"""
    if not text or not text.strip():
        raise JsonExtractionError("Empty response")

    # 1. 尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. 从 markdown 代码块提取
    for pattern in (r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue

    # 3. 尝试找到第一个 { 或 [ 开始的 JSON
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        # 从后往前找匹配的结束符
        end = text.rfind(end_char)
        if end <= start:
            continue
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # 4. 修复常见 JSON 问题后重试
    fixed = _try_fix_json(text)
    if fixed is not None:
        return fixed

    raise JsonExtractionError(f"Could not extract JSON from response (length={len(text)})")


def _try_fix_json(text: str) -> dict[str, Any] | list[Any] | None:
    """尝试修复常见 JSON 格式问题"""
    # 提取可能的 JSON 区域
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        end = text.rfind(end_char)
        if end <= start:
            continue
        candidate = text[start:end + 1]

        # 修复尾部逗号
        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
        # 修复单引号
        fixed = fixed.replace("'", '"')
        # 修复未转义的换行
        fixed = re.sub(r"(?<!\\)\n", "\\n", fixed)

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            continue

    return None


def repair_json_with_llm(
    raw_response: str,
    validation_errors: list[str],
    llm_invoke: callable,
) -> dict[str, Any] | None:
    """使用 LLM 修复 JSON（受约束：不新增事实）"""
    repair_prompt = f"""以下文本需要修复为合法 JSON。请只修复格式问题，不要新增或修改数据内容。

原始文本:
{raw_response[:2000]}

校验错误:
{chr(10).join(validation_errors[:5])}

请输出修复后的 JSON，不要包含解释。"""

    try:
        result = llm_invoke("你是 JSON 修复助手。只输出合法 JSON。", repair_prompt)
        return extract_json(result)
    except Exception as e:
        logger.warning(f"JSON repair via LLM failed: {e}")
        return None
