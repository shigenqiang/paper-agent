"""知识图谱实体/关系提取服务 — 从 paper_sections 文本中 LLM 提取结构化知识"""

from __future__ import annotations

from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm.prompts import KG_EXTRACTION_PROMPT
from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.storage import get_storage

# section_type → 提取优先级（method/experiment/result 优先）
_SECTION_PRIORITY: dict[str, int] = {
    "method": 1, "experiment": 1, "result": 2, "results": 2,
    "abstract": 3, "introduction": 4, "discussion": 5,
    "conclusion": 3, "limitation": 2, "related_work": 6,
}

# 最少文本长度（字符数）
_MIN_TEXT_LENGTH = 80


class GraphExtractor:
    """从 parsed paper_sections 中提取实体和关系，回写到 JSONB 字段"""

    def __init__(self, storage=None, llm_service: LLMService | None = None):
        self.storage = storage or get_storage()
        self.llm = llm_service or get_llm_service()

    # ── 单篇论文提取 ──

    def extract_from_paper(self, paper_id: str) -> dict[str, Any]:
        """对一篇论文的所有 sections 做 LLM 提取，回写到 paper_sections"""
        sections = self.storage.query("paper_sections", {"paper_id": paper_id})
        if not sections:
            logger.warning(f"No sections found for paper {paper_id}")
            return {"entities": [], "relations": [], "sections_processed": 0}

        # 按优先级排序，重要 section 先处理
        sections.sort(key=lambda s: _SECTION_PRIORITY.get(s.get("section_type", ""), 9))

        all_entities: list[dict] = []
        all_relations: list[dict] = []
        all_claims: list[dict] = []
        processed = 0

        for section in sections:
            text = section.get("text", "").strip()
            if len(text) < _MIN_TEXT_LENGTH:
                continue

            # 跳过已提取的 section（除非 force）
            if section.get("extraction_status") == "done":
                all_entities.extend(section.get("entities", []))
                all_relations.extend(section.get("relations", []))
                all_claims.extend(section.get("claims", []))
                processed += 1
                continue

            result = self._extract_from_section(text, section)
            if result:
                self._update_section(section["section_id"], result)
                all_entities.extend(result.get("entities", []))
                all_relations.extend(result.get("relations", []))
                all_claims.extend(result.get("key_claims", []))
                processed += 1

        # 去重实体
        unique_entities = self._deduplicate_entities(all_entities)

        logger.info(
            f"Extracted from paper {paper_id}: "
            f"{len(unique_entities)} entities, {len(all_relations)} relations, "
            f"{processed} sections processed"
        )

        return {
            "entities": unique_entities,
            "relations": all_relations,
            "key_claims": all_claims,
            "sections_processed": processed,
        }

    # ── 项目级批量提取 ──

    def extract_from_project(self, project_id: str, only_missing: bool = True) -> dict[str, Any]:
        """批量提取项目所有已解析论文"""
        papers = self.storage.query("papers", {"project_id": project_id})
        results: dict[str, dict] = {}
        total_entities = 0
        total_relations = 0

        for p in papers:
            pid = p["paper_id"]
            status = p.get("status", "")
            if status not in ("parsed", "card_ready", "evidence_ready"):
                continue

            if only_missing:
                sections = self.storage.query("paper_sections", {"paper_id": pid})
                if all(s.get("extraction_status") == "done" for s in sections):
                    logger.info(f"Skipping {pid}: all sections already extracted")
                    continue

            try:
                result = self.extract_from_paper(pid)
                results[pid] = result
                total_entities += len(result.get("entities", []))
                total_relations += len(result.get("relations", []))
            except Exception as e:
                logger.error(f"Extraction failed for paper {pid}: {e}")
                results[pid] = {"error": str(e)}

        logger.info(
            f"Project extraction done: {len(results)} papers, "
            f"{total_entities} entities, {total_relations} relations"
        )

        return {
            "papers_processed": len(results),
            "total_entities": total_entities,
            "total_relations": total_relations,
            "details": results,
        }

    # ── 单 section LLM 提取 ──

    def _extract_from_section(self, text: str, section: dict) -> dict[str, Any] | None:
        """对单个 section 文本做 LLM 提取"""
        # 截断到 6000 字符避免超长
        if len(text) > 6000:
            text = text[:6000]

        section_title = section.get("section_title", "") or section.get("section_type", "")
        section_type = section.get("section_type", "unknown")

        system_prompt = KG_EXTRACTION_PROMPT.system_prompt
        user_prompt = KG_EXTRACTION_PROMPT.user_template.format(
            section_title=section_title,
            section_type=section_type,
            text=text,
        )

        try:
            result = self.llm.invoke_json(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"LLM extraction failed for section {section.get('section_id')}: {e}")
            return None

        if not result or "raw_response" in result:
            logger.warning(f"Invalid extraction result for section {section.get('section_id')}")
            return None

        # 验证基本结构
        entities = result.get("entities", [])
        relations = result.get("relations", [])
        claims = result.get("key_claims", [])

        if not isinstance(entities, list):
            entities = []
        if not isinstance(relations, list):
            relations = []
        if not isinstance(claims, list):
            claims = []

        return {
            "entities": entities,
            "relations": relations,
            "key_claims": claims,
        }

    # ── 回写 section JSONB ──

    def _update_section(self, section_id: str, result: dict) -> None:
        """回写提取结果到 paper_sections 的 JSONB 字段"""
        item = self.storage.get_item("paper_sections", section_id)
        if not item:
            return

        entities = result.get("entities", [])
        relations = result.get("relations", [])
        claims = result.get("key_claims", [])

        # 填充 JSONB 字段
        item["entities"] = entities
        item["relations"] = relations
        item["claims"] = claims

        # 按类型分类
        item["methods_used"] = [
            e["name"] for e in entities if e.get("type") == "Method"
        ]
        item["datasets_used"] = [
            e["name"] for e in entities if e.get("type") == "Dataset"
        ]
        item["key_results"] = [
            e["name"] for e in entities if e.get("type") == "Finding"
        ]
        item["limitations"] = [
            e["name"] for e in entities if e.get("type") == "Limitation"
        ]
        item["future_work"] = [
            e["name"] for e in entities if e.get("type") == "Gap"
        ]

        item["extraction_status"] = "done"
        self.storage.upsert_item("paper_sections", section_id, item)

    # ── 实体去重 ──

    @staticmethod
    def _deduplicate_entities(entities: list[dict]) -> list[dict]:
        """按 (name, type) 去重，合并 description"""
        seen: dict[tuple[str, str], dict] = {}
        for e in entities:
            name = (e.get("name") or "").strip().lower()
            etype = (e.get("type") or "").strip()
            if not name or not etype:
                continue
            key = (name, etype)
            if key not in seen:
                seen[key] = e
            else:
                # 合并 description
                existing_desc = seen[key].get("description", "")
                new_desc = e.get("description", "")
                if new_desc and new_desc not in existing_desc:
                    seen[key]["description"] = f"{existing_desc}; {new_desc}" if existing_desc else new_desc
        return list(seen.values())
