# Reports 模块

> 版本：v1.0
> 更新日期：2026-05-04
> 状态：**已实现**

## 概述

统一报告生成模块，提供日报、周报、月报自动生成功能。

## 目录结构

```
reports/
├── __init__.py       # 统一导出
├── base.py          # 基础生成器
├── daily.py         # 日报生成
├── weekly.py        # 周报生成
└── monthly.py       # 月报生成
```

## 核心功能

### DailyReportGenerator

日报生成，包含：
- 今日摘要
- 重要发现
- 详细分析
- 明日展望

### WeeklyReportGenerator

周报生成，包含：
- 本周概览
- 主要进展
- 论文分析
- 趋势洞察
- 下周计划

### MonthlyReportGenerator

月报生成，包含：
- 月度概览
- 主要成就
- 深度分析
- 趋势与展望
- 下月计划

## 使用示例

```python
from src.agents_v2.reports import DailyReportGenerator, WeeklyReportGenerator, MonthlyReportGenerator, Report, ReportSection

# 周报生成
generator = WeeklyReportGenerator()
report = generator.generate(
    topic="深度学习研究",
    papers=[...],
    dates=("2024-01-01", "2024-01-07")
)
print(report.to_markdown())
```

## Report 结构

```python
class Report:
    title: str
    date_range: tuple
    sections: list[ReportSection]
    metadata: dict

class ReportSection:
    title: str
    content: str
    section_type: str  # summary/analysis/trend/plan
```

## 与旧模块对应

| 旧模块 | 替代模块 | 状态 |
|--------|----------|------|
| `paper_search/report_generator` | `reports/` | 保留 |
| `paper_search/daily_watcher` | `reports/DailyReportGenerator` | 保留 |
| `paper_search/weekly_report` | `reports/WeeklyReportGenerator` | 保留 |
| `paper_search/monthly_report` | `reports/MonthlyReportGenerator` | 保留 |

---

**版本**：v1.0
**更新日期**：2026-05-04