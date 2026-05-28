"""指标收集器"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MetricRecord(BaseModel):
    """指标记录"""
    metric_name: str
    value: float | int | str | bool
    unit: str | None = None
    service: str | None = None
    operation: str | None = None
    project_id: str | None = None
    request_id: str | None = None
    task_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class MetricsCollector:
    """本地指标收集器"""

    def __init__(self):
        self._records: list[MetricRecord] = []

    def record(
        self,
        metric_name: str,
        value: float | int | str | bool,
        unit: str | None = None,
        service: str | None = None,
        operation: str | None = None,
        project_id: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> MetricRecord:
        """记录一个指标"""
        from src.agents_v3.research_workspace.logging_utils import get_context
        ctx = get_context()

        rec = MetricRecord(
            metric_name=metric_name,
            value=value,
            unit=unit,
            service=service,
            operation=operation,
            project_id=project_id or ctx.get("project_id"),
            request_id=ctx.get("request_id"),
            task_id=ctx.get("task_id"),
            tags=tags or {},
        )
        self._records.append(rec)
        return rec

    def get_records(
        self, metric_name: str | None = None, service: str | None = None
    ) -> list[MetricRecord]:
        """获取指标记录"""
        records = self._records
        if metric_name:
            records = [r for r in records if r.metric_name == metric_name]
        if service:
            records = [r for r in records if r.service == service]
        return records

    def summarize(self, metric_name: str) -> dict[str, Any]:
        """汇总某个指标"""
        values = [
            r.value for r in self._records
            if r.metric_name == metric_name and isinstance(r.value, (int, float))
        ]
        if not values:
            return {"metric_name": metric_name, "count": 0}
        return {
            "metric_name": metric_name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values),
        }

    def summarize_all(self) -> dict[str, dict[str, Any]]:
        """汇总所有指标"""
        names = {r.metric_name for r in self._records}
        return {name: self.summarize(name) for name in sorted(names)}

    def clear(self) -> None:
        self._records.clear()

    def write_jsonl(self, path: str | Path) -> None:
        """写入 JSONL 文件"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for rec in self._records:
                f.write(rec.model_dump_json() + "\n")


# 全局单例
_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
