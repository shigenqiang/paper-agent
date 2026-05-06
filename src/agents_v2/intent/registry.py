"""
意图识别列表 - Intent Recognition Registry

定义所有意图类型、工作流路径和功能模块的映射关系。
用于智能路由和系统集成。

使用方式：
    from src.agents_v2.intent.registry import INTENT_REGISTRY

    # 根据意图获取对应的工作流
    route = INTENT_REGISTRY.get_workflow("literature_search")
"""

from typing import Dict, List, Optional, Callable
from enum import Enum


class IntentCategory(str, Enum):
    """意图分类"""
    SEARCH = "search"           # 搜索类
    WRITING = "writing"          # 写作类
    DIAGNOSTIC = "diagnostic"    # 诊断类
    REPORT = "report"            # 报告类
    QA = "qa"                    # 问答类
    MODIFICATION = "modification"  # 修改类
    OTHER = "other"              # 其他


class WorkflowPath(str, Enum):
    """工作流路径"""
    SEARCH = "search"            # 搜索工作流
    WRITING = "writing"          # 写作工作流
    REPORT = "report"            # 报告工作流
    QA = "qa"                    # 问答工作流
    REVISION = "revision"        # 修改工作流


# ============ 意图定义 ============

INTENTS = {
    # === 搜索类意图 ===
    "search_papers": {
        "category": IntentCategory.SEARCH,
        "workflow": WorkflowPath.SEARCH,
        "description": "搜索学术论文",
        "keywords": ["搜索论文", "找论文", "search papers", "找相关文章"],
        "agents": ["ArxivSearcher", "PubmedSearcher", "OpenAlexSearcher"],
        "nodes": ["crawler", "selector"],
    },
    "search_topic": {
        "category": IntentCategory.SEARCH,
        "workflow": WorkflowPath.SEARCH,
        "description": "搜索研究主题",
        "keywords": ["搜索主题", "研究主题", "topic search"],
        "agents": ["OpenAlexSearcher", "SemanticScholarSearcher"],
        "nodes": ["crawler", "selector"],
    },
    "search_keyword": {
        "category": IntentCategory.SEARCH,
        "workflow": WorkflowPath.SEARCH,
        "description": "关键词搜索",
        "keywords": ["关键词搜索", "keyword search"],
        "agents": ["BaseSearcher"],
        "nodes": ["crawler"],
    },
    "literature_search": {
        "category": IntentCategory.SEARCH,
        "workflow": WorkflowPath.WRITING,  # 文献搜索是写作流程的一部分
        "description": "文献搜索与调研",
        "keywords": ["文献搜索", "literature search", "找文献", "搜文献"],
        "agents": ["LiteratureAgent", "ArxivSearcher", "PubmedSearcher"],
        "nodes": ["literature"],  # 使用literature节点
    },

    # === 写作类意图 ===
    "write_paper": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "完整论文写作",
        "keywords": ["写论文", "生成论文", "write paper", "论文写作"],
        "agents": ["WriterAgent", "OutlineAgent"],
        "nodes": ["diagnostic", "topic", "literature", "methodology", "outline", "writing", "review"],
    },
    "write_outline": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "生成论文大纲",
        "keywords": ["写大纲", "生成大纲", "outline"],
        "agents": ["OutlineAgent"],
        "nodes": ["outline"],
    },
    "write_section": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "撰写论文章节",
        "keywords": ["写章节", "section"],
        "agents": ["WriterAgent"],
        "nodes": ["writing"],
    },
    "write_abstract": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "撰写摘要",
        "keywords": ["写摘要", "abstract"],
        "agents": ["WriterAgent"],
        "nodes": ["writing"],
    },

    # === 诊断类意图 ===
    "diagnostic": {
        "category": IntentCategory.DIAGNOSTIC,
        "workflow": WorkflowPath.WRITING,  # 诊断是写作流程的开始
        "description": "问题诊断",
        "keywords": ["诊断", "diagnostic"],
        "agents": ["DiagnosticNode"],
        "nodes": ["diagnostic"],
    },
    "diagnostic_topic": {
        "category": IntentCategory.DIAGNOSTIC,
        "workflow": WorkflowPath.WRITING,
        "description": "选题诊断",
        "keywords": ["选题诊断", "topic diagnostic"],
        "agents": ["DiagnosticNode"],
        "nodes": ["diagnostic"],
    },
    "diagnostic_literature": {
        "category": IntentCategory.DIAGNOSTIC,
        "workflow": WorkflowPath.WRITING,
        "description": "文献诊断",
        "keywords": ["文献诊断", "literature diagnostic"],
        "agents": ["DiagnosticNode"],
        "nodes": ["diagnostic"],
    },

    # === 选题相关意图 ===
    "topic_select": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "选题选择",
        "keywords": ["选题", "选择主题", "topic select"],
        "agents": ["TopicNode"],
        "nodes": ["topic"],
    },
    "thesis_formulate": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "论题制定",
        "keywords": ["论题", "thesis", " formulate"],
        "agents": ["TopicNode"],
        "nodes": ["topic"],
    },
    "outline_generate": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "大纲生成",
        "keywords": ["大纲", "outline", "生成"],
        "agents": ["OutlineAgent"],
        "nodes": ["outline"],
    },
    "draft_write": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "草稿写作",
        "keywords": ["草稿", "draft", "写作"],
        "agents": ["WriterAgent"],
        "nodes": ["writing"],
    },
    "full_paper": {
        "category": IntentCategory.WRITING,
        "workflow": WorkflowPath.WRITING,
        "description": "完整论文生成",
        "keywords": ["完整论文", "full paper", "生成论文"],
        "agents": ["WriterAgent", "ReviewerAgent"],
        "nodes": ["diagnostic", "topic", "literature", "methodology", "outline", "writing", "review", "polish"],
    },

    # === 报告类意图 ===
    "literature_review": {
        "category": IntentCategory.REPORT,
        "workflow": WorkflowPath.REPORT,
        "description": "文献综述",
        "keywords": ["文献综述", "literature review", "综述"],
        "agents": ["ReportGenerator", "LiteratureAgent"],
        "nodes": ["report_crawl", "report_analyze", "report_gen"],
    },
    "report_generate": {
        "category": IntentCategory.REPORT,
        "workflow": WorkflowPath.REPORT,
        "description": "生成报告",
        "keywords": ["生成报告", "report", "报告生成"],
        "agents": ["ReportGenerator", "DailyWatcher", "WeeklyReportGenerator", "MonthlyReportGenerator"],
        "nodes": ["report_crawl", "report_analyze", "report_gen"],
    },
    "report_summarize": {
        "category": IntentCategory.REPORT,
        "workflow": WorkflowPath.REPORT,
        "description": "总结报告",
        "keywords": ["总结报告", "summarize"],
        "agents": ["ReportGenerator"],
        "nodes": ["report_analyze", "report_gen"],
    },

    # === 问答类意图 ===
    "question_answer": {
        "category": IntentCategory.QA,
        "workflow": WorkflowPath.QA,
        "description": "问答系统",
        "keywords": ["问答", "question", "answer", "回答问题"],
        "agents": ["QASearchNode", "QASynthesizeNode", "QAAnswerNode"],
        "nodes": ["qa_search", "qa_synthesize", "qa_answer"],
    },

    # === 修改类意图 ===
    "revise": {
        "category": IntentCategory.MODIFICATION,
        "workflow": WorkflowPath.REVISION,
        "description": "修改论文",
        "keywords": ["修改", "revise", "修订"],
        "agents": ["ReviseNode"],
        "nodes": ["revise"],
    },
    "polish": {
        "category": IntentCategory.MODIFICATION,
        "workflow": WorkflowPath.REVISION,
        "description": "润色论文",
        "keywords": ["润色", "polish", "打磨"],
        "agents": ["PolishNode"],
        "nodes": ["polish"],
    },
    "refine": {
        "category": IntentCategory.MODIFICATION,
        "workflow": WorkflowPath.REVISION,
        "description": "精炼内容",
        "keywords": ["精炼", "refine", "优化"],
        "agents": ["RefineNode"],
        "nodes": ["refine"],
    },

    # === 其他意图 ===
    "summary": {
        "category": IntentCategory.OTHER,
        "workflow": WorkflowPath.SEARCH,
        "description": "总结摘要",
        "keywords": ["总结", "summary"],
        "agents": [],
        "nodes": [],
    },
    "translation": {
        "category": IntentCategory.OTHER,
        "workflow": WorkflowPath.SEARCH,
        "description": "翻译功能",
        "keywords": ["翻译", "translation"],
        "agents": [],
        "nodes": [],
    },
    "unknown": {
        "category": IntentCategory.OTHER,
        "workflow": WorkflowPath.SEARCH,
        "description": "未知意图",
        "keywords": [],
        "agents": [],
        "nodes": [],
    },
    "general": {
        "category": IntentCategory.OTHER,
        "workflow": WorkflowPath.SEARCH,
        "description": "一般查询",
        "keywords": ["查询", "general"],
        "agents": [],
        "nodes": [],
    },
}


