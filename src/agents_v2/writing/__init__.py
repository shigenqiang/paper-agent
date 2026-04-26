"""
论文写作全流程Agent模块

Agent列表:
- LiteratureReviewAgent: 文献综述
- OutlineGeneratorAgent: 大纲生成
- DraftGeneratorAgent: 全文初稿
- ReportRefinerAgent: 报告精炼(多轮迭代)
- ProposalGeneratorAgent: 开题报告
- ReferenceProcessorAgent: 参考文献处理
- SmartReviserAgent: 智能改稿
- LanguagePolisherAgent: 语言润色
"""
from .literature_review import LiteratureReviewAgent
from .outline_generator import OutlineGeneratorAgent
from .draft_generator import DraftGeneratorAgent
from .report_refiner import ReportRefinerAgent, ReviewerAgent
from .proposal_generator import ProposalGeneratorAgent
from .reference_processor import ReferenceProcessorAgent
from .smart_reviser import SmartReviserAgent, LanguagePolisherAgent

__all__ = [
    "LiteratureReviewAgent",
    "OutlineGeneratorAgent",
    "DraftGeneratorAgent",
    "ReportRefinerAgent",
    "ReviewerAgent",
    "ProposalGeneratorAgent",
    "ReferenceProcessorAgent",
    "SmartReviserAgent",
    "LanguagePolisherAgent",
]