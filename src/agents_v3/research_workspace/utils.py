"""共享工具函数：文本归一化、哈希、脱敏"""

from __future__ import annotations

import hashlib
import re


# ── 文本归一化 ──────────────────────────────────────

def normalize_label(text: str) -> str:
    """文本归一化：NFKC、小写、CJK标点、去标点、压缩空格、去复数、同义词"""
    import unicodedata
    # NFKC 归一化（全角→半角，兼容分解）
    t = unicodedata.normalize("NFKC", text.strip().lower())
    # CJK 标点替换
    t = re.sub(r"[，。；：！？、（）【】「」『』]", " ", t)
    # 全角空格 + 下划线/连字符
    t = re.sub(r"[　]+", " ", t)
    t = re.sub(r"[_\-]+", " ", t)
    # 压缩空格
    t = re.sub(r"\s+", " ", t).strip()
    # 去尾部标点
    t = t.rstrip(".,;:;")
    # 简单去复数
    if t.endswith("s") and not t.endswith("ss") and len(t) > 3:
        t = t[:-1]
    # 同义词解析（延迟导入避免循环依赖）
    from src.agents_v3.research_workspace.services.graph_utils import resolve_alias
    t = resolve_alias(t)
    return t


def stable_hash(text: str) -> str:
    """生成稳定的短哈希（10 字符）"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:10]


# ── 脱敏与哈希 ──────────────────────────────────────

_SENSITIVE_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"(api_key|apikey|authorization|cookie)\s*[:=]\s*\S+", re.IGNORECASE), r"\1=[REDACTED]"),
    (re.compile(r"[A-Z]:\\Users\\[^\s]+"), "[REDACTED_PATH]"),
    (re.compile(r"/home/[^\s]+"), "[REDACTED_PATH]"),
]


def redact_text(text: str | None, max_len: int = 200) -> str | None:
    """脱敏文本：移除敏感信息后截断"""
    if not text:
        return text
    result = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    if len(result) > max_len:
        result = result[:max_len] + f"...[{len(text)}chars]"
    return result


def hash_text(text: str | None) -> str | None:
    """生成文本哈希（用于日志关联，不泄露原文）"""
    if not text:
        return text
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
