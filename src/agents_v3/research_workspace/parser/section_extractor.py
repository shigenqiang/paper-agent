"""论文章节级结构化提取服务

对每个 PaperSection 调用 LLM，按 section_type 提取对应结构化字段。
遵循 docs/research/02-提示词工程/Agent提示词工程指南.md 规范。
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from src.agents_v3.research_workspace.llm.service import LLMService, get_llm_service
from src.agents_v3.research_workspace.models import PaperSection
from src.agents_v3.research_workspace.storage import JSONStorage, get_storage

# ── 按 section_type 定义提取 prompt ──────────────────────

_ABSTRACT_PROMPT = """## 角色
你是一个学术论文结构化信息抽取器，专注于从论文 Abstract 中提取核心信息。

## 能力边界
- 你只能使用输入的文本内容，不能使用外部知识
- 你擅长识别研究问题、方法、关键发现和局限性

## 行为准则
1. 逐句分析 Abstract，识别每句话的信息类型
2. 提取具体的方法名称、数据集名称、量化指标
3. 对于 key_results，提取 metric（指标名）、value（具体数值）、quote（原文）
4. 无法确认的字段留空列表，不要编造

## 约束限制
- quote 必须是原文片段
- 不要编造数据或指标
- 每个列表至少保留 1 条，最多 5 条

## 输出格式（JSON）：
{
  "summary": "用 2-3 句话概括本章节的核心内容，不超过 200 字",
  "claims": [{"claim": "核心论点描述", "evidence_quote": "原文引用", "confidence": 0.8}],
  "entities": [{"name": "实体名", "entity_type": "Method/Dataset/Metric/Task", "mention_text": "原文片段"}],
  "methods_used": ["方法1", "方法2"],
  "datasets_used": ["数据集1"],
  "key_results": [{"metric": "指标名", "value": "具体数值", "quote": "原文引用"}],
  "limitations": ["局限性1"],
  "future_work": ["未来方向1"]
}

## 示例
输入：Abstract: "We propose Transformer, a novel architecture based solely on attention mechanisms. Experiments on WMT 2014 EN-DE achieve 28.4 BLEU, outperforming previous models by 2 BLEU points while reducing training time."
输出：
{
  "claims": [{"claim": "Transformer 仅基于注意力机制替代循环结构", "evidence_quote": "based solely on attention mechanisms", "confidence": 0.9}],
  "entities": [
    {"name": "Transformer", "entity_type": "Method", "mention_text": "Transformer, a novel architecture"},
    {"name": "WMT 2014 EN-DE", "entity_type": "Dataset", "mention_text": "WMT 2014 EN-DE"}
  ],
  "methods_used": ["attention mechanism", "Transformer"],
  "datasets_used": ["WMT 2014 EN-DE"],
  "key_results": [{"metric": "BLEU", "value": "28.4", "quote": "achieved 28.4 BLEU"}],
  "limitations": ["仅在机器翻译任务上验证"],
  "future_work": ["应用到其他序列任务"]
}"""

_INTRODUCTION_PROMPT = """## 角色
你是一个学术论文结构化信息抽取器，专注于从论文 Introduction 中提取研究动机、空白和贡献。

## 能力边界
- 你只能使用输入的文本内容，不能使用外部知识
- 你擅长识别研究背景、现有工作的不足、以及本文的创新点

## 行为准则
1. 识别背景知识（background_points）：领域现状、已有方法
2. 识别研究空白（gap_points）：现有方法的不足、未解决的问题
3. 识别本文贡献（contribution_points）：本文提出的新方法/新发现
4. 提取引用的前人文献（prior_work_refs）：文中明确引用的前人工作名称

## 约束限制
- 每个列表 1-5 条
- quote 必须是原文片段
- 不要编造前人文献

## 输出格式（JSON）：
{
  "summary": "用 2-3 句话概括本章节的核心内容，不超过 200 字",
  "claims": [{"claim": "核心论点", "evidence_quote": "原文引用", "confidence": 0.8}],
  "entities": [{"name": "实体名", "entity_type": "Method/Theory/Task", "mention_text": "原文片段"}],
  "background_points": ["背景要点1", "背景要点2"],
  "gap_points": ["研究空白1", "研究空白2"],
  "contribution_points": ["贡献1", "贡献2"],
  "prior_work_refs": ["前人工作名称1", "前人工作名称2"]
}

