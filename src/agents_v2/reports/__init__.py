"""
统一报告生成模块 - Unified Reports Module

功能：
1. 日报生成
2. 周报生成
3. 月报生成
4. 通用报告生成

使用方式：
    from src.agents_v2.reports import DailyReportGenerator, WeeklyReportGenerator

    daily_gen = DailyReportGenerator()
    report = await daily_gen.generate(topic="AI研究进展")

    weekly_gen = WeeklyReportGenerator()
    report = await weekly_gen.generate(dates=("2024-01-01", "2024-01-07"))
"""

from .base import BaseReportGenerator, ReportConfig, ReportSection, ReportType
from .daily import DailyReportGenerator, generate_daily_report
from .weekly import WeeklyReportGenerator, generate_weekly_report
from .monthly import MonthlyReportGenerator, generate_monthly_report

__all__ = [
    "BaseReportGenerator",
    "ReportConfig",
    "ReportSection",
    "ReportType",
    "DailyReportGenerator",
    "generate_daily_report",
    "WeeklyReportGenerator",
    "generate_weekly_report",
    "MonthlyReportGenerator",
    "generate_monthly_report",
]