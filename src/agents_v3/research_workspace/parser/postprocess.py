"""分块后处理：文本修复、清洗、去重、质量评分、冗余过滤"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.models import ChunkType


class TextPostProcessor:
    """文本后处理管线：修复 PDF 提取中的常见文本问题"""

    LIGATURE_MAP = {
        "ﬀ": "ff",
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬅ": "st",
        "ﬆ": "st",
    }

    PAGE_NUM_RE = re.compile(r"^\s*(?:\-?\s*\d+\s*\-?|Page\s+\d+|第\s*\d+\s*页)\s*$")
    CID_RE = re.compile(r"\(cid:\d+\)")

    def process(self, text: str) -> str:
        """完整后处理管线"""
        text = self.fix_cid_artifacts(text)
        text = self.fix_ligatures(text)
        text = self.fix_word_spacing(text)
        text = self.fix_hyphenation(text)
        text = self.fix_citation_markers(text)
        text = self.remove_page_numbers(text)
        return text

    def fix_cid_artifacts(self, text: str) -> str:
        """移除 pdfplumber 的 CID 伪影：(cid:48) (cid:62) 等"""
        return self.CID_RE.sub("", text)

    def fix_ligatures(self, text: str) -> str:
        """合字修复：ﬁ → fi"""
        for lig, replacement in self.LIGATURE_MAP.items():
            text = text.replace(lig, replacement)
        return text

    @staticmethod
    def fix_word_spacing(text: str) -> str:
        """修复 PDF 提取中丢失的单词间距"""
        text = re.sub(r"([a-z0-9)'’])([A-Z])", r"\1 \2", text)
        text = re.sub(r"([a-z])(\()", r"\1 \2", text)
        text = re.sub(r"(\))([a-zA-Z])", r"\1 \2", text)
        text = re.sub(r"([,;])([a-zA-Z])", r"\1 \2", text)
        return text

    @staticmethod
    def fix_hyphenation(text: str) -> str:
        """连字符断行修复：computa-\\ntion → computation"""
        return re.sub(r"(\w+)-[ \t]*\n[ \t]*(\w+)", r"\1\2", text)

    @staticmethod
    def fix_citation_markers(text: str) -> str:
        """引用标记重连：word [1] → word[1]"""
        return re.sub(r"(\w)\s+\[(\d+(?:,\s*\d+)*)\]", r"\1[\2]", text)

    def remove_page_numbers(self, text: str) -> str:
        """移除独立的页码行"""
        lines = text.split("\n")
        cleaned = [line for line in lines if not self.PAGE_NUM_RE.match(line.strip())]
        return "\n".join(cleaned)

    @staticmethod
    def remove_headers_footers(pages_text: list[tuple[int, str]]) -> list[tuple[int, str]]:
        """基于重复检测去除页眉页脚"""
        if len(pages_text) < 3:
            return pages_text

        line_page_count: Counter[str] = Counter()
        for _, text in pages_text:
            seen: set[str] = set()
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped and len(stripped) < 50 and stripped not in seen:
                    line_page_count[stripped] += 1
                    seen.add(stripped)

        threshold = len(pages_text) * 0.8
        headers_footers = {
            line
            for line, count in line_page_count.items()
            if count >= threshold and len(line) < 50
        }

        if not headers_footers:
            return pages_text

        result = []
        for page_num, text in pages_text:
            lines = text.split("\n")
            cleaned = [line for line in lines if line.strip() not in headers_footers]
            result.append((page_num, "\n".join(cleaned)))

        return result


# ── BM25 工具函数 ─────────────────────────────────────


def _tokenize(text: str) -> list[str]:
    """简单分词：按空白 + 标点拆分，转小写"""
    return re.findall(r"[a-zA-Z0-9一-鿿]+", text.lower())


def _bm25_pairwise_similarity(chunks: list[dict]) -> list[list[float]] | None:
    """计算 chunk 间的 BM25 两两相似度矩阵（归一化到 [0,1]）"""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.debug("rank_bm25 not installed, skipping BM25 similarity")
        return None

    texts = [c.get("text", "") for c in chunks]
    tokenized = [_tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized)

    n = len(chunks)
    sim_matrix = [[0.0] * n for _ in range(n)]

    scores_cache: list[list[float]] = []
    for i in range(n):
        scores = bm25.get_scores(tokenized[i])
        scores_cache.append(scores.tolist())

    for i in range(n):
        sim_matrix[i][i] = 1.0
        self_score_i = scores_cache[i][i] if scores_cache[i][i] > 0 else 1.0
        for j in range(i + 1, n):
            self_score_j = scores_cache[j][j] if scores_cache[j][j] > 0 else 1.0
            norm_ij = scores_cache[i][j] / self_score_i
            norm_ji = scores_cache[j][i] / self_score_j
            sim = (norm_ij + norm_ji) / 2.0
            sim_matrix[i][j] = sim
            sim_matrix[j][i] = sim

    return sim_matrix


# ── Chunk 分块后清洗 ──────────────────────────────────


class ChunkCleaner:
    """分块后清洗：过滤噪声行、合并碎片、去重、质量评分、冗余过滤"""

    _MATH_CHARS = set(
        "αβγδεζηθικλμνξπρστυφχψω"
        "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ"
        "∑∏∫∂∇∆∈∉⊂⊃∪∩∧∨¬±×÷≈≠≤≥∞∅⊤⊥⊢⊨"
        "₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹"
        "·⋯…‖|‖⟨⟩⟪⟫"
    )

    def __init__(self) -> None:
        self._deduplicator = ChunkDeduplicator()
        self._quality_scorer = ChunkQualityScorer()
        self._redundancy_filter = ChunkRedundancyFilter()

    def clean(self, chunks: list[dict]) -> list[dict]:
        """完整清洗管线"""
        chunks = self._filter_noise_lines(chunks)
        chunks = self._merge_fragments(chunks)
        chunks = self._deduplicator.deduplicate(chunks)
        chunks = self._filter_low_quality(chunks)
        chunks = self._redundancy_filter.filter(chunks)
        chunks = self._update_token_counts(chunks)
        return chunks

    def _filter_low_quality(self, chunks: list[dict], min_score: float = 0.3) -> list[dict]:
        """过滤低质量 chunk"""
        result = []
        for c in chunks:
            score_result = self._quality_scorer.score(c)
            c["quality_score"] = score_result["quality_score"]
            c["quality_details"] = score_result["details"]
            if c["quality_score"] >= min_score:
                result.append(c)
        return result

    def _filter_noise_lines(self, chunks: list[dict]) -> list[dict]:
        """过滤每个 chunk 中的噪声行"""
        for chunk in chunks:
            text = chunk.get("text", "")
            if not text:
                continue
            lines = text.split("\n")
            cleaned = self._filter_lines(lines)
            chunk["text"] = "\n".join(cleaned)
        return chunks

    def _filter_lines(self, lines: list[str]) -> list[str]:
        """过滤行列表，移除噪声行"""
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                result.append(line)
                i += 1
                continue

            if re.match(r"^(Figure|Table|Fig\.)\s+\d+", stripped, re.IGNORECASE):
                result.append(line)
                i += 1
                continue

            if self._is_formula_line(stripped):
                i += 1
                continue

            block_end = self._find_axis_label_block(lines, i)
            if block_end > i:
                i = block_end
                continue

            result.append(line)
            i += 1

        return result

    def _is_formula_line(self, line: str) -> bool:
        """判断是否为公式行"""
        if len(line) < 3:
            return False

        math_count = sum(1 for c in line if c in self._MATH_CHARS)
        normal_words = re.findall(r"[a-zA-Z]{4,}", line)
        normal_word_count = len(normal_words)
        alpha_count = sum(1 for c in line if c.isalpha())
        alpha_ratio = alpha_count / len(line) if line else 0

        if math_count >= 2 and normal_word_count < 5:
            return True
        if math_count >= 1 and normal_word_count < 2 and len(line) < 30:
            return True
        if len(line) > 0 and math_count / len(line) > 0.2 and normal_word_count < 3:
            return True
        if alpha_ratio < 0.2 and math_count >= 1:
            return True

        return False

    def _find_axis_label_block(self, lines: list[str], start: int) -> int:
        """检测从 start 开始的坐标轴标签块"""
        end = start
        while end < len(lines) and end - start < 20:
            stripped = lines[end].strip()
            if not stripped:
                end += 1
                continue
            if len(stripped) > 30:
                break
            if re.match(r"^(Figure|Table|Fig\.)\s+\d+", stripped, re.IGNORECASE):
                break
            end += 1

        block_size = end - start
        if block_size < 5:
            return start

        block_lines = [lines[j].strip() for j in range(start, end) if lines[j].strip()]
        numeric_or_single = sum(
            1 for l in block_lines
            if re.match(r"^[\d.±\-+]+$", l) or len(l) <= 2
        )

        if len(block_lines) >= 5 and numeric_or_single / len(block_lines) > 0.5:
            return end
        return start

    def _merge_fragments(self, chunks: list[dict], min_tokens: int = 200, max_tokens: int = 1000) -> list[dict]:
        """合并过小的碎片 chunk"""
        if len(chunks) <= 1:
            return chunks

        result = []
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            tokens = self._estimate_tokens(chunk.get("text", ""))

            if chunk.get("chunk_index", -1) == 0 and tokens < min_tokens:
                result.append(chunk)
                i += 1
                continue

            if tokens >= min_tokens:
                result.append(chunk)
                i += 1
                continue

            if result:
                prev = result[-1]
                if (prev.get("section_type") == chunk.get("section_type")
                        and self._estimate_tokens(prev.get("text", "")) + tokens <= max_tokens):
                    prev["text"] = prev["text"] + "\n" + chunk["text"]
                    prev["page_end"] = max(prev.get("page_end", 0), chunk.get("page_end", 0))
                    i += 1
                    continue

            if i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                next_tokens = self._estimate_tokens(next_chunk.get("text", ""))
                if (next_chunk.get("section_type") == chunk.get("section_type")
                        and tokens + next_tokens <= max_tokens):
                    chunk["text"] = chunk["text"] + "\n" + next_chunk["text"]
                    chunk["page_end"] = max(chunk.get("page_end", 0), next_chunk.get("page_end", 0))
                    result.append(chunk)
                    i += 2
                    continue

            result.append(chunk)
            i += 1

        return result

    def _update_token_counts(self, chunks: list[dict]) -> list[dict]:
        """重新计算 token 数"""
        for chunk in chunks:
            chunk["token_count"] = self._estimate_tokens(chunk.get("text", ""))
        return chunks

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """粗略估算 token 数"""
        cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
        en_chars = len(text) - cn_chars
        return cn_chars // 2 + en_chars // 4


# ── T4.27 分块后去重 ─────────────────────────────────


class ChunkDeduplicator:
    """分块后去重：精确哈希 → 近似 MinHash → 余弦相似度"""

    def __init__(self, jaccard_threshold: float = 0.8, cosine_threshold: float = 0.9):
        self.jaccard_threshold = jaccard_threshold
        self.cosine_threshold = cosine_threshold

    def deduplicate(self, chunks: list[dict]) -> list[dict]:
        """三层去重管线"""
        chunks = self._exact_dedup(chunks)
        chunks = self._minhash_dedup(chunks)
        chunks = self._cosine_dedup(chunks)
        return chunks

    def _exact_dedup(self, chunks: list[dict]) -> list[dict]:
        """精确哈希去重：完全相同的文本"""
        seen: set[str] = set()
        result = []
        for c in chunks:
            h = hashlib.sha256(c.get("text", "").encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                result.append(c)
        return result

    def _minhash_dedup(self, chunks: list[dict]) -> list[dict]:
        """MinHash 近似去重：Jaccard ≥ threshold 的近似重复"""
        try:
            from datasketch import MinHash, MinHashLSH
        except ImportError:
            logger.debug("datasketch not installed, skipping MinHash dedup")
            return chunks

        lsh = MinHashLSH(threshold=self.jaccard_threshold, num_perm=128)
        result = []

        for i, c in enumerate(chunks):
            m = MinHash(num_perm=128)
            text = c.get("text", "").lower()
            for j in range(len(text) - 4):
                m.update(text[j : j + 5].encode("utf8"))

            duplicates = lsh.query(m)
            if not duplicates:
                lsh.insert(f"chunk_{i}", m)
                result.append(c)

        return result

    def _cosine_dedup(self, chunks: list[dict]) -> list[dict]:
        """BM25 语义相似度去重：≥ threshold 的语义重复"""
        if len(chunks) < 2:
            return chunks

        sim_matrix = _bm25_pairwise_similarity(chunks)
        if sim_matrix is None:
            return chunks

        to_remove: set[int] = set()
        for i in range(len(chunks)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(chunks)):
                if j in to_remove:
                    continue
                if sim_matrix[i][j] >= self.cosine_threshold:
                    if len(chunks[i].get("text", "")) < len(chunks[j].get("text", "")):
                        to_remove.add(i)
                    else:
                        to_remove.add(j)

        return [c for idx, c in enumerate(chunks) if idx not in to_remove]


# ── T4.28 分块质量评分 ───────────────────────────────


class ChunkQualityScorer:
    """分块质量评分器"""

    WEIGHTS = {
        "length_score": 0.25,
        "info_density": 0.25,
        "structure_score": 0.20,
        "language_score": 0.15,
        "noise_score": 0.15,
    }

    _STOPWORDS = frozenset(
        {"the", "a", "an", "is", "are", "was", "were", "in", "on",
         "at", "to", "for", "of", "with", "and", "or", "but", "not"}
    )

    def score(self, chunk: dict) -> dict:
        """计算 chunk 质量分，返回 0-1 分数和各维度详情"""
        text = chunk.get("text", "")
        scores = {
            "length_score": self._score_length(text),
            "info_density": self._score_info_density(text),
            "structure_score": self._score_structure(text),
            "language_score": self._score_language(text),
            "noise_score": self._score_noise(text),
        }
        weighted = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        return {"quality_score": round(weighted, 3), "details": scores}

    @staticmethod
    def _score_length(text: str) -> float:
        """长度评分：过短过长都扣分"""
        tokens = len(text.split())
        if tokens < 30:
            return 0.2
        if tokens < 50:
            return 0.5
        if tokens <= 1000:
            return 1.0
        if tokens <= 1500:
            return 0.8
        return 0.5

    def _score_info_density(self, text: str) -> float:
        """信息密度：停用词占比、词汇多样性"""
        words = text.lower().split()
        if not words:
            return 0.0
        diversity = len(set(words)) / len(words)
        content_ratio = sum(1 for w in words if w not in self._STOPWORDS) / len(words)
        return min(1.0, (diversity * 0.5 + content_ratio * 0.5) * 1.5)

    @staticmethod
    def _score_structure(text: str) -> float:
        """结构评分：是否包含有意义的句子结构"""
        has_sentence = bool(re.search(r"[.!?。！？]\s", text))
        has_paragraph = "\n\n" in text or text.count("\n") > 3
        score = 0.5
        if has_sentence:
            score += 0.3
        if has_paragraph:
            score += 0.2
        return min(1.0, score)

    @staticmethod
    def _score_language(text: str) -> float:
        """语言一致性评分：中英文混杂扣分"""
        if not text:
            return 0.0
        cn_chars = sum(1 for c in text if "一" <= c <= "鿿")
        en_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total = cn_chars + en_chars
        if total == 0:
            return 0.0
        return max(cn_chars, en_chars) / total

    @staticmethod
    def _score_noise(text: str) -> float:
        """噪声评分：噪声越少分越高（反向）"""
        lines = text.split("\n")
        noise_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            math_chars = sum(
                1 for c in stripped if c in "∑∫∂∇αβγδεζηθ∈∉⊂⊃∪∩≈≠≤≥∞±×÷"
            )
            if len(stripped) > 0 and math_chars / len(stripped) > 0.2:
                noise_count += 1
            elif stripped.replace(" ", "").isdigit():
                noise_count += 1
            elif len(stripped) < 5 and not re.match(r"^\d+\.", stripped):
                noise_count += 1
        noise_ratio = noise_count / max(len(lines), 1)
        return max(0.0, 1.0 - noise_ratio * 3)


# ── T4.29 Chunk 冗余过滤 ─────────────────────────────


class ChunkRedundancyFilter:
    """Chunk 冗余过滤：BM25 + 动态阈值"""

    def __init__(self, redundancy_threshold: float = 0.85):
        self.threshold = redundancy_threshold

    def filter(self, chunks: list[dict]) -> list[dict]:
        """移除冗余 chunk，保留信息量更大的那个"""
        if len(chunks) < 2:
            return chunks

        sim = _bm25_pairwise_similarity(chunks)
        if sim is None:
            return chunks

        to_remove: set[int] = set()
        for i in range(len(chunks)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(chunks)):
                if j in to_remove:
                    continue
                if sim[i][j] >= self.threshold:
                    if len(chunks[i].get("text", "")) < len(chunks[j].get("text", "")):
                        to_remove.add(i)
                        break
                    else:
                        to_remove.add(j)

        return [c for idx, c in enumerate(chunks) if idx not in to_remove]


# ── 章节类型归一 ──────────────────────────────────────

_SECTION_TYPE_MAP: dict[str, str] = {
    "abstract": "abstract", "摘要": "abstract",
    "introduction": "introduction", "引言": "introduction", "导言": "introduction",
    "related work": "related_work", "相关工作": "related_work", "文献综述": "related_work",
    "background": "background", "背景": "background",
    "preliminary": "background", "preliminaries": "background",
    "method": "method", "方法": "method", "methodology": "method", "方法论": "method",
    "approach": "method", "approaches": "method",
    "experiment": "method", "实验": "method", "experiments": "method",
    "model": "method", "模型": "method",
    "estimation": "method", "估计": "method",
    "simulation": "method", "仿真": "method", "simulations": "method",
    "data analysis": "method", "数据分析": "method",
    "proposed method": "method", "proposed model": "method",
    "result": "result", "结果": "result", "results": "result",
    "simulation results": "result", "simulation settings": "method",
    "model selection": "method", "模型选择": "method",
    "model estimation": "method",
    "discussion": "discussion", "讨论": "discussion",
    "conclusion": "conclusion", "结论": "conclusion", "conclusions": "conclusion",
    "limitation": "limitation", "局限": "limitation", "limitations": "limitation",
    "future work": "future_work", "未来工作": "future_work", "future direction": "future_work",
    "acknowledgment": "acknowledgment", "致谢": "acknowledgment",
    "reference": "reference", "参考文献": "reference", "references": "reference",
    "appendix": "appendix", "附录": "appendix",
}

_SECTION_TO_CHUNK_TYPE: dict[str, str] = {
    "abstract": ChunkType.ABSTRACT.value,
    "introduction": ChunkType.BODY.value,
    "related_work": ChunkType.BODY.value,
    "background": ChunkType.BODY.value,
    "method": ChunkType.METHOD.value,
    "result": ChunkType.RESULT.value,
    "discussion": ChunkType.DISCUSSION.value,
    "limitation": ChunkType.LIMITATION.value,
    "conclusion": ChunkType.CONCLUSION.value,
    "future_work": ChunkType.BODY.value,
    "reference": ChunkType.REFERENCE.value,
    "appendix": ChunkType.APPENDIX.value,
    "acknowledgment": ChunkType.BODY.value,
}