## 示例
输入：Introduction: "Existing sequence models rely on recurrent architectures (Bahdanau 2015), which are hard to parallelize. We propose the Transformer, which replaces recurrence entirely with multi-head self-attention, achieving 3.5x faster training."
输出：
{
  "summary": "现有循环序列模型难以并行化，本文提出 Transformer 架构，完全基于多头自注意力替代循环结构，训练速度提升 3.5 倍。",
  "claims": [{"claim": "循环架构难以并行化，Transformer 通过注意力机制解决此问题", "evidence_quote": "replaces recurrence entirely with multi-head self-attention", "confidence": 0.9}],
  "entities": [{"name": "multi-head self-attention", "entity_type": "Method", "mention_text": "multi-head self-attention"}],
  "background_points": ["现有序列模型依赖循环架构", "循环架构难以并行化"],
  "gap_points": ["缺乏完全基于注意力的并行化序列模型"],
  "contribution_points": ["提出 Transformer 架构", "训练速度提升 3.5 倍"],
  "prior_work_refs": ["Bahdanau 2015"]
}"""

_METHOD_PROMPT = """## 角色
你是一个学术论文结构化信息抽取器，专注于从论文 Method/Experiments 中提取方法、数据集和模型细节。

## 能力边界
- 你只能使用输入的文本内容，不能使用外部知识
- 你擅长识别具体的技术方法、模型架构、数据集和超参数

## 行为准则
1. 提取具体的方法/算法/技术名称（methods_used）
2. 提取使用的数据集名称（datasets_used）
3. 提取模型架构细节（model_details）
4. 识别方法相关的实体（entities）

## 约束限制
- 提取具体名称，不要泛泛描述（如 "深度学习" → "BERT-base-uncased"）
- 每个列表 1-8 条
- quote 必须是原文片段

## 输出格式（JSON）：
{
  "summary": "用 2-3 句话概括本章节的核心内容，不超过 200 字",
  "claims": [{"claim": "方法描述", "evidence_quote": "原文引用", "confidence": 0.8}],
  "entities": [{"name": "实体名", "entity_type": "Method/Dataset/Model", "mention_text": "原文片段"}],
  "methods_used": ["方法1", "方法2"],
  "datasets_used": ["数据集1", "数据集2"],
  "model_details": ["模型细节1", "模型细节2"]
}

## 示例
输入：Method: "We use BERT-base as encoder with 12 layers and 110M parameters. The model is fine-tuned on SQuAD 2.0 with learning rate 3e-5 and batch size 32."
输出：
{
  "claims": [{"claim": "使用 BERT-base 作为编码器在 SQuAD 2.0 上微调", "evidence_quote": "BERT-base as encoder...fine-tuned on SQuAD 2.0", "confidence": 0.9}],
  "entities": [
    {"name": "BERT-base", "entity_type": "Method", "mention_text": "BERT-base as encoder"},
    {"name": "SQuAD 2.0", "entity_type": "Dataset", "mention_text": "SQuAD 2.0"}
  ],
  "methods_used": ["BERT-base", "fine-tuning"],
  "datasets_used": ["SQuAD 2.0"],
  "model_details": ["12 layers", "110M parameters", "learning rate 3e-5", "batch size 32"]
}"""

_RESULT_PROMPT = """## 角色
你是一个学术论文结构化信息抽取器，专注于从论文 Results 中提取量化结果和关键发现。

## 能力边界
- 你只能使用输入的文本内容，不能使用外部知识
- 你擅长识别实验指标、数值结果和比较结论

## 行为准则
1. 提取每项关键结果的 metric（指标名）、value（具体数值）、quote（原文引用）
2. 如果有表格数据，提取表格中的关键比较结果
3. 识别与 baseline 的对比结论

