"""统计学问答系统 - 智能路由、论文搜索、报告生成"""
from .base_qa_agent import BaseQAAgent, QuestionType, RoutingDecision
from .query_router import QueryRouter
from .paper_search import PaperSearchAgent, Paper, SearchResult
from .report_generator import ReportGenerator, PaperReport, ReportSection
from .daily_watcher import DailyWatcher, DailyPaperReport
from .weekly_report import WeeklyReportGenerator, WeeklyPaperReport
from .monthly_report import MonthlyReportGenerator, MonthlyPaperReport
from .paper_flash import PaperFlash, FlashType, FlashReport, PaperFlashResult, FlashSubscription
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
    # Citation management
    "CitationManager",
    "Citation",
]