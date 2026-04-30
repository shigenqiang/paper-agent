"""
安全模块 - 安全加固

提供:
1. InputSanitizer: 输入清理
2. SecretManager: 敏感信息管理
3. SecurityAudit: 安全审计
4. PermissionChecker: 权限检查
5. 安全配置
"""
import re
import html
import hashlib
import hmac
import time
import json
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """审计事件类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    API_ACCESS = "api_access"
    DATA_ACCESS = "data_access"
    DATA_MODIFY = "data_modify"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"
    SECURITY_VIOLATION = "security_violation"
    AGENT_EXECUTION = "agent_execution"
    TOOL_EXECUTION = "tool_execution"
    FILE_ACCESS = "file_access"
    ERROR = "error"


class AuditSeverity(str, Enum):
    """审计事件严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""
    event_type: AuditEventType
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    session_id: str = ""
    ip_address: str = ""
    user_agent: str = ""
    action: str = ""
    resource: str = ""
    result: str = "success"  # success, failure, denied
    severity: AuditSeverity = AuditSeverity.INFO
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            content = f"{self.event_type.value}:{self.timestamp}:{self.action}"
            self.event_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "severity": self.severity.value,
            "metadata": self.metadata
        }


class SecurityAudit:
    """
    安全审计系统

    功能:
    - 审计事件记录
    - 审计日志查询
    - 安全合规报告
    - 异常行为检测
    """

    def __init__(self, retention_days: int = 90):
        self.retention_days = retention_days
        self._events: List[AuditEvent] = []
        self._max_events = 100000
        self._user_activity: Dict[str, List[AuditEvent]] = defaultdict(list)
        self._ip_activity: Dict[str, List[AuditEvent]] = defaultdict(list)

    def record(self, event: AuditEvent):
        """记录审计事件"""
        self._events.append(event)

        # 索引
        if event.user_id:
            self._user_activity[event.user_id].append(event)
        if event.ip_address:
            self._ip_activity[event.ip_address].append(event)

        # 定期清理
        if len(self._events) > self._max_events:
            self._cleanup_old_events()

    def _cleanup_old_events(self):
        """清理过期事件"""
        cutoff = time.time() - (self.retention_days * 86400)
        self._events = [e for e in self._events if e.timestamp > cutoff]

    def get_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """查询审计事件"""
        results = self._events

        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]

    def check_anomalies(self, user_id: str) -> List[Dict[str, Any]]:
        """检测用户异常行为"""
        anomalies = []
        events = self._user_activity.get(user_id, [])

        if not events:
            return anomalies

        # 检查频繁失败
        failures = [e for e in events if e.result == "failure"]
        if len(failures) > 5:
            anomalies.append({
                "type": "frequent_failures",
                "severity": AuditSeverity.WARNING,
                "message": f"User {user_id} has {len(failures)} failed attempts"
            })

        # 检查异常IP地址
        unique_ips = set(e.ip_address for e in events)
        if len(unique_ips) > 3:
            anomalies.append({
                "type": "multiple_ips",
                "severity": AuditSeverity.WARNING,
                "message": f"User {user_id} accessed from {len(unique_ips)} different IPs"
            })

        # 检查敏感操作
        sensitive_events = [
            e for e in events
            if e.event_type in (AuditEventType.CONFIG_CHANGE, AuditEventType.PERMISSION_CHANGE)
        ]
        if len(sensitive_events) > 10:
            anomalies.append({
                "type": "excessive_sensitive_ops",
                "severity": AuditSeverity.ERROR,
                "message": f"User {user_id} performed {len(sensitive_events)} sensitive operations"
            })

        return anomalies

    def generate_report(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """生成安全审计报告"""
        events = self.get_events(start_time=start_time, end_time=end_time, limit=10000)

        # 统计
        event_counts = defaultdict(int)
        user_counts = defaultdict(int)
        result_counts = defaultdict(int)
        severity_counts = defaultdict(int)

        for event in events:
            event_counts[event.event_type.value] += 1
            if event.user_id:
                user_counts[event.user_id] += 1
            result_counts[event.result] += 1
            severity_counts[event.severity.value] += 1

        return {
            "period": {
                "start": datetime.fromtimestamp(start_time).isoformat(),
                "end": datetime.fromtimestamp(end_time).isoformat()
            },
            "summary": {
                "total_events": len(events),
                "unique_users": len(user_counts),
                "event_types": dict(event_counts),
                "results": dict(result_counts),
                "severities": dict(severity_counts)
            },
            "top_users": sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "critical_events": [
                e.to_dict() for e in events
                if e.severity == AuditSeverity.CRITICAL
            ][:10]
        }

    def verify_integrity(self, data: str, signature: str, key: str) -> bool:
        """验证数据完整性"""
        expected = hmac.new(
            key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


class PermissionChecker:
    """
    权限检查器

    功能:
    - 基于角色的访问控制 (RBAC)
    - 资源级别权限
    - 权限验证
    """

    # 预定义角色权限
    ROLE_PERMISSIONS = {
        "admin": {
            "*"  # 所有权限
        },
        "user": {
            "agent:execute",
            "agent:read",
            "tool:execute",
            "tool:read",
            "memory:read",
            "memory:write"
        },
        "readonly": {
            "agent:read",
            "tool:read",
            "memory:read"
        },
        "guest": {
            "agent:read"
        }
    }

    def __init__(self):
        self._user_roles: Dict[str, Set[str]] = {}
        self._user_resources: Dict[str, Set[str]] = {}

    def assign_role(self, user_id: str, role: str):
        """为用户分配角色"""
        if role not in self.ROLE_PERMISSIONS:
            raise ValueError(f"Unknown role: {role}")

        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()

        # 展开角色到实际权限
        permissions = self.ROLE_PERMISSIONS[role]
        for perm in permissions:
            self._user_roles[user_id].add(perm)

    def grant_permission(self, user_id: str, permission: str):
        """授予用户特定权限"""
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        self._user_roles[user_id].add(permission)

    def revoke_permission(self, user_id: str, permission: str):
        """撤销用户特定权限"""
        if user_id in self._user_roles:
            self._user_roles[user_id].discard(permission)

    def check_permission(self, user_id: str, permission: str) -> bool:
        """检查用户是否有指定权限"""
        if user_id not in self._user_roles:
            return False

        user_permissions = self._user_roles[user_id]

        # 检查通配符
        if "*" in user_permissions:
            return True

        return permission in user_permissions

    def check_resource_access(self, user_id: str, resource: str, action: str) -> bool:
        """检查用户对资源的访问权限"""
        # 格式: resource:action
        permission = f"{resource}:{action}"
        return self.check_permission(user_id, permission)

    def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户所有权限"""
        if user_id not in self._user_roles:
            return set()

        return self._user_roles[user_id].copy()


class InputSanitizer:
    """
    输入清理器 - 防止XSS、注入等攻击

    使用方式:
        sanitizer = InputSanitizer()
        clean_input = sanitizer.sanitize(user_input)
    """

    # HTML标签黑名单
    DANGEROUS_TAGS = [
        "script", "iframe", "object", "embed", "form",
        "input", "button", "select", "textarea"
    ]

    # 危险事件属性
    DANGEROUS_ATTRS = [
        "onerror", "onload", "onclick", "onmouseover",
        "onfocus", "onblur", "onchange", "onsubmit"
    ]

    def __init__(self, allow_html: bool = False):
        self.allow_html = allow_html

    def sanitize(self, text: str) -> str:
        """
        清理输入文本

        Args:
            text: 原始输入

        Returns:
            清理后的文本
        """
        if not text:
            return ""

        # 基础清理
        text = self._remove_null_bytes(text)
        text = self._normalize_whitespace(text)

        if self.allow_html:
            text = self._sanitize_html(text)
        else:
            text = self._escape_html(text)

        # 移除潜在危险字符序列
        text = self._remove_dangerous_patterns(text)

        return text.strip()

    def _remove_null_bytes(self, text: str) -> str:
        """移除空字节"""
        return text.replace("\x00", "").replace("\0", "")

    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        text = re.sub(r"[\t\n\r]+", " ", text)
        text = re.sub(r" +", " ", text)
        return text

    def _escape_html(self, text: str) -> str:
        """转义HTML"""
        return html.escape(text, quote=True)

    def _sanitize_html(self, text: str) -> str:
        """清理HTML（保留部分标签）"""
        # 允许的标签白名单
        allowed_tags = ["p", "br", "strong", "em", "u", "ol", "ul", "li", "h1", "h2", "h3"]

        # 1. 先移除危险标签（不使用转义）
        for tag in self.DANGEROUS_TAGS:
            text = re.sub(f"<{tag}[^>]*>.*?</{tag}>", "", text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(f"<{tag}[^>]*/?>", "", text, flags=re.IGNORECASE)

        # 2. 移除危险属性（只移除属性，不处理标签内容）
        for attr in self.DANGEROUS_ATTRS:
            # 匹配 onxxx="..." 或 onxxx='...'
            text = re.sub(r'\s+' + attr + r'="[^"]*"', "", text, flags=re.IGNORECASE)
            text = re.sub(r'\s+' + attr + r"='[^']*'", "", text, flags=re.IGNORECASE)

        # 3. 转义任何剩余的危险标签（如果标签不在白名单中）
        # 先找出所有标签
        tag_pattern = re.compile(r'<(\w+)([^>]*)>([^<]*)</\1>', re.IGNORECASE | re.DOTALL)
        def escape_tag(match):
            tag_name = match.group(1).lower()
            attrs = match.group(2)
            content = match.group(3)
            if tag_name not in allowed_tags:
                # 危险标签，整个转义
                return html.escape(match.group(0))
            return match.group(0)

        # 转义不在白名单的标签及其内容
        text = tag_pattern.sub(escape_tag, text)

        # 4. 对单独的危险标签（自闭合）也做处理
        for tag in self.DANGEROUS_TAGS:
            text = re.sub(f"<{tag}[^>]*/?>", "", text, flags=re.IGNORECASE)

        return text

    def _remove_dangerous_patterns(self, text: str) -> str:
        """移除危险模式"""
        dangerous_patterns = [
            r"javascript:",
            r"vbscript:",
            r"data:text/html",
            r"<[^\s]*[\s\S]*?feed[\s\S]*?>",
            r"[\s\S]*?eval\s*\(",
            r"[\s\S]*?document\.cookie",
            r"[\s\S]*?document\.write",
        ]

        for pattern in dangerous_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理字典中的所有字符串值"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [self.sanitize(v) if isinstance(v, str) else v for v in value]
            else:
                sanitized[key] = value
        return sanitized


class SecretManager:
    """
    敏感信息管理

    使用方式:
        secrets = SecretManager()
        secrets.set("OPENAI_API_KEY", "sk-xxx")
        api_key = secrets.get("OPENAI_API_KEY")  # 从环境变量或存储获取
    """

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._env_prefix = "PAPER_AGENT_"

    def set(self, key: str, value: str):
        """设置密钥"""
        self._secrets[key] = value

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取密钥（优先从环境变量）"""
        # 先检查环境变量
        env_key = f"{self._env_prefix}{key}"
        import os
        env_value = os.environ.get(env_key) or os.environ.get(key)
        if env_value:
            return env_value

        # 回退到内存存储
        return self._secrets.get(key, default)

    def get_or_raise(self, key: str) -> str:
        """获取密钥，不存在则抛出异常"""
        value = self.get(key)
        if not value:
            from .exceptions import ConfigurationError
            raise ConfigurationError(f"Required secret not found: {key}")
        return value

    def clear(self):
        """清空所有密钥"""
        self._secrets.clear()


class SecurityConfig:
    """安全配置"""

    def __init__(
        self,
        sanitize_input: bool = True,
        allow_html: bool = False,
        max_input_length: int = 10000,
        rate_limit: int = 100,
        rate_window: int = 60
    ):
        self.sanitize_input = sanitize_input
        self.allow_html = allow_html
        self.max_input_length = max_input_length
        self.rate_limit = rate_limit  # 每窗口最大请求数
        self.rate_window = rate_window  # 窗口大小（秒）


# 全局实例
_secrets = SecretManager()


def get_secrets() -> SecretManager:
    """获取全局密钥管理器"""
    return _secrets


def sanitize_input(text: str, sanitizer: Optional[InputSanitizer] = None) -> str:
    """快捷输入清理函数"""
    if sanitizer is None:
        sanitizer = InputSanitizer()
    return sanitizer.sanitize(text)
