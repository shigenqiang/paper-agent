"""
Paper Agents - 基于论文写作流程的多Agent系统

Agent列表:
- TopicAgent: 主题选择
- LiteratureAgent: 文献工作
- ThesisAgent: 研究凝练
- OutlineAgent: 大纲制定
- DraftWriterAgent: 分节撰写
- EditorAgent: 修订编辑
- ReviewerAgent: 最终审核
- DigestReportAgent: 学术资讯快报生成
"""
from .topic_agent import TopicAgent
from .literature_agent import LiteratureAgent
from .thesis_agent import ThesisAgent
from .outline_agent import OutlineAgent
from .draft_writer import DraftWriterAgent
from .editor_agent import EditorAgent
from .reviewer_agent import ReviewerAgent
from .digest_agent import DigestReportAgent

__all__ = [
    "TopicAgent",
    "LiteratureAgent",
    "ThesisAgent",
    "OutlineAgent",
    "DraftWriterAgent",
    "EditorAgent",
    "ReviewerAgent",
    "DigestReportAgent",
]
