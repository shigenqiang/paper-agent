"""Prompt 注册表"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptTemplateSpec(BaseModel):
    """Prompt 模板规范"""
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


# ── 内置 Prompts ──────────────────────────────────

PAPER_CARD_PROMPT = PromptTemplateSpec(
    name="paper_card_extraction",
    version="v1",
    module="paper_card",
    task_type="structured_extraction",
    system_prompt="学术论文结构化信息抽取器。只能使用输入 chunks，每条 finding/limitation/future_work 必须有 quote 和 chunk_id。",
    output_schema_name="PaperCardExtractionResult",
    rules=[
        "只能使用输入的 chunks 内容",
        "每条关键 claim 必须有 quote 和 chunk_id",
        "无依据填 unknown 或空列表",
        "禁止编造 DOI、作者、年份",
    ],
    forbidden=["编造数据", "使用外部知识"],
)

SCOPE_QA_PROMPT = PromptTemplateSpec(
    name="scope_qa_answer",
    version="v1",
    module="scope_qa",
    task_type="qa_generation",
    system_prompt="学术论文分析助手。只能基于给定 Scope 和 Evidence 回答。每个关键结论尽量绑定 evidence_id。",
    output_schema_name="QAResponse",
    rules=[
        "只能基于给定 Scope 和 Evidence 回答",
        "不得引用不存在的 paper_id/evidence_id",
        "证据不足必须说明不确定性或拒答",
    ],
    forbidden=["编造引用", "引用 scope 外内容"],
)

REVIEW_PROMPT = PromptTemplateSpec(
    name="review_generation",
    version="v1",
    module="review_generator",
    task_type="report_generation",
    system_prompt="学术文献综述写作专家。每个主要章节必须返回 evidence_ids。证据不足写限制说明。",
    output_schema_name="ReviewGenerationResult",
    rules=[
        "只能使用输入材料",
        "每个章节必须标注 evidence_ids",
        "证据不足写入限制说明",
    ],
    forbidden=["编造论文", "引用 scope 外内容"],
)

INNOVATION_PROMPT = PromptTemplateSpec(
    name="innovation_generation",
    version="v1",
    module="innovation_generator",
    task_type="innovation_analysis",
    system_prompt="学术研究创新分析专家。创新点必须有具体证据支撑。不得自造 paper_id/evidence_id。",
    output_schema_name="InnovationGenerationResult",
    rules=[
        "创新点必须有证据支撑",
        "不得自造 paper_id/evidence_id",
        "评估可行性和风险要考虑具体约束",
    ],
    forbidden=["空泛建议", "编造来源"],
)


class PromptRegistry:
    """Prompt 注册表"""

    def __init__(self):
        self._prompts: dict[str, PromptTemplateSpec] = {}
        self._register_builtins()

    def _register_builtins(self):
        for prompt in [PAPER_CARD_PROMPT, SCOPE_QA_PROMPT, REVIEW_PROMPT, INNOVATION_PROMPT]:
            key = f"{prompt.name}_{prompt.version}"
            self._prompts[key] = prompt

    def get(self, name: str, version: str | None = None) -> PromptTemplateSpec | None:
        """获取 prompt 模板"""
        if version:
            return self._prompts.get(f"{name}_{version}")
        # 返回最新版本
        matches = [p for p in self._prompts.values() if p.name == name]
        return matches[-1] if matches else None

    def register(self, spec: PromptTemplateSpec) -> None:
        """注册 prompt 模板"""
        key = f"{spec.name}_{spec.version}"
        self._prompts[key] = spec

    def list(self, module: str | None = None) -> list[PromptTemplateSpec]:
        """列出所有 prompt"""
        prompts = list(self._prompts.values())
        if module:
            prompts = [p for p in prompts if p.module == module]
        return prompts


# 全局单例
_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