# ============ 功能模块映射 ============

MODULE_REGISTRY = {
    # 搜索模块
    "search": {
        "path": "src.agents_v2.search",
        "description": "学术论文搜索",
        "capabilities": [
            "多源搜索(arXiv/PubMed/OpenAlex/Semantic Scholar)",
            "结果去重合并",
            "频率限制管理",
            "搜索缓存",
            "查询解析",
        ],
        "main_classes": [
            "ArxivSearcher",
            "PubmedSearcher",
            "OpenAlexSearcher",
            "SemanticScholarSearcher",
            "SearchOrchestrator",
            "SearchFactory",
        ],
    },

    # 论文搜索模块（兼容旧模块）
    "paper_search": {
        "path": "src.agents_v2.paper_search",
        "description": "论文搜索与报告生成（旧模块，保持兼容）",
        "capabilities": [
            "论文搜索",
            "报告生成（日报/周报/月报）",
            "引用管理",
            "快讯服务",
        ],
        "main_classes": [
            "PaperSearchAgent",
            "ReportGenerator",
            "DailyWatcher",
            "WeeklyReportGenerator",
            "MonthlyReportGenerator",
            "PaperFlash",
            "CitationManager",
        ],
        "deprecated": True,
        "replacement": "src.agents_v2.search + src.agents_v2.reports + src.agents_v2.citation",
    },

    # 报告模块
    "reports": {
        "path": "src.agents_v2.reports",
        "description": "统一报告生成",
        "capabilities": [
            "日报生成",
            "周报生成",
            "月报生成",
            "通用报告生成",
        ],
        "main_classes": [
            "DailyReportGenerator",
            "WeeklyReportGenerator",
            "MonthlyReportGenerator",
            "BaseReportGenerator",
        ],
    },

    # 引用模块
    "citation": {
        "path": "src.agents_v2.citation",
        "description": "引用管理与格式化",
        "capabilities": [
            "参考文献格式化（APA/MLA/Chicago/IEEE/GB7714）",
            "DOI验证",
            "引用提取引用溯源",
        ],
        "main_classes": [
            "CitationFormatter",
            "DOIVerifier",
            "CitationExtractor",
            "CitationTracker",
        ],
    },

    # 意图分类模块
    "intent": {
        "path": "src.agents_v2.intent",
        "description": "意图识别与分类",
        "capabilities": [
            "意图类型枚举",
            "意图分类（LLMIntentClassifier）",
            "路由决策",
        ],
        "main_classes": [
            "IntentType",
        ],
    },

    # 路由模块
    "routing": {
        "path": "src.agents_v2.routing",
        "description": "智能路由",
        "capabilities": [
            "LLM意图分类",
            "Agent路由",
            "查询解析",
        ],
        "main_classes": [
            "LLMIntentClassifier",
            "IntentRouter",
        ],
    },

    # LangGraph统一工作流
    "unified_workflow": {
        "path": "src.agents_v2.langgraph_workflow.unified_workflow",
        "description": "LangGraph统一工作流",
        "capabilities": [
            "搜索工作流（crawl → select）",
            "写作工作流（diagnostic → topic → literature → methodology → outline → writing → review → polish）",
            "报告工作流（report_crawl → report_analyze → report_gen）",
            "问答工作流（qa_search → qa_synthesize → qa_answer）",
            "修改工作流（revise → refine → polish）",
            "HITL人机协作",
            "记忆节点",
            "知识图谱节点",
            "多模态节点",
        ],
        "main_classes": [
            "UnifiedWorkflow",
        ],
    },
}


