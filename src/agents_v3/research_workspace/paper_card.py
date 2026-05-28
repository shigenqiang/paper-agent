"""论文卡片生成器 - 增强版"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import (
    CardQualityReport,
    ExtractedClaim,
    PaperCard,
    PaperCardExtractionResult,
    PaperStatus,
    SourceSpan,
)
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage

# ── Prompt ────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个学术论文结构化信息抽取器。你的任务是从论文 chunks 中提取结构化信息。

规则：
1. 只能使用输入的 chunks 内容，不要使用外部知识
2. 每条 key_finding、limitation、future_work、possible_gap 必须给出 quote（原文引用）和 chunk_id
3. 无明确依据的字段填 "unknown" 或空列表
4. 禁止编造 DOI、作者、年份、具体数据、效果大小
5. 优先提取具体方法、样本量、指标、实验结果，不要泛泛总结
6. quote 必须是 chunk 中的原文片段（可以截取关键句）

输出格式（JSON）：
{
  "research_question": "研究问题",
  "method": "研究方法",
  "data_or_sample": "数据集或样本",
  "key_findings": [
    {"text": "发现描述", "quote": "原文引用", "chunk_id": "chunk_xxx"}
  ],
  "limitations": [
    {"text": "局限描述", "quote": "原文引用", "chunk_id": "chunk_xxx"}
  ],
  "future_work": [
    {"text": "未来方向", "quote": "原文引用", "chunk_id": "chunk_xxx"}
  ],
  "topics": ["主题1", "主题2"],
  "possible_gaps": [
    {"text": "研究空白", "quote": "原文引用", "chunk_id": "chunk_xxx"}
  ],
  "confidence": 0.7
}"""

# ── 章节选择预算 ──────────────────────────────────────

_SECTION_BUDGETS: dict[str, int] = {
    "abstract": 800,
    "introduction": 1200,
    "method": 1200,
    "result": 1800,
    "discussion": 1500,
    "conclusion": 1000,
    "limitation": 800,
    "future_work": 600,
    "related_work": 800,
    "background": 800,
}

# 字段对章节的偏好
_FIELD_SECTIONS: dict[str, list[str]] = {
    "research_question": ["abstract", "introduction"],
    "method": ["method", "introduction"],
    "data_or_sample": ["method"],
    "key_findings": ["result", "discussion", "conclusion"],
    "limitations": ["limitation", "discussion"],
    "future_work": ["conclusion", "future_work", "discussion"],
    "possible_gaps": ["introduction", "limitation", "future_work", "discussion"],
}

# 关键字段（需要 source_span 的字段）
_CRITICAL_FIELDS = ["key_findings", "limitations", "future_work", "possible_gaps"]

# 泛化套话检测
_GENERIC_PHRASES = [
    "需要进一步研究", "未来可以探索", "有待改进", "有一定局限性",
    "further research", "needs improvement", "limitation of this study",
    "提高效率", "优化模型", "加强研究", "扩大样本",
]


class ContextSelector:
    """按章节选择输入 chunks"""

    def select(
        self,
        chunks: list[dict[str, Any]],
        max_total_tokens: int = 8000,
    ) -> list[dict[str, Any]]:
        """按章节预算选择 chunks，返回按 section_type 分组后选择的子集"""
        # 按 section_type 分组
        by_section: dict[str, list[dict]] = {}
        for c in chunks:
            st = c.get("section_type", "body")
            by_section.setdefault(st, []).append(c)

        selected: list[dict[str, Any]] = []
        total_tokens = 0

        # 按预算优先级选择
        priority_order = [
            "abstract", "introduction", "method", "result",
            "discussion", "conclusion", "limitation", "future_work",
            "related_work", "background", "body", "",
        ]

        for section_type in priority_order:
            section_chunks = by_section.get(section_type, [])
            if not section_chunks:
                continue

            budget = _SECTION_BUDGETS.get(section_type, 1000)
            remaining_budget = min(budget, max_total_tokens - total_tokens)
            if remaining_budget <= 0:
                break

            section_tokens = 0
            for c in section_chunks:
                tokens = c.get("token_count", 0)
                if section_tokens + tokens > remaining_budget:
                    break
                selected.append(c)
                section_tokens += tokens
                total_tokens += tokens

            if total_tokens >= max_total_tokens:
                break

        # 按 chunk_index 排序
        selected.sort(key=lambda c: c.get("chunk_index", 0))
        return selected


