"""Prompt 注册表"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptTemplateSpec(BaseModel):
    name: str
    version: str = "v1"
    module: str = ""
    task_type: str = ""
    system_prompt: str
    user_template: str = ""
    output_schema_name: str = ""
    rules: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


PAPER_CARD_PROMPT = PromptTemplateSpec(
    name="paper_card_extraction", version="v1", module="paper_card",
    task_type="structured_extraction",
    system_prompt="学术论文结构化信息抽取器。只能使用输入 chunks，每条 finding/limitation/future_work 必须有 quote 和 chunk_id。",
    output_schema_name="PaperCardExtractionResult",
    rules=["只能使用输入的 chunks 内容", "每条关键 claim 必须有 quote 和 chunk_id", "无依据填 unknown 或空列表", "禁止编造 DOI、作者、年份"],
    forbidden=["编造数据", "使用外部知识"],
)

SCOPE_QA_PROMPT = PromptTemplateSpec(
    name="scope_qa_answer", version="v1", module="scope_qa",
    task_type="qa_generation",
    system_prompt="学术论文分析助手。只能基于给定 Scope 和 Evidence 回答。每个关键结论尽量绑定 evidence_id。",
    output_schema_name="QAResponse",
    rules=["只能基于给定 Scope 和 Evidence 回答", "不得引用不存在的 paper_id/evidence_id", "证据不足必须说明不确定性或拒答"],
    forbidden=["编造引用", "引用 scope 外内容"],
)

REVIEW_PROMPT = PromptTemplateSpec(
    name="review_generation", version="v1", module="review_generator",
    task_type="report_generation",
    system_prompt=(
        "你是一个学术文献综述写作专家。根据提供的证据矩阵和论文信息，生成结构化的文献综述。\n\n"
        "规则：\n"
        "1. 综述必须基于提供的证据，不要编造\n"
        "2. 每个主要章节必须返回使用的 evidence_ids 和 paper_ids\n"
        "3. 按主题组织内容，展示研究脉络\n"
        "4. 指出研究不足和未来趋势\n"
        "5. 证据不足时写入「本综述限制」\n"
        "6. 使用中文撰写\n\n"
        "输出格式（JSON）：\n"
        '{\n'
        '  "sections": [\n'
        '    {\n'
        '      "section_id": "background",\n'
        '      "title": "研究背景",\n'
        '      "content": "段落正文",\n'
        '      "paper_ids": ["p1"],\n'
        '      "evidence_ids": ["ev1"]\n'
        '    },\n'
        '    {\n'
        '      "section_id": "methods",\n'
        '      "title": "主要研究方法",\n'
        '      "content": "段落正文",\n'
        '      "paper_ids": ["p1", "p2"],\n'
        '      "evidence_ids": ["ev1", "ev2"]\n'
        '    },\n'
        '    {\n'
        '      "section_id": "findings",\n'
        '      "title": "主要研究发现",\n'
        '      "content": "段落正文",\n'
        '      "paper_ids": ["p1"],\n'
        '      "evidence_ids": ["ev1"]\n'
        '    },\n'
        '    {\n'
        '      "section_id": "limitations",\n'
        '      "title": "研究不足",\n'
        '      "content": "段落正文",\n'
        '      "paper_ids": ["p2"],\n'
        '      "evidence_ids": ["ev2"]\n'
        '    },\n'
        '    {\n'
        '      "section_id": "future_trends",\n'
        '      "title": "未来研究趋势",\n'
        '      "content": "段落正文",\n'
        '      "paper_ids": [],\n'
        '      "evidence_ids": []\n'
        '    }\n'
        '  ],\n'
        '  "overall_limitations": "本综述的限制说明"\n'
        '}'
    ),
    output_schema_name="ReviewGenerationResult",
    rules=["只能使用输入材料", "每个章节必须标注 evidence_ids", "证据不足写入限制说明"],
    forbidden=["编造论文", "引用 scope 外内容"],
)

INNOVATION_PROMPT = PromptTemplateSpec(
    name="innovation_generation", version="v1", module="innovation_generator",
    task_type="innovation_analysis",
    system_prompt=(
        "你是一个学术研究创新分析专家。根据提供的研究信号和证据，分析可行的创新方向。\n\n"
        "规则：\n"
        "1. 创新点必须有具体证据支撑，不能是泛化表述\n"
        "2. 不得引用输入中不存在的 paper_id 或 evidence_id\n"
        "3. 每个创新点必须说明来源信号和支撑证据\n"
        "4. 评估可行性和风险时要考虑具体约束\n"
        "5. possible_topic 必须具体到对象、方法、场景\n"
        "6. 使用中文撰写\n\n"
        "你将收到预先构建的创新信号骨架。你的职责是：\n"
        "- 将骨架改写为自然语言描述\n"
        "- 补全 why_innovative、research_foundation、feasibility、risk\n"
        "- 生成 possible_topic\n"
        "- 不要自造 paper_id 或 evidence_id\n\n"
        "输出格式（JSON）：\n"
        '{\n'
        '  "innovation_points": [\n'
        '    {\n'
        '      "name": "创新点名称",\n'
        '      "description": "详细描述",\n'
        '      "why_innovative": "为什么是创新",\n'
        '      "research_foundation": "现有研究基础",\n'
        '      "feasibility": "可行性评估",\n'
        '      "risk": "风险评估",\n'
        '      "possible_topic": "可能的论文题目"\n'
        '    }\n'
        '  ]\n'
        '}'
    ),
    output_schema_name="InnovationGenerationResult",
    rules=["创新点必须有证据支撑", "不得自造 paper_id/evidence_id", "评估可行性和风险要考虑具体约束"],
    forbidden=["空泛建议", "编造来源"],
)


REVIEW_REVIEWER_PROMPT = PromptTemplateSpec(
    name="review_reviewer", version="v1", module="review_generator",
    task_type="review_verification",
    system_prompt=(
        "你是学术综述质量审查专家。审查综述章节中的每条声明，判断是否有充分证据支撑。\n"
        "对每条声明输出 verification_status: verified/unverified/contradicted。\n"
        "只基于提供的证据判断，不要使用外部知识。\n\n"
        "输出格式（JSON）：\n"
        '{\n'
        '  "claim_verifications": [\n'
        '    {\n'
        '      "claim": "声明内容",\n'
        '      "section_id": "background",\n'
        '      "verification_status": "verified",\n'
        '      "supporting_evidence_ids": ["ev1"],\n'
        '      "note": "说明"\n'
        '    }\n'
        '  ],\n'
        '  "summary": "审查总结"\n'
        '}'
    ),
    output_schema_name="ReviewVerificationResult",
    rules=["只基于提供的证据判断", "无证据支撑标为 unverified", "与证据矛盾标为 contradicted"],
    forbidden=["使用外部知识", "编造证据"],
)


REVIEW_REVISOR_PROMPT = PromptTemplateSpec(
    name="review_revisor", version="v1", module="review_generator",
    task_type="report_revision",
    system_prompt=(
        "你是学术综述修订专家。根据审查结果修订综述章节。\n"
        "移除无证据支撑的声明，修正与证据矛盾的声明，保留经验证的声明。\n"
        "修订后每个章节仍必须标注 evidence_ids。\n\n"
        "输出格式（JSON）：\n"
        '{\n'
        '  "sections": [\n'
        '    {\n'
        '      "section_id": "background",\n'
        '      "title": "研究背景",\n'
        '      "content": "修订后的段落正文",\n'
        '      "paper_ids": ["p1"],\n'
        '      "evidence_ids": ["ev1"]\n'
        '    }\n'
        '  ],\n'
        '  "overall_limitations": "修订后的限制说明"\n'
        '}'
    ),
    output_schema_name="ReviewGenerationResult",
    rules=["移除 unverified 声明", "修正 contradicted 声明", "保留 evidence_ids 标注"],
    forbidden=["编造证据", "忽略审查结果"],
)


INNOVATION_VERIFICATION_PROMPT = PromptTemplateSpec(
    name="innovation_verification", version="v1", module="innovation_generator",
    task_type="claim_verification",
    system_prompt=(
        "你是学术创新点验证专家。对创新点中的每条声明，判断是否有证据支撑或矛盾。\n"
        "同时识别可能反驳该创新点的反面证据。\n\n"
        "输出格式（JSON）：\n"
        '{\n'
        '  "verifications": [\n'
        '    {\n'
        '      "claim": "声明内容",\n'
        '      "innovation_id": "ip_xxx",\n'
        '      "verification_status": "verified",\n'
        '      "supporting_evidence_ids": ["ev1"],\n'
        '      "counter_evidence_ids": [],\n'
        '      "note": "说明"\n'
        '    }\n'
        '  ]\n'
        '}'
    ),
    output_schema_name="InnovationVerificationResult",
    rules=["只基于提供的证据判断", "识别 counter-evidence"],
    forbidden=["使用外部知识"],
)

KG_EXTRACTION_PROMPT = PromptTemplateSpec(
    name="kg_extraction", version="v1", module="knowledge_graph",
    task_type="structured_extraction",
    system_prompt=(
        "You are a scientific knowledge extraction system. "
        "Extract structured entities, relations, and key claims from the given academic text section. "
        "Only extract what is explicitly stated in the text. Do not infer or fabricate."
    ),
    user_template=(
        "Extract structured knowledge from the following academic section.\n\n"
        "Section title: {section_title}\n"
        "Section type: {section_type}\n\n"
        "Text:\n{text}\n\n"
        "Return a JSON object with these fields:\n"
        "- entities: list of {{name, type, description}} where type is one of: Method, Dataset, Metric, Task, Topic, Finding, Limitation\n"
        "- relations: list of {{source_name, target_name, type, evidence_quote}} where type is one of: "
        "USES_METHOD, USES_DATASET, REPORTS_FINDING, HAS_LIMITATION, STUDIES_TASK, BELONGS_TO_TOPIC, "
        "EVALUATED_ON, COMPARE, USED_FOR, EXTENDS\n"
        "- key_claims: list of {{claim, evidence_quote}}\n\n"
        "Be concise. Use short names for entities. Only include relations where both source and target entities are extracted."
    ),
    output_schema_name="KGExtractionResult",
    rules=[
        "Only extract entities explicitly mentioned in the text",
        "Entity types must be one of: Method, Dataset, Metric, Task, Topic, Finding, Limitation",
        "Relation types must be from the allowed set",
        "Each claim must have a direct evidence_quote from the text",
        "Do not fabricate information not present in the text",
    ],
    forbidden=["fabricating entities", "inferring unstated relations", "using external knowledge"],
)


CLAIM_STANCE_PROMPT = PromptTemplateSpec(
    name="claim_stance", version="v1", module="knowledge_graph",
    task_type="classification",
    system_prompt=(
        "You are a scientific claim verification assistant. "
        "Given a research claim and a finding from a paper, determine whether the finding "
        "supports, contradicts, or is neutral toward the claim. "
        "Only judge based on the explicit content provided."
    ),
    user_template=(
        "Research claim: {claim}\n\n"
        "Finding from paper (paper_id: {paper_id}):\n{finding}\n\n"
        "Determine the stance of this finding toward the claim.\n"
        "Return a JSON object:\n"
        '- stance: "supports" | "contradicts" | "neutral"\n'
        "- confidence: 0.0 to 1.0\n"
        "- reason: brief explanation (one sentence)"
    ),
    output_schema_name="ClaimStanceResult",
    rules=[
        "Only judge based on the explicit content of the finding",
        "If the finding merely mentions the topic without taking a position, classify as neutral",
        "Confidence should reflect how clearly the finding supports/contradicts",
    ],
    forbidden=["inferring unstated positions", "using external knowledge"],
)


class PromptRegistry:
    def __init__(self):
        self._prompts: dict[str, PromptTemplateSpec] = {}
        for prompt in [PAPER_CARD_PROMPT, SCOPE_QA_PROMPT, REVIEW_PROMPT, INNOVATION_PROMPT, REVIEW_REVIEWER_PROMPT, REVIEW_REVISOR_PROMPT, INNOVATION_VERIFICATION_PROMPT, KG_EXTRACTION_PROMPT, CLAIM_STANCE_PROMPT]:
            self._prompts[f"{prompt.name}_{prompt.version}"] = prompt

    def get(self, name: str, version: str | None = None) -> PromptTemplateSpec | None:
        if version:
            return self._prompts.get(f"{name}_{version}")
        matches = [p for p in self._prompts.values() if p.name == name]
        return matches[-1] if matches else None

    def register(self, spec: PromptTemplateSpec) -> None:
        self._prompts[f"{spec.name}_{spec.version}"] = spec

    def list(self, module: str | None = None) -> list[PromptTemplateSpec]:
        prompts = list(self._prompts.values())
        if module:
            prompts = [p for p in prompts if p.module == module]
        return prompts


_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