## 约束限制
- key_results 中的 metric 必须是具体指标名（如 BLEU、F1、Accuracy），不要用泛化描述
- value 必须是具体数值或数值范围
- 每个列表 1-10 条
- quote 必须是原文片段

## 输出格式（JSON）：
{
  "summary": "用 2-3 句话概括本章节的核心内容，不超过 200 字",
  "claims": [{"claim": "结果结论", "evidence_quote": "原文引用", "confidence": 0.8}],
  "entities": [{"name": "实体名", "entity_type": "Method/Metric/Dataset", "mention_text": "原文片段"}],
  "methods_used": ["对比方法1"],
  "datasets_used": ["数据集1"],
  "key_results": [
    {"metric": "BLEU", "value": "28.4", "quote": "achieved 28.4 BLEU on WMT 2014 EN-DE"},
    {"metric": "Training Time", "value": "3.5 days", "quote": "3.5 days on 8 GPUs"}
  ]
}

## 示例
输入：Results: "Table 2 shows our model achieves BLEU 28.4 on WMT 2014 EN-DE, surpassing the previous best by 2.0 points. Training takes 3.5 days on 8 P100 GPUs."
输出：
{
  "claims": [{"claim": "模型在 WMT 2014 EN-DE 上超越前人最佳 2.0 BLEU", "evidence_quote": "surpassing the previous best by 2.0 points", "confidence": 0.95}],
  "entities": [{"name": "WMT 2014 EN-DE", "entity_type": "Dataset", "mention_text": "WMT 2014 EN-DE"}],
  "key_results": [
    {"metric": "BLEU", "value": "28.4", "quote": "achieves BLEU 28.4 on WMT 2014 EN-DE"},
    {"metric": "BLEU Improvement", "value": "+2.0", "quote": "surpassing the previous best by 2.0 points"},
    {"metric": "Training Time", "value": "3.5 days", "quote": "3.5 days on 8 P100 GPUs"}
  ],
  "datasets_used": ["WMT 2014 EN-DE"]
}"""

_DISCUSSION_PROMPT = """## 角色
你是一个学术论文结构化信息抽取器，专注于从论文 Discussion/Conclusion 中提取局限性、未来方向和启示。

## 能力边界
- 你只能使用输入的文本内容，不能使用外部知识
- 你擅长识别作者明确承认的不足和未来计划

## 行为准则
1. 提取局限性（limitations）：作者明确提到的不足、未覆盖的场景
2. 提取未来方向（future_work）：作者提到的后续研究计划
3. 提取启示（implications）：研究结果的更广泛意义
4. 提取贡献（contribution_points）：讨论中重申的核心贡献

## 约束限制
- limitations 必须是作者明确提到的，不要推断
- 每个列表 1-5 条
- quote 必须是原文片段

## 输出格式（JSON）：
{
  "summary": "用 2-3 句话概括本章节的核心内容，不超过 200 字",
  "claims": [{"claim": "讨论要点", "evidence_quote": "原文引用", "confidence": 0.8}],
  "entities": [{"name": "实体名", "entity_type": "Method/Theory", "mention_text": "原文片段"}],
  "limitations": ["局限性1", "局限性2"],
  "future_work": ["未来方向1", "未来方向2"],
  "implications": ["启示1"],
  "contribution_points": ["贡献1"]
}

## 示例
输入：Discussion: "Our approach has several limitations: it was only evaluated on English-German translation. Future work should explore multilingual settings and document-level translation. Despite these limitations, our results demonstrate that attention alone is sufficient for high-quality translation."
输出：
{
  "claims": [{"claim": "仅注意力机制足以实现高质量翻译", "evidence_quote": "attention alone is sufficient for high-quality translation", "confidence": 0.9}],
  "entities": [],
  "limitations": ["仅在英德翻译任务上评估"],
  "future_work": ["探索多语言设置", "探索文档级翻译"],
  "implications": ["注意力机制足以替代循环结构"],
  "contribution_points": ["证明纯注意力架构可行"]
}"""

_GENERIC_PROMPT = """## 角色
你是一个学术论文结构化信息抽取器。

