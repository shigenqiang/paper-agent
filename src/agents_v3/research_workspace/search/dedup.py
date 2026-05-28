"""论文去重逻辑 - 增强版"""

from __future__ import annotations

import re
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel, Field


# ── 归一化函数 ──────────────────────────────────────────


def normalize_doi(doi: str) -> str:
    """DOI 归一化：去前缀、转小写、去空白"""
    d = doi.strip().lower()
    d = re.sub(r"^(https?://doi\.org/|doi:)", "", d)
    return d.strip()


def normalize_arxiv_id(arxiv_id: str) -> str:
    """arXiv ID 归一化：去版本号 v1/v2，保留 base_id"""
    a = arxiv_id.strip()
    a = re.sub(r"^https?://arxiv\.org/abs/", "", a)
    a = re.sub(r"v\d+$", "", a)
    return a.strip()


def normalize_title(title: str) -> str:
    """标题归一化：小写、去标点、去多余空格"""
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def normalize_author(author: str) -> str:
    """作者归一化：保留姓氏和首字母"""
    a = author.strip()
    # "Smith, John" -> "smith j" (last, first format)
    if "," in a:
        parts = [p.strip() for p in a.split(",", 1)]
        if len(parts) == 2:
            last = parts[0].lower()
            initials = "".join(p[0].lower() for p in parts[1].split() if p)
            return f"{last} {initials}".strip()
    # "John Smith" -> "smith j"
    parts = a.split()
    if not parts:
        return ""
    last = parts[-1].lower()
    initials = "".join(p[0].lower() for p in parts[:-1] if p)
    return f"{last} {initials}".strip()


def first_author_key(authors: list[str]) -> str:
    """第一作者简化键"""
    if not authors:
        return ""
    return normalize_author(authors[0])


# ── 去重 Key 生成 ──────────────────────────────────────


def make_dedup_key(paper: dict[str, Any]) -> str | None:
    """生成去重 key。优先级：DOI > arXiv ID > 标准化标题+年份"""
    doi = normalize_doi(paper.get("doi", ""))
    if doi:
        return f"doi:{doi}"

    arxiv_id = normalize_arxiv_id(paper.get("arxiv_id", ""))
    if arxiv_id:
        return f"arxiv:{arxiv_id}"

    title = normalize_title(paper.get("title", ""))
    year = paper.get("year")
    fa = first_author_key(paper.get("authors", []))
    if title and year and fa:
        return f"tya:{title}|{year}|{fa}"
    if title and year:
        return f"title_year:{title}|{year}"
    if title:
        return f"title:{title}"

    return None


def is_duplicate(
    paper: dict[str, Any],
    existing_keys: set[str],
) -> bool:
    """检查论文是否与已有记录重复"""
    key = make_dedup_key(paper)
    if key is None:
        return False
    return key in existing_keys


def build_existing_keys(papers: list[dict[str, Any]]) -> set[str]:
    """从已有论文列表构建去重 key 集合"""
    keys: set[str] = set()
    for p in papers:
        key = make_dedup_key(p)
        if key:
            keys.add(key)
    return keys


# ── 去重决策模型 ──────────────────────────────────────


class DedupDecision(BaseModel):
    action: Literal["new", "duplicate", "merge", "possible_duplicate"]
    result_id: str = ""
    matched_paper_id: str = ""
    matched_result_id: str = ""
    reason: str = ""
    confidence: float = 0.0
    merge_fields: dict[str, Any] = Field(default_factory=dict)


# ── 去重服务 ──────────────────────────────────────────


class DedupService:
    """搜索结果去重服务"""

    def check_against_existing(
        self,
        result: dict[str, Any],
        existing_papers: list[dict[str, Any]],
    ) -> DedupDecision:
        """检查搜索结果与已有论文是否重复"""
        existing_keys = build_existing_keys(existing_papers)
        key = make_dedup_key(result)

        if key and key in existing_keys:
            # Find the matching paper
            for p in existing_papers:
                pkey = make_dedup_key(p)
                if pkey == key:
                    return DedupDecision(
                        action="duplicate",
                        result_id=result.get("result_id", ""),
                        matched_paper_id=p.get("paper_id", ""),
                        reason=f"Dedup key match: {key}",
                        confidence=1.0 if key.startswith("doi:") or key.startswith("arxiv:") else 0.9,
                    )

        return DedupDecision(
            action="new",
            result_id=result.get("result_id", ""),
        )

    def check_result_pair(
        self,
        a: dict[str, Any],
        b: dict[str, Any],
    ) -> DedupDecision:
        """检查两个搜索结果是否重复"""
        # Exact key match
        key_a = make_dedup_key(a)
        key_b = make_dedup_key(b)
        if key_a and key_b and key_a == key_b:
            return DedupDecision(
                action="merge",
                result_id=a.get("result_id", ""),
                matched_result_id=b.get("result_id", ""),
                reason=f"Exact key match: {key_a}",
                confidence=1.0 if key_a.startswith("doi:") else 0.95,
            )

        # Title similarity check
        title_a = normalize_title(a.get("title", ""))
        title_b = normalize_title(b.get("title", ""))
        if title_a and title_b:
            sim = _jaccard_similarity(title_a, title_b)
            year_a = a.get("year")
            year_b = b.get("year")

            if sim >= 0.95 and (not year_a or not year_b or abs(year_a - year_b) <= 1):
                fa_a = first_author_key(a.get("authors", []))
                fa_b = first_author_key(b.get("authors", []))
                if fa_a and fa_b and fa_a == fa_b:
                    return DedupDecision(
                        action="merge",
                        result_id=a.get("result_id", ""),
                        matched_result_id=b.get("result_id", ""),
                        reason=f"Title similarity {sim:.2f} + same first author",
                        confidence=0.9,
                    )
                return DedupDecision(
                    action="possible_duplicate",
                    result_id=a.get("result_id", ""),
                    matched_result_id=b.get("result_id", ""),
                    reason=f"Title similarity {sim:.2f}",
                    confidence=sim,
                )

        return DedupDecision(
            action="new",
            result_id=a.get("result_id", ""),
        )


def _jaccard_similarity(a: str, b: str) -> float:
    """Jaccard 相似度（基于单词集合）"""
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)