# ============ 工作流节点定义 ============

WORKFLOW_NODES = {
    # === 核心节点 ===
    "router": {
        "description": "路由节点",
        "workflows": [WorkflowPath.SEARCH, WorkflowPath.WRITING, WorkflowPath.REPORT, WorkflowPath.QA, WorkflowPath.REVISION],
        "input": ["user_query"],
        "output": ["intent", "route_path", "intent_confidence"],
    },
    "diagnostic": {
        "description": "诊断节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["user_query"],
        "output": ["diagnostic_result", "problems", "severity"],
    },
    "topic": {
        "description": "选题节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["user_query", "diagnostic_result"],
        "output": ["topic", "research_direction"],
    },
    "literature": {
        "description": "文献节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["topic"],
        "output": ["papers", "selected_papers", "literature_review"],
    },
    "methodology": {
        "description": "方法论节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["topic", "selected_papers"],
        "output": ["methodology", "research_design"],
    },
    "outline": {
        "description": "大纲节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["topic", "methodology", "selected_papers"],
        "output": ["outline"],
    },
    "writing": {
        "description": "写作节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["outline", "selected_papers", "methodology"],
        "output": ["draft", "sections"],
    },
    "review": {
        "description": "审查节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["draft"],
        "output": ["feedback", "review_result"],
    },
    "evaluator": {
        "description": "评估节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["draft", "feedback"],
        "output": ["quality_score", "evaluation_result"],
    },
    "polish": {
        "description": "润色节点",
        "workflows": [WorkflowPath.REVISION, WorkflowPath.WRITING],
        "input": ["draft"],
        "output": ["polished_draft"],
    },

    # === 搜索节点 ===
    "crawler": {
        "description": "爬虫节点",
        "workflows": [WorkflowPath.SEARCH],
        "input": ["user_query"],
        "output": ["papers", "search_results"],
    },
    "selector": {
        "description": "选择器节点",
        "workflows": [WorkflowPath.SEARCH],
        "input": ["papers", "search_results"],
        "output": ["selected_papers"],
    },

    # === 报告节点 ===
    "report_crawl": {
        "description": "报告爬虫节点",
        "workflows": [WorkflowPath.REPORT],
        "input": ["keywords", "report_type"],
        "output": ["collected_data"],
    },
    "report_analyze": {
        "description": "报告分析节点",
        "workflows": [WorkflowPath.REPORT],
        "input": ["collected_data"],
        "output": ["analysis_result"],
    },
    "report_gen": {
        "description": "报告生成节点",
        "workflows": [WorkflowPath.REPORT],
        "input": ["analysis_result", "report_type"],
        "output": ["report"],
    },

    # === QA节点 ===
    "qa_search": {
        "description": "问答搜索节点",
        "workflows": [WorkflowPath.QA],
        "input": ["user_query"],
        "output": ["qa_contexts", "relevant_docs"],
    },
    "qa_synthesize": {
        "description": "问答综合节点",
        "workflows": [WorkflowPath.QA],
        "input": ["qa_contexts", "relevant_docs"],
        "output": ["synthesized_answer"],
    },
    "qa_answer": {
        "description": "问答回答节点",
        "workflows": [WorkflowPath.QA],
        "input": ["user_query", "synthesized_answer"],
        "output": ["answer", "sources"],
    },

    # === 修改节点 ===
    "revise": {
        "description": "修改节点",
        "workflows": [WorkflowPath.REVISION],
        "input": ["draft", "feedback"],
        "output": ["revised_draft"],
    },
    "refine": {
        "description": "精炼节点",
        "workflows": [WorkflowPath.REVISION],
        "input": ["revised_draft"],
        "output": ["refined_draft"],
    },

    # === 扩展节点 ===
    "memory_recall": {
        "description": "记忆召回节点",
        "workflows": [WorkflowPath.SEARCH, WorkflowPath.WRITING],
        "input": ["user_query"],
        "output": ["remembered_context"],
    },
    "memory_remember": {
        "description": "记忆存储节点",
        "workflows": [WorkflowPath.SEARCH, WorkflowPath.WRITING],
        "input": ["final_result"],
        "output": [],
    },
    "multimodal": {
        "description": "多模态分析节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["papers", "draft"],
        "output": ["multimodal_analysis"],
    },
    "kg": {
        "description": "知识图谱节点",
        "workflows": [WorkflowPath.WRITING],
        "input": ["selected_papers", "topic"],
        "output": ["knowledge_graph"],
    },
}


