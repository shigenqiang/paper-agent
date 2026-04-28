"""
调度器模块 单元测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.agents_v2.scheduler import (
    SubscriptionManager,
    ReportSubscription,
    get_subscription_manager,
    ReportScheduler,
    ScheduleType,
    ScheduledTask,
    get_report_scheduler
)


class TestReportSubscription:
    """ReportSubscription 测试"""

    def test_create_subscription(self):
        """测试创建订阅"""
        sub = ReportSubscription(
            subscription_id="sub_001",
            user_id="user_001",
            subscription_type="daily",
            keywords=["machine learning", "deep learning"],
            sources=["arxiv", "pubmed"],
            channels=["email"],
            output_format="markdown"
        )
        assert sub.subscription_id == "sub_001"
        assert sub.enabled is True
        assert "machine learning" in sub.keywords

    def test_to_dict(self):
        """测试转换为字典"""
        sub = ReportSubscription(
            subscription_id="sub_002",
            user_id="user_002",
            subscription_type="weekly",
            keywords=["NLP"]
        )
        data = sub.to_dict()
        assert data["subscription_id"] == "sub_002"
        assert data["subscription_type"] == "weekly"
        assert "NLP" in data["keywords"]

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "subscription_id": "sub_003",
            "user_id": "user_003",
            "subscription_type": "monthly",
            "keywords": ["causal inference"],
            "sources": ["arxiv"],
            "channels": ["slack"],
            "output_format": "json",
            "enabled": True
        }
        sub = ReportSubscription.from_dict(data)
        assert sub.subscription_id == "sub_003"
        assert sub.channels == ["slack"]
        assert sub.output_format == "json"

    def test_default_values(self):
        """测试默认值"""
        sub = ReportSubscription(
            subscription_id="sub_004",
            user_id="user_004",
            subscription_type="daily",
            keywords=[]
        )
        assert sub.sources == []  # 默认空列表
        assert sub.channels == []  # 默认空列表
        assert sub.output_format == "markdown"
        assert sub.enabled is True


class TestSubscriptionManager:
    """SubscriptionManager 测试"""

    def setup_method(self):
        self.manager = SubscriptionManager()

    def test_create_subscription(self):
        """测试创建订阅"""
        sub = self.manager.create_subscription(
            user_id="user_001",
            subscription_type="daily",
            keywords=["ML", "DL"]
        )
        assert sub.user_id == "user_001"
        assert sub.subscription_type == "daily"
        assert len(sub.subscription_id) > 0

    def test_get_subscription(self):
        """测试获取订阅"""
        created = self.manager.create_subscription(
            user_id="user_002",
            subscription_type="weekly",
            keywords=["NLP"]
        )
        retrieved = self.manager.get_subscription(created.subscription_id)
        assert retrieved is not None
        assert retrieved.subscription_id == created.subscription_id

    def test_get_user_subscriptions(self):
        """测试获取用户订阅"""
        self.manager.create_subscription("user_003", "daily", ["ML"])
        self.manager.create_subscription("user_003", "weekly", ["NLP"])

        subs = self.manager.get_user_subscriptions("user_003")
        assert len(subs) == 2

    def test_update_subscription(self):
        """测试更新订阅"""
        sub = self.manager.create_subscription(
            user_id="user_004",
            subscription_type="daily",
            keywords=["ML"]
        )
        updated = self.manager.update_subscription(
            sub.subscription_id,
            keywords=["updated ML"]
        )
        assert updated is not None
        assert "updated ML" in updated.keywords

    def test_delete_subscription(self):
        """测试删除订阅"""
        sub = self.manager.create_subscription(
            user_id="user_005",
            subscription_type="daily",
            keywords=["ML"]
        )
        result = self.manager.delete_subscription(sub.subscription_id)
        assert result is True
        assert self.manager.get_subscription(sub.subscription_id) is None

    def test_enable_disable_subscription(self):
        """测试启用/禁用订阅"""
        sub = self.manager.create_subscription(
            user_id="user_006",
            subscription_type="daily",
            keywords=["ML"]
        )
        self.manager.disable_subscription(sub.subscription_id)
        disabled = self.manager.get_subscription(sub.subscription_id)
        assert disabled.enabled is False

        self.manager.enable_subscription(sub.subscription_id)
        enabled = self.manager.get_subscription(sub.subscription_id)
        assert enabled.enabled is True

    def test_get_active_subscriptions(self):
        """测试获取活跃订阅"""
        sub1 = self.manager.create_subscription("user_007", "daily", ["ML"])
        sub2 = self.manager.create_subscription("user_008", "weekly", ["NLP"])
        self.manager.disable_subscription(sub1.subscription_id)

        active = self.manager.get_active_subscriptions()
        assert len(active) == 1
        assert active[0].subscription_id == sub2.subscription_id

    def test_get_statistics(self):
        """测试获取统计"""
        self.manager.create_subscription("user_009", "daily", ["ML"])
        self.manager.create_subscription("user_010", "weekly", ["NLP"])
        self.manager.create_subscription("user_011", "monthly", ["CV"])

        stats = self.manager.get_statistics()
        assert stats["total_subscriptions"] == 3
        assert stats["active_subscriptions"] == 3
        assert "daily" in stats["by_type"]
        assert "weekly" in stats["by_type"]


class TestScheduleType:
    """ScheduleType 枚举测试"""

    def test_schedule_types(self):
        """测试调度类型"""
        assert ScheduleType.CRON.value == "cron"
        assert ScheduleType.INTERVAL.value == "interval"
        assert ScheduleType.ONCE.value == "once"


class TestScheduledTask:
    """ScheduledTask 测试"""

    def test_create_task(self):
        """测试创建任务"""
        task = ScheduledTask(
            task_id="task_001",
            name="Daily Report",
            task_type="daily_report",
            schedule_type=ScheduleType.CRON,
            schedule="0 8 * * *",
            keywords=["ML"],
            subscription_id="sub_001"
        )
        assert task.task_id == "task_001"
        assert task.enabled is True
        assert task.run_count == 0

    def test_task_with_next_run(self):
        """测试任务下次执行时间"""
        task = ScheduledTask(
            task_id="task_002",
            name="Weekly Report",
            task_type="weekly_report",
            schedule_type=ScheduleType.CRON,
            schedule="0 9 * * 1",
            keywords=["NLP"],
            subscription_id=None,
            next_run=datetime.now() + timedelta(days=1)
        )
        assert task.next_run is not None
        assert task.next_run > datetime.now()


class TestReportScheduler:
    """ReportScheduler 测试"""

    def setup_method(self):
        self.scheduler = ReportScheduler()

    def test_create_task(self):
        """测试创建任务"""
        task = self.scheduler.create_task(
            name="Test Daily",
            task_type="daily_report",
            schedule="0 8 * * *",
            keywords=["machine learning"]
        )
        assert task.name == "Test Daily"
        assert task.task_type == "daily_report"
        assert len(task.task_id) > 0

    def test_get_task(self):
        """测试获取任务"""
        created = self.scheduler.create_task(
            name="Test Weekly",
            task_type="weekly_report",
            schedule="0 9 * * 1",
            keywords=["NLP"]
        )
        retrieved = self.scheduler.get_task(created.task_id)
        assert retrieved is not None
        assert retrieved.task_id == created.task_id

    def test_enable_disable_task(self):
        """测试启用/禁用任务"""
        task = self.scheduler.create_task(
            name="Test Monthly",
            task_type="monthly_report",
            schedule="0 10 1 * *",
            keywords=["CV"]
        )
        self.scheduler.disable_task(task.task_id)
        disabled = self.scheduler.get_task(task.task_id)
        assert disabled.enabled is False
        assert disabled.next_run is None

    def test_delete_task(self):
        """测试删除任务"""
        task = self.scheduler.create_task(
            name="To Delete",
            task_type="flash_hot",
            schedule="0 10 * * *",
            keywords=["ML"]
        )
        result = self.scheduler.delete_task(task.task_id)
        assert result is True
        assert self.scheduler.get_task(task.task_id) is None

    def test_list_tasks(self):
        """测试列出任务"""
        self.scheduler.create_task("Task 1", "daily_report", "0 8 * * *", ["ML"])
        self.scheduler.create_task("Task 2", "weekly_report", "0 9 * * 1", ["NLP"])

        tasks = self.scheduler.list_tasks()
        assert len(tasks) == 2

    def test_get_statistics(self):
        """测试获取统计"""
        self.scheduler.create_task("T1", "daily_report", "0 8 * * *", ["ML"])
        self.scheduler.create_task("T2", "flash_hot", "0 10 * * *", ["DL"])

        stats = self.scheduler.get_statistics()
        assert stats["total_tasks"] == 2
        assert stats["enabled_tasks"] == 2

    @pytest.mark.asyncio
    async def test_execute_task_dry_run(self):
        """测试任务执行（干跑）"""
        task = self.scheduler.create_task(
            name="Dry Run Task",
            task_type="daily_report",
            schedule="0 8 * * *",
            keywords=["test"]
        )
        # 注意：这个测试需要mock实际的API调用
        # 这里只测试任务创建和结构


class TestGlobalInstances:
    """全局实例测试"""

    def test_get_subscription_manager_singleton(self):
        """测试订阅管理器单例"""
        mgr1 = get_subscription_manager()
        mgr2 = get_subscription_manager()
        assert mgr1 is mgr2

    def test_get_report_scheduler_singleton(self):
        """测试调度器单例"""
        sched1 = get_report_scheduler()
        sched2 = get_report_scheduler()
        assert sched1 is sched2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
