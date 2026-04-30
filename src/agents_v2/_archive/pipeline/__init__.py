"""
Pipeline型Agent模块 - 论文写作流程Agent

Pipeline流程:
1. TopicAgent - 选题
2. LiteratureAgent - 文献搜索与综述
3. ThesisAgent - Thesis凝练
4. OutlineAgent - 大纲生成
5. DraftWriterAgent - 初稿撰写
6. EditorAgent - 编辑
7. ReviewerAgent - 评审

Usage:
    from src.agents_v2.pipeline import TopicAgent, LiteratureAgent, DraftWriterAgent

    topic_agent = TopicAgent(llm_config)
    topic_result = await topic_agent.execute({"user_request": "我想写一篇关于..."})

    literature_agent = LiteratureAgent(llm_config)
    lit_result = await literature_agent.execute({"topic": topic_result.result})

    ...
"""
from .base_pipeline_agent import PipelineAgentBase, PipelineOutput, LLMConfig
from .topic_agent import TopicAgent
from .literature_agent import LiteratureAgent
from .thesis_agent import ThesisAgent
from .outline_agent import OutlineAgent
from .draft_writer_agent import DraftWriterAgent
from .editor_agent import EditorAgent
from .reviewer_agent import ReviewerAgent

__all__ = [
    "PipelineAgentBase",
    "PipelineOutput",
    "LLMConfig",
    "TopicAgent",
    "LiteratureAgent",
    "ThesisAgent",
    "OutlineAgent",
    "DraftWriterAgent",
    "EditorAgent",
    "ReviewerAgent",
]