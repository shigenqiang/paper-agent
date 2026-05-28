"""论文卡片生成器 - LLM 驱动"""

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm_service import LLMConfig, LLMService, get_llm_service
from src.agents_v3.research_workspace.models import PaperCard, PaperStatus, SourceSpan
from src.agents_v3.research_workspace.storage import get_storage

SYSTEM_PROMPT = """你是一个学术论文分析专家。请从论文文本中提取结构化信息，输出 JSON 格式。

输出格式：
{
  "research_question": "研究问题",
  "method": "研究方法",
  "data_or_sample": "数据集或样本",
  "key_findings": ["发现1", "发现2"],
  "limitations": ["局限1", "局限2"],
  "future_work": ["未来方向1"],
  "topics": ["主题1", "主题2"],
  "possible_gaps": ["研究空白1"],
  "confidence": 0.8
}

要求：
- 字段无依据时填 "unknown" 或空列表
- 禁止编造 DOI、作者、年份
- key_findings 和 limitations 至少提取 2 条
- topics 从内容中推断，不超过 5 个
- confidence 根据文本质量评估（0-1）"""


class PaperCardGenerator:
    """从论文 chunks 生成结构化卡片"""

    def __init__(self, llm_service: LLMService | None = None):
        self.storage = get_storage()
        self.llm = llm_service or get_llm_service()

    def generate(self, paper_id: str) -> PaperCard | None:
        paper_data = self.storage.get_item("papers", paper_id)
        if not paper_data:
            return None

        chunks_data = self.storage.load_collection(f"chunks_{paper_id}")
        if not chunks_data:
            logger.warning(f"No chunks for paper {paper_id}")
            return None

        full_text = " ".join(c.get("text", "") for c in chunks_data)
        card = self._extract_card_with_llm(paper_id, paper_data, chunks_data, full_text)

        self.storage.upsert_item("paper_cards", card.card_id, card.model_dump())

        paper_data["status"] = PaperStatus.CARD_READY.value
        self.storage.upsert_item("papers", paper_id, paper_data)

        logger.info(f"Generated card for paper {paper_id}")
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
                existing = self.storage.query("paper_cards", {"paper_id": p["paper_id"]})
                if existing:
                    continue

            card = self.generate(p["paper_id"])
            if card:
                cards.append(card)

        return cards

    def _extract_card_with_llm(
        self,
        paper_id: str,
        paper_data: dict[str, Any],
        chunks: list[dict[str, Any]],
        full_text: str,
    ) -> PaperCard:
        card_id = f"card_{uuid.uuid4().hex[:8]}"

        # 截取文本避免超长
        text_for_llm = full_text[:8000] if len(full_text) > 8000 else full_text

        user_prompt = f"""论文标题：{paper_data.get('title', '未知')}

论文内容：
{text_for_llm}

请提取结构化信息，输出 JSON。"""

        try:
            result = self.llm.invoke_json(SYSTEM_PROMPT, user_prompt)

            # 构建 source_spans
            source_spans = []
            findings = result.get("key_findings", [])
            for i, chunk in enumerate(chunks[:len(findings)]):
                source_spans.append(SourceSpan(
                    field="key_findings",
                    chunk_id=chunk.get("chunk_id", f"chunk_{i}"),
                    quote=findings[i] if i < len(findings) else "",
                ))

            return PaperCard(
                card_id=card_id,
                paper_id=paper_id,
                project_id=paper_data.get("project_id", ""),
                research_question=result.get("research_question", "unknown"),
                method=result.get("method", "unknown"),
                data_or_sample=result.get("data_or_sample", "unknown"),
                key_findings=result.get("key_findings", ["unknown"]),
                limitations=result.get("limitations", ["unknown"]),
                future_work=result.get("future_work", ["unknown"]),
                topics=result.get("topics", []),
                possible_gaps=result.get("possible_gaps", []),
                source_spans=source_spans,
                confidence=result.get("confidence", 0.5),
            )
        except Exception as e:
            logger.error(f"LLM extraction failed for {paper_id}: {e}")
            return self._extract_card_fallback(paper_id, paper_data, chunks, full_text)

    def _extract_card_fallback(
        self,
        paper_id: str,
        paper_data: dict[str, Any],
        chunks: list[dict[str, Any]],
        full_text: str,
    ) -> PaperCard:
        """LLM 失败时的降级提取"""
        card_id = f"card_{uuid.uuid4().hex[:8]}"

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

        return PaperCard(
            card_id=card_id,
            paper_id=paper_id,
            project_id=paper_data.get("project_id", ""),
            research_question="unknown",
            method="unknown",
            data_or_sample="unknown",
            key_findings=key_findings if key_findings else ["unknown"],
            limitations=limitations if limitations else ["unknown"],
            future_work=future_work if future_work else ["unknown"],
            topics=[],
            possible_gaps=[],
            source_spans=source_spans,
            confidence=0.3,
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
