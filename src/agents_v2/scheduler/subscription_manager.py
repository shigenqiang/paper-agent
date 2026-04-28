"""订阅管理 - 用户订阅配置和管理"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from ..qa.paper_flash import FlashType

logger = logging.getLogger(__name__)


@dataclass
class ReportSubscription:
    """报告订阅配置"""
    subscription_id: str
    user_id: str
    subscription_type: str  # daily, weekly, monthly, flash
    keywords: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)  # arXiv, PubMed等
    channels: List[str] = field(default_factory=list)  # email, slack, feishu
    output_format: str = "markdown"  # json, markdown, html
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    last_run: Optional[str] = None
    next_run: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "user_id": self.user_id,
            "subscription_type": self.subscription_type,
            "keywords": self.keywords,
            "sources": self.sources,
            "channels": self.channels,
            "output_format": self.output_format,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_run": self.last_run,
            "next_run": self.next_run
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportSubscription":
        return cls(
            subscription_id=data.get("subscription_id", ""),
            user_id=data.get("user_id", ""),
            subscription_type=data.get("subscription_type", "daily"),
            keywords=data.get("keywords", []),
            sources=data.get("sources", ["arxiv", "pubmed"]),
            channels=data.get("channels", ["email"]),
            output_format=data.get("output_format", "markdown"),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            last_run=data.get("last_run"),
            next_run=data.get("next_run")
        )


class SubscriptionManager:
    """
    订阅管理器

    功能：
    - 管理用户订阅配置
    - 生成订阅ID
    - 订阅CRUD操作
    """

    def __init__(self):
        self._subscriptions: Dict[str, ReportSubscription] = {}
        self._user_subscriptions: Dict[str, List[str]] = {}  # user_id -> [subscription_ids]

    def create_subscription(
        self,
        user_id: str,
        subscription_type: str,
        keywords: List[str],
        sources: Optional[List[str]] = None,
        channels: Optional[List[str]] = None,
        output_format: str = "markdown"
    ) -> ReportSubscription:
        """创建新订阅"""
        import uuid
        subscription_id = str(uuid.uuid4())[:8]

        subscription = ReportSubscription(
            subscription_id=subscription_id,
            user_id=user_id,
            subscription_type=subscription_type,
            keywords=keywords,
            sources=sources or ["arxiv", "pubmed"],
            channels=channels or ["email"],
            output_format=output_format
        )

        self._subscriptions[subscription_id] = subscription

        # 更新用户订阅索引
        if user_id not in self._user_subscriptions:
            self._user_subscriptions[user_id] = []
        self._user_subscriptions[user_id].append(subscription_id)

        logger.info(f"创建订阅: {subscription_id} for user: {user_id}")
        return subscription

    def get_subscription(self, subscription_id: str) -> Optional[ReportSubscription]:
        """获取订阅"""
        return self._subscriptions.get(subscription_id)

    def get_user_subscriptions(self, user_id: str) -> List[ReportSubscription]:
        """获取用户的所有订阅"""
        sub_ids = self._user_subscriptions.get(user_id, [])
        return [self._subscriptions[sid] for sid in sub_ids if sid in self._subscriptions]

    def get_active_subscriptions(
        self,
        subscription_type: Optional[str] = None
    ) -> List[ReportSubscription]:
        """获取活跃订阅"""
        active = [sub for sub in self._subscriptions.values() if sub.enabled]
        if subscription_type:
            active = [sub for sub in active if sub.subscription_type == subscription_type]
        return active

    def update_subscription(
        self,
        subscription_id: str,
        **kwargs
    ) -> Optional[ReportSubscription]:
        """更新订阅"""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            return None

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(subscription, key) and value is not None:
                setattr(subscription, key, value)

        subscription.updated_at = datetime.now().isoformat()
        logger.info(f"更新订阅: {subscription_id}")
        return subscription

    def delete_subscription(self, subscription_id: str) -> bool:
        """删除订阅"""
        subscription = self._subscriptions.pop(subscription_id, None)
        if not subscription:
            return False

        # 从用户索引中移除
        user_id = subscription.user_id
        if user_id in self._user_subscriptions:
            self._user_subscriptions[user_id].remove(subscription_id)

        logger.info(f"删除订阅: {subscription_id}")
        return True

    def enable_subscription(self, subscription_id: str) -> bool:
        """启用订阅"""
        sub = self.update_subscription(subscription_id, enabled=True)
        return sub is not None

    def disable_subscription(self, subscription_id: str) -> bool:
        """禁用订阅"""
        sub = self.update_subscription(subscription_id, enabled=False)
        return sub is not None

    def list_all_subscriptions(self) -> List[ReportSubscription]:
        """列出所有订阅"""
        return list(self._subscriptions.values())

    def get_statistics(self) -> Dict[str, Any]:
        """获取订阅统计"""
        total = len(self._subscriptions)
        active = len([s for s in self._subscriptions.values() if s.enabled])

        by_type: Dict[str, int] = {}
        for sub in self._subscriptions.values():
            by_type[sub.subscription_type] = by_type.get(sub.subscription_type, 0) + 1

        by_channel: Dict[str, int] = {}
        for sub in self._subscriptions.values():
            for channel in sub.channels:
                by_channel[channel] = by_channel.get(channel, 0) + 1

        return {
            "total_subscriptions": total,
            "active_subscriptions": active,
            "inactive_subscriptions": total - active,
            "by_type": by_type,
            "by_channel": by_channel
        }

    def export_subscriptions(self) -> str:
        """导出所有订阅为JSON"""
        data = [sub.to_dict() for sub in self._subscriptions.values()]
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_subscriptions(self, json_str: str) -> int:
        """导入订阅"""
        try:
            data = json.loads(json_str)
            count = 0
            for item in data:
                sub = ReportSubscription.from_dict(item)
                self._subscriptions[sub.subscription_id] = sub
                if sub.user_id not in self._user_subscriptions:
                    self._user_subscriptions[sub.user_id] = []
                self._user_subscriptions[sub.user_id].append(sub.subscription_id)
                count += 1
            return count
        except Exception as e:
            logger.error(f"导入订阅失败: {e}")
            return 0


# 全局订阅管理器实例
_global_subscription_manager: Optional[SubscriptionManager] = None


def get_subscription_manager() -> SubscriptionManager:
    """获取全局订阅管理器"""
    global _global_subscription_manager
    if _global_subscription_manager is None:
        _global_subscription_manager = SubscriptionManager()
    return _global_subscription_manager
