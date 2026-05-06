"""
Intent Type 枚举定义

定义所有可能的意图类型，用于路由和分类
"""
from enum import Enum

from .registry import (
    IntentCategory,
    WorkflowPath,
    INTENTS,
    MODULE_REGISTRY,
    WORKFLOW_NODES,
    IntentRegistry,
    INTENT_REGISTRY,
    get_intent_workflow,
    list_all_intents,
    list_search_intents,
    list_writing_intents,
    list_report_intents,
    list_qa_intents,
)


# ============ 意图类型枚举（保持向后兼容） ============

class IntentType(str, Enum):
    """意图类型枚举"""

    # 搜索相关
    SEARCH_PAPERS = "search_papers"          # 搜索论文
    SEARCH_TOPIC = "search_topic"            # 搜索主题
    SEARCH_KEYWORD = "search_keyword"         # 关键词搜索
    LITERATURE_SEARCH = "literature_search"  # 文献搜索

    # 写作相关
    WRITE_PAPER = "write_paper"              # 写论文
    WRITE_OUTLINE = "write_outline"          # 写大纲
    WRITE_SECTION = "write_section"          # 写章节
    WRITE_ABSTRACT = "write_abstract"       # 写摘要

    # 诊断相关
    DIAGNOSTIC = "diagnostic"               # 诊断问题
    DIAGNOSTIC_TOPIC = "diagnostic_topic"    # 选题诊断
    DIAGNOSTIC_LITERATURE = "diagnostic_literature"  # 文献诊断

    # 修改相关
    REVISE = "revise"                        # 修改
    POLISH = "polish"                        # 润色
    REFINE = "refine"                        # 精炼

    # 报告相关
    REPORT_GENERATE = "report_generate"     # 生成报告
    REPORT_SUMMARIZE = "report_summarize"   # 总结报告
    LITERATURE_REVIEW = "literature_review"  # 文献综述

    # 选题相关
    TOPIC_SELECT = "topic_select"           # 选题选择
    THESIS_FORMULATE = "thesis_formulate"   # 论题制定

    # 大纲/写作相关
    OUTLINE_GENERATE = "outline_generate"   # 大纲生成
    DRAFT_WRITE = "draft_write"             # 草稿写作

    # 完整论文
    FULL_PAPER = "full_paper"               # 完整论文

    # 问答相关
    QUESTION_ANSWER = "question_answer"     # 问答

    # 总结/翻译
    SUMMARY = "summary"                     # 总结
    TRANSLATION = "translation"             # 翻译

    # 其他
    UNKNOWN = "unknown"                       # 未知意图
    GENERAL = "general"                      # 一般查询