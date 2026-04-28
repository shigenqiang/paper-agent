"""定时调度器 - 定时生成报告并推送"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import croniter

from ..qa import (
    DailyWatcher,
    WeeklyReportGenerator,
    MonthlyReportGenerator,
    PaperFlash,
    FlashType
)
from .subscription_manager import (
    SubscriptionManager,
    ReportSubscription,
    get_subscription_manager
)

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """调度类型"""
    CRON = "cron"           # Cron表达式
    INTERVAL = "interval"    # 间隔调度
    ONCE = "once"           # 单次调度


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    name: str
    task_type: str  # daily_report, weekly_report, monthly_report, flash
    schedule_type: ScheduleType
    schedule: str    # cron表达式或间隔秒数
    keywords: List[str]
    subscription_id: Optional[str]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0


class ReportScheduler:
    """
    报告调度器

    功能：
    - 管理定时任务
    - 执行报告生成
    - 跟踪任务状态
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task_handle: Optional[asyncio.Task] = None
        self._subscription_manager = get_subscription_manager()

        # 报告生成器
        self._daily_watcher = DailyWatcher()
        self._weekly_generator = WeeklyReportGenerator()
        self._monthly_generator = MonthlyReportGenerator()
        self._paper_flash = PaperFlash()

    def create_task(
        self,
        name: str,
        task_type: str,
        schedule: str,
        keywords: List[str],
        schedule_type: ScheduleType = ScheduleType.CRON,
        subscription_id: Optional[str] = None
    ) -> ScheduledTask:
        """创建调度任务"""
        import uuid
        task_id = str(uuid.uuid4())[:8]

        task = ScheduledTask(
            task_id=task_id,
            name=name,
            task_type=task_type,
            schedule_type=schedule_type,
            schedule=schedule,
            keywords=keywords,
            subscription_id=subscription_id
        )

        # 计算下次执行时间
        task.next_run = self._calculate_next_run(schedule, schedule_type)

        self._tasks[task_id] = task
        logger.info(f"创建调度任务: {task_id} ({name}), 类型: {task_type}")
        return task

    def _calculate_next_run(
        self,
        schedule: str,
        schedule_type: ScheduleType
    ) -> Optional[datetime]:
        """计算下次执行时间"""
        try:
            if schedule_type == ScheduleType.CRON:
                cron = croniter.croniter(schedule, datetime.now())
                return cron.get_next(datetime)
            elif schedule_type == ScheduleType.INTERVAL:
                seconds = int(schedule)
                return datetime.now() + timedelta(seconds=seconds)
            else:
                return None
        except Exception as e:
            logger.error(f"计算下次执行时间失败: {e}")
            return None

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[ScheduledTask]:
        """列出所有任务"""
        return list(self._tasks.values())

    def list_enabled_tasks(self) -> List[ScheduledTask]:
        """列出所有启用任务"""
        return [t for t in self._tasks.values() if t.enabled]

    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        task = self._tasks.get(task_id)
        if task:
            task.enabled = True
            task.next_run = self._calculate_next_run(task.schedule, task.schedule_type)
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        task = self._tasks.get(task_id)
        if task:
            task.enabled = False
            task.next_run = None
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        task = self._tasks.pop(task_id, None)
        return task is not None

    async def execute_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """执行单个任务"""
        logger.info(f"执行任务: {task.task_id} ({task.name})")
        start_time = datetime.now()

        try:
            result = await self._run_report(task)
            task.last_run = start_time
            task.next_run = self._calculate_next_run(task.schedule, task.schedule_type)
            task.run_count += 1
            task.success_count += 1

            return {
                "success": True,
                "task_id": task.task_id,
                "task_type": task.task_type,
                "result": result,
                "duration": (datetime.now() - start_time).total_seconds()
            }

        except Exception as e:
            task.failure_count += 1
            logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")
            return {
                "success": False,
                "task_id": task.task_id,
                "error": str(e),
                "duration": (datetime.now() - start_time).total_seconds()
            }

    async def _run_report(self, task: ScheduledTask) -> Dict[str, Any]:
        """运行报告生成"""
        keywords = task.keywords

        if task.task_type == "daily_report":
            return await self._daily_watcher.execute(keywords=keywords)
        elif task.task_type == "weekly_report":
            return await self._weekly_generator.execute(keywords=keywords)
        elif task.task_type == "monthly_report":
            return await self._monthly_generator.execute(keywords=keywords)
        elif task.task_type == "flash_hot":
            return await self._paper_flash.execute(
                flash_type=FlashType.HOT,
                topic=keywords[0] if keywords else "machine learning"
            )
        elif task.task_type == "flash_trending":
            return await self._paper_flash.execute(
                flash_type=FlashType.TRENDING,
                topic=keywords[0] if keywords else "machine learning"
            )
        elif task.task_type == "flash_conference":
            return await self._paper_flash.execute(
                flash_type=FlashType.CONFERENCE,
                topic=keywords[0] if keywords else "machine learning"
            )
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

    async def run_scheduler(self, check_interval: int = 60):
        """
        运行调度器

        Args:
            check_interval: 检查间隔（秒）
        """
        self._running = True
        logger.info("调度器启动")

        while self._running:
            try:
                now = datetime.now()
                due_tasks = [
                    task for task in self.list_enabled_tasks()
                    if task.next_run and task.next_run <= now
                ]

                for task in due_tasks:
                    asyncio.create_task(self.execute_task(task))

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"调度器错误: {e}")
                await asyncio.sleep(check_interval)

    def stop_scheduler(self):
        """停止调度器"""
        self._running = False
        logger.info("调度器停止")

    def start_background(self, check_interval: int = 60):
        """后台启动调度器"""
        self._task_handle = asyncio.create_task(self.run_scheduler(check_interval))

    def create_tasks_from_subscriptions(self) -> int:
        """从订阅创建调度任务"""
        subscriptions = self._subscription_manager.get_active_subscriptions()
        created = 0

        for sub in subscriptions:
            task_type_map = {
                "daily": "daily_report",
                "weekly": "weekly_report",
                "monthly": "monthly_report",
                "flash": "flash_hot"
            }

            task_type = task_type_map.get(sub.subscription_type)
            if not task_type:
                continue

            # 确定调度表达式
            schedule_map = {
                "daily": "0 8 * * *",      # 每天8点
                "weekly": "0 9 * * 1",    # 每周一9点
                "monthly": "0 10 1 * *"   # 每月1号10点
            }
            schedule = schedule_map.get(sub.subscription_type, "0 8 * * *")

            self.create_task(
                name=f"Task for subscription {sub.subscription_id}",
                task_type=task_type,
                schedule=schedule,
                keywords=sub.keywords,
                subscription_id=sub.subscription_id
            )
            created += 1

        return created

    def get_statistics(self) -> Dict[str, Any]:
        """获取调度统计"""
        tasks = list(self._tasks.values())
        enabled = len([t for t in tasks if t.enabled])

        total_runs = sum(t.run_count for t in tasks)
        total_success = sum(t.success_count for t in tasks)
        total_failure = sum(t.failure_count for t in tasks)

        return {
            "total_tasks": len(tasks),
            "enabled_tasks": enabled,
            "disabled_tasks": len(tasks) - enabled,
            "total_runs": total_runs,
            "total_success": total_success,
            "total_failure": total_failure,
            "success_rate": total_success / total_runs if total_runs > 0 else 0
        }


# 全局调度器实例
_global_scheduler: Optional[ReportScheduler] = None


def get_report_scheduler() -> ReportScheduler:
    """获取全局调度器"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = ReportScheduler()
    return _global_scheduler