class PaperCardGenerator:
    """从论文 chunks 生成结构化卡片"""

    def __init__(self, storage: JSONStorage | None = None, llm_service: LLMService | None = None):
        self.storage = storage or get_storage()
        self.llm = llm_service or get_llm_service()
        self.context_selector = ContextSelector()

    def generate(self, paper_id: str, regenerate: bool = False) -> PaperCard | None:
        paper_data = self.storage.get_item("papers", paper_id)
        if not paper_data:
            return None

        # 幂等：已有 active card 且非 regenerate 则返回
        if not regenerate:
            existing = self._get_active_card(paper_id)
            if existing:
                logger.info(f"Returning existing active card for {paper_id}")
                return existing

        # 获取 body chunks
        chunks_data = self._get_body_chunks(paper_id)
        if not chunks_data:
            logger.warning(f"No chunks for paper {paper_id}")
            return None

        project_id = paper_data.get("project_id", "")

        # 选择输入上下文
        selected_chunks = self.context_selector.select(chunks_data)
        input_chunk_ids = [c.get("chunk_id", "") for c in selected_chunks]

        # LLM 抽取
        card = self._extract_card(paper_id, project_id, paper_data, selected_chunks, input_chunk_ids)

        # 校验
        validation_errors = self._validate_card(card, chunks_data)
        card.validation_errors = validation_errors

        # 计算 confidence 和 quality_score
        card = self._compute_scores(card, chunks_data)

        # 标记旧 card 为 inactive
        if regenerate:
            self._deactivate_old_cards(paper_id)

        # 保存
        self.storage.upsert_item("paper_cards", card.card_id, card.model_dump())

        paper_data["status"] = PaperStatus.CARD_READY.value
        self.storage.upsert_item("papers", paper_id, paper_data)

        logger.info(f"Generated card for paper {paper_id} (v{card.version}, confidence={card.confidence:.2f})")
        return card

    def batch_generate(
        self, project_id: str, only_missing: bool = True
    ) -> list[PaperCard]:
        papers = self.storage.query("papers", {"project_id": project_id})
        cards = []

        for p in papers:
            if only_missing and p.get("status") in (
                PaperStatus.CARD_READY.value,
                PaperStatus.EVIDENCE_READY.value,
            ):
                existing = self._get_active_card(p["paper_id"])
                if existing:
                    continue

            card = self.generate(p["paper_id"])
            if card:
                cards.append(card)

        return cards

    def get_quality_report(self, paper_id: str) -> CardQualityReport | None:
        card = self._get_active_card(paper_id)
        if not card:
            return None

        chunks = self._get_body_chunks(paper_id)
        return self._build_quality_report(card, chunks)

    # ── 内部方法 ──────────────────────────────────────

    def _get_active_card(self, paper_id: str) -> PaperCard | None:
        cards = self.storage.query("paper_cards", {"paper_id": paper_id, "active": True})
        if cards:
            return PaperCard(**cards[0])
        return None

    def _deactivate_old_cards(self, paper_id: str) -> None:
        cards = self.storage.query("paper_cards", {"paper_id": paper_id})
        for c in cards:
            if c.get("active", True):
                c["active"] = False
                c["updated_at"] = datetime.now().isoformat()
                self.storage.upsert_item("paper_cards", c["card_id"], c)

    def _get_body_chunks(self, paper_id: str) -> list[dict[str, Any]]:
        """获取正文 chunks（排除 reference/table/figure_caption）"""
        all_chunks = self.storage.load_collection("paper_chunks")
        body = [
            c for c in all_chunks
            if c.get("paper_id") == paper_id
            and c.get("chunk_type", "body") not in ("reference", "table", "figure_caption")
        ]
        # 兼容旧格式
        if not body:
            old = self.storage.load_collection(f"chunks_{paper_id}")
            if old:
                body = [c for c in old if c.get("text", "").strip()]
        return body

    def _extract_card(
        self,
        paper_id: str,
        project_id: str,
        paper_data: dict[str, Any],
        chunks: list[dict[str, Any]],
        input_chunk_ids: list[str],
    ) -> PaperCard:
        """LLM 抽取或 fallback"""
        # 构建带 chunk_id 标记的输入
        chunks_text = self._build_chunks_text(chunks)
        user_prompt = f"""论文标题：{paper_data.get('title', '未知')}
作者：{', '.join(paper_data.get('authors', []))}
年份：{paper_data.get('year', '未知')}

Chunks:
{chunks_text}

请提取结构化信息，输出 JSON。每条 finding/limitation/future_work/gap 必须包含 quote 和 chunk_id。"""

        # 尝试 LLM 抽取
        if self.llm:
            try:
                result = self.llm.invoke_json(SYSTEM_PROMPT, user_prompt)
                # Pydantic 校验
                extraction = self._validate_extraction(result)
                if extraction:
                    return self._extraction_to_card(
                        paper_id, project_id, extraction, input_chunk_ids, "llm",
                    )
            except Exception as e:
                logger.error(f"LLM extraction failed for {paper_id}: {e}")

        # Fallback
        return self._extract_card_fallback(paper_id, project_id, paper_data, chunks, input_chunk_ids)

    def _validate_extraction(self, result: dict[str, Any]) -> PaperCardExtractionResult | None:
        """校验 LLM 输出，尝试 repair"""
        try:
            return PaperCardExtractionResult(**result)
        except Exception:
            # 尝试修复常见问题
            repaired = self._repair_extraction(result)
            try:
                return PaperCardExtractionResult(**repaired)
            except Exception:
                return None

    def _repair_extraction(self, result: dict[str, Any]) -> dict[str, Any]:
        """修复常见 LLM 输出格式问题"""
        # 把字符串列表转为 ExtractedClaim 列表
        for field in _CRITICAL_FIELDS:
            if field in result and isinstance(result[field], list):
                fixed = []
                for item in result[field]:
                    if isinstance(item, str):
                        fixed.append({"text": item, "quote": "", "chunk_id": ""})
                    elif isinstance(item, dict):
                        fixed.append(item)
                result[field] = fixed
        return result

    def _extraction_to_card(
        self,
        paper_id: str,
        project_id: str,
        extraction: PaperCardExtractionResult,
        input_chunk_ids: list[str],
        method: str,
    ) -> PaperCard:
        """将抽取结果转为 PaperCard"""
        card_id = f"card_{uuid.uuid4().hex[:8]}"
        source_spans: list[SourceSpan] = []

        # 从 ExtractedClaim 生成 source_spans
        for field in _CRITICAL_FIELDS:
            claims: list[ExtractedClaim] = getattr(extraction, field, [])
            for claim in claims:
                if claim.chunk_id or claim.quote:
                    source_spans.append(SourceSpan(
                        field=field,
                        chunk_id=claim.chunk_id,
                        quote=claim.quote,
                        section_type=claim.section_type,
                    ))

        # 计算版本号
        version = 1
        old_cards = self.storage.query("paper_cards", {"paper_id": paper_id})
        if old_cards:
            version = max(c.get("version", 0) for c in old_cards) + 1

        return PaperCard(
            card_id=card_id,
            paper_id=paper_id,
            project_id=project_id,
            version=version,
            active=True,
            research_question=extraction.research_question,
            method=extraction.method,
            data_or_sample=extraction.data_or_sample,
            key_findings=[c.text for c in extraction.key_findings],
            limitations=[c.text for c in extraction.limitations],
            future_work=[c.text for c in extraction.future_work],
            topics=extraction.topics,
            possible_gaps=[c.text for c in extraction.possible_gaps],
            source_spans=source_spans,
            input_chunk_ids=input_chunk_ids,
            extraction_method=method,
            confidence=extraction.confidence,
        )

    def _extract_card_fallback(
        self,
        paper_id: str,
        project_id: str,
        paper_data: dict[str, Any],
        chunks: list[dict[str, Any]],
        input_chunk_ids: list[str],
    ) -> PaperCard:
        """LLM 失败时的降级抽取"""
        card_id = f"card_{uuid.uuid4().hex[:8]}"
        full_text = " ".join(c.get("text", "") for c in chunks)

        key_findings = self._extract_list_from_text(full_text, ["finding", "result", "showed", "found"])
        limitations = self._extract_list_from_text(full_text, ["limitation", "weakness", "constraint"])
        future_work = self._extract_list_from_text(full_text, ["future", "next", "extend"])

        source_spans = []
        for i, chunk in enumerate(chunks[:3]):
            source_spans.append(SourceSpan(
                field="key_findings",
                chunk_id=chunk.get("chunk_id", f"chunk_{i}"),
                quote=chunk.get("text", "")[:200],
            ))

        # 版本号
        version = 1
        old_cards = self.storage.query("paper_cards", {"paper_id": paper_id})
        if old_cards:
            version = max(c.get("version", 0) for c in old_cards) + 1

        return PaperCard(
            card_id=card_id,
            paper_id=paper_id,
            project_id=project_id,
            version=version,
            active=True,
            research_question="unknown",
            method="unknown",
            data_or_sample="unknown",
            key_findings=key_findings if key_findings else ["unknown"],
            limitations=limitations if limitations else ["unknown"],
            future_work=future_work if future_work else ["unknown"],
            topics=[],
            possible_gaps=[],
            source_spans=source_spans,
            input_chunk_ids=input_chunk_ids,
            extraction_method="fallback",
            confidence=0.3,
        )

    def _build_chunks_text(self, chunks: list[dict[str, Any]]) -> str:
        """构建带 chunk_id 和 section 标记的输入文本"""
        parts = []
        for c in chunks:
            chunk_id = c.get("chunk_id", "")
            section = c.get("section_type", c.get("section_title", ""))
            page = c.get("page_start", c.get("page_number", 0))
            parts.append(f"[chunk_id={chunk_id}, section={section}, page={page}]")
            parts.append(c.get("text", ""))
            parts.append("")
        return "\n".join(parts)

    # ── 校验 ──────────────────────────────────────────

    def _validate_card(self, card: PaperCard, chunks: list[dict[str, Any]]) -> list[str]:
        """校验卡片来源和字段"""
        errors: list[str] = []
        chunk_ids = {c.get("chunk_id", "") for c in chunks}

        # 校验 source_span chunk_id 存在
        for span in card.source_spans:
            if span.chunk_id and span.chunk_id not in chunk_ids:
                errors.append(f"source_span chunk_id not found: {span.chunk_id}")

            # 校验 quote 匹配
            if span.chunk_id and span.quote:
                chunk = next((c for c in chunks if c.get("chunk_id") == span.chunk_id), None)
                if chunk:
                    chunk_text = chunk.get("text", "")
                    if span.quote not in chunk_text and not self._fuzzy_match(span.quote, chunk_text):
                        errors.append(f"quote not found in chunk {span.chunk_id}: {span.quote[:50]}...")

        # 检查泛化套话
        for field in _CRITICAL_FIELDS:
            values = getattr(card, field, [])
            for v in values:
                if isinstance(v, str) and self._is_generic(v):
                    card.quality_flags.append(f"generic:{field}")

        return errors

    def _fuzzy_match(self, quote: str, text: str, threshold: float = 0.6) -> bool:
        """模糊匹配：quote 的关键词在 text 中出现"""
        quote_words = set(re.findall(r"\w+", quote.lower()))
        text_words = set(re.findall(r"\w+", text.lower()))
        if not quote_words:
            return False
        overlap = len(quote_words & text_words)
        return overlap / len(quote_words) >= threshold

    def _is_generic(self, text: str) -> bool:
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in _GENERIC_PHRASES)

    # ── 分数计算 ──────────────────────────────────────

    def _compute_scores(self, card: PaperCard, chunks: list[dict[str, Any]]) -> PaperCard:
        """计算 confidence 和 quality_score"""
        # 完整度
        completeness = self._compute_completeness(card)
        # 可追溯度
        traceability = self._compute_traceability(card)
        # 具体度
        specificity = self._compute_specificity(card)

        # quality_score
        card.quality_score = 0.4 * completeness + 0.4 * traceability + 0.2 * specificity

        # confidence 调整
        base = card.confidence or 0.5
        if completeness >= 0.8:
            base += 0.1
        if traceability >= 0.8:
            base += 0.1
        if card.extraction_method == "fallback":
            base = min(base, 0.5)
        if "unknown" in card.research_question:
            base -= 0.1

        card.confidence = max(0.1, min(1.0, base))
        return card

    def _compute_completeness(self, card: PaperCard) -> float:
        fields = [
            card.research_question != "unknown",
            card.method != "unknown",
            card.data_or_sample != "unknown",
            len(card.key_findings) > 0 and card.key_findings != ["unknown"],
            len(card.limitations) > 0 and card.limitations != ["unknown"],
            len(card.future_work) > 0 and card.future_work != ["unknown"],
        ]
        return sum(fields) / len(fields)

    def _compute_traceability(self, card: PaperCard) -> float:
        critical_count = 0
        with_span = 0
        for field in _CRITICAL_FIELDS:
            values = getattr(card, field, [])
            for v in values:
                if v and v != "unknown":
                    critical_count += 1
                    # 检查是否有对应 source_span
                    if any(s.field == field and (s.chunk_id or s.quote) for s in card.source_spans):
                        with_span += 1
        if critical_count == 0:
            return 0.0
        return with_span / critical_count

    def _compute_specificity(self, card: PaperCard) -> float:
        """检查是否包含具体信息而非泛化套话"""
        all_text = " ".join(card.key_findings + card.limitations + card.future_work)
        if not all_text or all_text == "unknown":
            return 0.0
        generic_count = sum(1 for p in _GENERIC_PHRASES if p in all_text.lower())
        return max(0.0, 1.0 - generic_count * 0.2)

    def _build_quality_report(
        self, card: PaperCard, chunks: list[dict[str, Any]]
    ) -> CardQualityReport:
        completeness = self._compute_completeness(card)
        traceability = self._compute_traceability(card)
        specificity = self._compute_specificity(card)

        missing = []
        if card.research_question == "unknown":
            missing.append("research_question")
        if card.method == "unknown":
            missing.append("method")
        if not card.key_findings or card.key_findings == ["unknown"]:
            missing.append("key_findings")

        weak = []
        if "generic:key_findings" in card.quality_flags:
            weak.append("key_findings")
        if "generic:limitations" in card.quality_flags:
            weak.append("limitations")

        recommended = "accept"
        if completeness < 0.5:
            recommended = "regenerate"
        elif traceability < 0.3:
            recommended = "add_sources"

        return CardQualityReport(
            card_id=card.card_id,
            paper_id=card.paper_id,
            completeness=completeness,
            traceability=traceability,
            specificity=specificity,
            quote_match_rate=traceability,
            missing_fields=missing,
            weak_fields=weak,
            validation_errors=card.validation_errors,
            recommended_action=recommended,
        )

    def _extract_list_from_text(self, text: str, keywords: list[str]) -> list[str]:
        results = []
        sentences = text.split(".")
        for sent in sentences:
            lower = sent.lower()
            if any(kw in lower for kw in keywords):
                clean = sent.strip()
                if 10 < len(clean) < 500:
                    results.append(clean)
                    if len(results) >= 3:
                        break
        return results

    def _migrate_and_save_chunks(self, paper_id: str, old_chunks: list[dict]) -> None:
        """迁移旧格式 chunks 到 paper_chunks 集合"""
        migrated = []
        for i, c in enumerate(old_chunks):
            migrated.append({
                "chunk_id": c.get("chunk_id", f"chunk_{paper_id}_{i:04d}"),
                "paper_id": paper_id,
                "chunk_index": i,
                "section_title": c.get("section_title", ""),
                "section_type": "",
                "chunk_type": "body",
                "text": c.get("text", ""),
                "start_char": c.get("start_char", 0),
                "end_char": c.get("end_char", 0),
                "page_start": c.get("page_number", 0),
                "page_end": c.get("page_number", 0),
                "token_count": c.get("token_count", 0),
                "parser_name": "pdfplumber",
                "quality_flags": [],
                "metadata": {},
            })
        existing = self.storage.load_collection("paper_chunks")
        filtered = [c for c in existing if c.get("paper_id") != paper_id]
        filtered.extend(migrated)
        self.storage.save_collection("paper_chunks", filtered)