# ============ 意图识别注册表 ============

class IntentRegistry:
    """意图识别注册表"""

    @staticmethod
    def get_intent_info(intent_name: str) -> Optional[Dict]:
        """获取意图信息"""
        return INTENTS.get(intent_name)

    @staticmethod
    def get_workflow(intent_name: str) -> Optional[WorkflowPath]:
        """根据意图获取工作流路径"""
        info = INTENTS.get(intent_name)
        return info.get("workflow") if info else None

    @staticmethod
    def get_category(intent_name: str) -> Optional[IntentCategory]:
        """根据意图获取分类"""
        info = INTENTS.get(intent_name)
        return info.get("category") if info else None

    @staticmethod
    def get_nodes_for_intent(intent_name: str) -> List[str]:
        """获取意图对应的节点列表"""
        info = INTENTS.get(intent_name)
        return info.get("nodes", []) if info else []

    @staticmethod
    def list_intents_by_category(category: IntentCategory) -> List[str]:
        """列出指定分类的所有意图"""
        return [
            name for name, info in INTENTS.items()
            if info.get("category") == category
        ]

    @staticmethod
    def list_intents_by_workflow(workflow: WorkflowPath) -> List[str]:
        """列出指定工作流的所有意图"""
        return [
            name for name, info in INTENTS.items()
            if info.get("workflow") == workflow
        ]

    @staticmethod
    def get_module_for_intent(intent_name: str) -> Optional[str]:
        """获取意图对应的主要模块"""
        info = INTENTS.get(intent_name)
        if not info:
            return None
        nodes = info.get("nodes", [])
        if not nodes:
            return None
        # 返回第一个节点对应的模块
        first_node = nodes[0]
        if first_node in ["crawler", "selector"]:
            return "search"
        elif first_node in ["literature"]:
            return "search"
        elif first_node in ["report_crawl", "report_analyze", "report_gen"]:
            return "reports"
        elif first_node in ["qa_search", "qa_synthesize", "qa_answer"]:
            return "academic_qa"
        elif first_node in ["revise", "refine", "polish"]:
            return "modification"
        elif first_node in ["diagnostic"]:
            return "diagnostic"
        elif first_node in ["topic"]:
            return "topic"
        elif first_node in ["outline", "writing", "review", "polish", "evaluator"]:
            return "writing"
        return "unknown"