## 行为准则
从以下论文章节文本中提取结构化信息。

## 约束限制
- 只使用输入文本，不要使用外部知识
- quote 必须是原文片段
- 每个列表 1-5 条

## 输出格式（JSON）：
{
  "summary": "用 2-3 句话概括本章节的核心内容，不超过 200 字",
  "claims": [{"claim": "论点描述", "evidence_quote": "原文引用", "confidence": 0.7}],
  "entities": [{"name": "实体名", "entity_type": "Method/Dataset/Metric/Task/Theory", "mention_text": "原文片段"}]
}"""

_SECTION_PROMPTS: dict[str, str] = {
    "abstract": _ABSTRACT_PROMPT,
    "introduction": _INTRODUCTION_PROMPT,
    "method": _METHOD_PROMPT,
    "experiment": _METHOD_PROMPT,
    "result": _RESULT_PROMPT,
    "discussion": _DISCUSSION_PROMPT,
    "conclusion": _DISCUSSION_PROMPT,
    "limitation": _DISCUSSION_PROMPT,
}


class SectionExtractor:
    """论文章节级结构化提取"""

    def __init__(
        self,
        storage: JSONStorage | None = None,
        llm_service: LLMService | None = None,
    ):
        self.storage = storage or get_storage()
        self.llm = llm_service or get_llm_service()

    def extract_section(self, section: PaperSection, force: bool = False) -> PaperSection:
        """对单个章节执行 LLM 结构化提取"""
        if not force and section.extraction_status == "extracted":
            logger.debug(f"Section {section.section_id} already extracted, skipping")
            return section

        if not section.text or len(section.text.strip()) < 50:
            logger.warning(f"Section {section.section_id} text too short, skipping")
            section.extraction_status = "failed"
            return section

        prompt = _SECTION_PROMPTS.get(section.section_type.value, _GENERIC_PROMPT)

        text = section.text
        if len(text) > 12000:
            text = text[:12000] + "\n...(文本过长已截断)"

        user_prompt = f"""论文章节：{section.section_type.value} - {section.section_title}

章节文本：
{text}

