"""统计学问答系统 - 智能路由、论文搜索、报告生成"""

# 统一模块导入（推荐）
# 使用 src.agents_v2.citation 和 src.agents_v2.reports 替代以下旧模块
from .citation_manager import CitationManager, Citation as LegacyCitation

# 保持向后兼容的导出
from .base_qa_agent import BaseQAAgent, QuestionType, RoutingDecision
from .query_router import QueryRouter
from .paper_search import PaperSearchAgent, Paper, SearchResult
from .report_generator import ReportGenerator, PaperReport, ReportSection
from .daily_watcher import DailyWatcher, DailyPaperReport
from .weekly_report import WeeklyReportGenerator, WeeklyPaperReport
from .monthly_report import MonthlyReportGenerator, MonthlyPaperReport
from .paper_flash import PaperFlash, FlashType, FlashReport, PaperFlashResult, FlashSubscription

# 引用管理器（保持向后兼容，但推荐使用 src.agents_v2.citation）
from .citation_manager import CitationManager, Citation

__all__ = [
    # Base
    "BaseQAAgent",
    "QuestionType",
    "RoutingDecision",
    # Query routing
    "QueryRouter",
    # Paper search
    "PaperSearchAgent",
    "Paper",
    "SearchResult",
    # Report generation
    "ReportGenerator",
    "PaperReport",
    "ReportSection",
    # Daily watcher
    "DailyWatcher",
    "DailyPaperReport",
    # Weekly report
    "WeeklyReportGenerator",
    "WeeklyPaperReport",
    # Monthly report
    "MonthlyReportGenerator",
    "MonthlyPaperReport",
    # Paper flash
    "PaperFlash",
    "FlashType",
    "FlashReport",
    "PaperFlashResult",
    "FlashSubscription",
    # Citation management (legacy - use src.agents_v2.citation instead)
    "CitationManager",
    "Citation",
    # Legacy alias
    "LegacyCitation",
]