# 全局注册表实例
INTENT_REGISTRY = IntentRegistry()


# ============ 便捷函数 ============

def get_intent_workflow(intent: str) -> Optional[str]:
    """获取意图对应的工作流路径（字符串）"""
    workflow = IntentRegistry.get_workflow(intent)
    return workflow.value if workflow else None


def list_all_intents() -> List[str]:
    """列出所有意图"""
    return list(INTENTS.keys())


def list_search_intents() -> List[str]:
    """列出搜索类意图"""
    return IntentRegistry.list_intents_by_category(IntentCategory.SEARCH)


def list_writing_intents() -> List[str]:
    """列出写作类意图"""
    return IntentRegistry.list_intents_by_category(IntentCategory.WRITING)


def list_report_intents() -> List[str]:
    """列出报告类意图"""
    return IntentRegistry.list_intents_by_category(IntentCategory.REPORT)


def list_qa_intents() -> List[str]:
    """列出问答类意图"""
    return IntentRegistry.list_intents_by_category(IntentCategory.QA)


# ============ 导出 ============

__all__ = [
    "IntentType",
    "IntentCategory",
    "WorkflowPath",
    "INTENTS",
    "MODULE_REGISTRY",
    "WORKFLOW_NODES",
    "IntentRegistry",
    "INTENT_REGISTRY",
    "get_intent_workflow",
    "list_all_intents",
    "list_search_intents",
    "list_writing_intents",
    "list_report_intents",
    "list_qa_intents",
]