请提取结构化信息，输出 JSON。"""

        try:
            result = self.llm.invoke_json(prompt, user_prompt)
            if not result or not isinstance(result, dict):
                logger.warning(f"LLM returned invalid result for section {section.section_id}")
                section.extraction_status = "failed"
                return section

            section = self._fill_fields(section, result)
            section.extraction_status = "extracted"
            logger.info(f"Extracted section {section.section_id} ({section.section_type.value}): "
                        f"{len(section.claims)} claims, {len(section.entities)} entities")

        except Exception as e:
            logger.error(f"Extraction failed for section {section.section_id}: {e}")
            section.extraction_status = "failed"

        return section

    def extract_paper_sections(self, paper_id: str, force: bool = False) -> list[PaperSection]:
        """对一篇论文的所有章节执行提取"""
        sections_data = self.storage.query("paper_sections", {"paper_id": paper_id})
        if not sections_data:
            logger.warning(f"No sections found for paper {paper_id}")
            return []

        sections = [PaperSection(**s) for s in sections_data]
        extracted = []

        for section in sections:
            result = self.extract_section(section, force=force)
            extracted.append(result)
            self._save_section(result)

        success_count = sum(1 for s in extracted if s.extraction_status == "extracted")
        logger.info(f"Paper {paper_id}: {success_count}/{len(extracted)} sections extracted")
        return extracted

    def _fill_fields(self, section: PaperSection, result: dict) -> PaperSection:
        """将 LLM 提取结果填充到 PaperSection 字段"""
        from src.agents_v3.research_workspace.models import SectionClaim, SectionEntity

        if "summary" in result and isinstance(result["summary"], str) and result["summary"].strip():
            section.summary = result["summary"].strip()
        else:
            section.summary = self._generate_summary(section)

        if "claims" in result and isinstance(result["claims"], list):
            for c in result["claims"]:
                if isinstance(c, dict) and c.get("claim"):
                    section.claims.append(SectionClaim(
                        claim=c["claim"],
                        evidence_quote=c.get("evidence_quote", ""),
                        confidence=c.get("confidence", 0.7),
                    ))

        if "entities" in result and isinstance(result["entities"], list):
            for e in result["entities"]:
                if isinstance(e, dict) and e.get("name"):
                    section.entities.append(SectionEntity(
                        entity_id=f"ent_{section.section_id}_{len(section.entities):03d}",
                        name=e["name"],
                        entity_type=e.get("entity_type", ""),
                        mention_text=e.get("mention_text", ""),
                        confidence=0.8,
                    ))

        section_type = section.section_type.value

        if section_type in ("abstract", "method", "experiment", "result"):
            if "methods_used" in result:
                section.methods_used = [m for m in result["methods_used"] if isinstance(m, str)]
            if "datasets_used" in result:
                section.datasets_used = [d for d in result["datasets_used"] if isinstance(d, str)]
            if "model_details" in result:
                section.model_details = [d for d in result["model_details"] if isinstance(d, str)]

        if section_type in ("abstract", "result"):
            if "key_results" in result and isinstance(result["key_results"], list):
                for kr in result["key_results"]:
                    if isinstance(kr, dict) and kr.get("metric"):
                        section.key_results.append({
                            "metric": kr["metric"],
                            "value": kr.get("value", ""),
                            "quote": kr.get("quote", ""),
                        })

        if section_type == "introduction":
            if "background_points" in result:
                section.background_points = [p for p in result["background_points"] if isinstance(p, str)]
            if "gap_points" in result:
                section.gap_points = [p for p in result["gap_points"] if isinstance(p, str)]
            if "contribution_points" in result:
                section.contribution_points = [p for p in result["contribution_points"] if isinstance(p, str)]
            if "prior_work_refs" in result:
                section.prior_work_refs = [r for r in result["prior_work_refs"] if isinstance(r, str)]

        if section_type in ("abstract", "discussion", "conclusion", "limitation"):
            if "limitations" in result:
                section.limitations = [l for l in result["limitations"] if isinstance(l, str)]
        if section_type in ("abstract", "discussion", "conclusion"):
            if "future_work" in result:
                section.future_work = [f for f in result["future_work"] if isinstance(f, str)]
        if section_type in ("discussion", "conclusion"):
            if "implications" in result:
                section.implications = [i for i in result["implications"] if isinstance(i, str)]

        if "contribution_points" in result and section_type != "introduction":
            section.contribution_points = [p for p in result["contribution_points"] if isinstance(p, str)]

        return section

    def _generate_summary(self, section: PaperSection) -> str:
        """从已提取字段生成章节摘要（LLM 未返回 summary 时的降级方案）"""
        parts = []
        if section.methods_used:
            parts.append(f"Methods: {', '.join(section.methods_used[:3])}")
        if section.key_results:
            results_str = "; ".join(
                f"{kr.get('metric', '')}={kr.get('value', '')}"
                for kr in section.key_results[:3]
                if kr.get("metric")
            )
            if results_str:
                parts.append(f"Results: {results_str}")
        if section.limitations:
            parts.append(f"Limitations: {', '.join(section.limitations[:2])}")
        if section.gap_points:
            parts.append(f"Gaps: {', '.join(section.gap_points[:2])}")
        if section.contribution_points:
            parts.append(f"Contributions: {', '.join(section.contribution_points[:2])}")
        if section.future_work:
            parts.append(f"Future: {', '.join(section.future_work[:2])}")
        if section.implications:
            parts.append(f"Implications: {', '.join(section.implications[:2])}")

        if parts:
            return f"[{section.section_type.value}] " + ". ".join(parts)

        text = section.text[:300].strip()
        if text:
            return f"[{section.section_type.value}] {text}"
        return ""

    def _save_section(self, section: PaperSection) -> None:
        """保存单个 section 到 storage"""
        existing = self.storage.load_collection("paper_sections")
        updated = []
        for s in existing:
            if s.get("section_id") == section.section_id:
                updated.append(section.model_dump())
            else:
                updated.append(s)
        self.storage.save_collection("paper_sections", updated)
