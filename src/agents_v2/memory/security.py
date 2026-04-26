"""
记忆系统安全 - Memory Security

提供:
- MemoryAccessControl: 访问控制
- DataSanitizer: 数据清理
- AuditLogger: 审计日志
"""
import asyncio
import time
import hashlib
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from .types import MemoryType


class Permission(Enum):
    """权限类型"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class AccessRule:
    """访问规则"""
    client_id: str
    memory_types: Set[str]
    permissions: Set[Permission]
    expires_at: Optional[float] = None


@dataclass
class AuditEntry:
    """审计条目"""
    timestamp: float
    client_id: str
    operation: str
    memory_key: str
    memory_type: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)


class MemoryAccessControl:
    """
    记忆访问控制

    职责:
    - 基于客户端的访问控制
    - 权限管理
    - 数据隔离
    """

    def __init__(self):
        self._rules: Dict[str, AccessRule] = {}
        self._default_permissions: Set[Permission] = {Permission.READ, Permission.WRITE}
        self._lock = asyncio.Lock()

    def _is_expired(self, rule: AccessRule) -> bool:
        """检查规则是否过期"""
        if rule.expires_at is None:
            return False
        return time.time() > rule.expires_at

    async def grant_access(
        self,
        client_id: str,
        memory_types: List[str],
        permissions: Optional[List[Permission]] = None,
        expires_at: Optional[float] = None
    ) -> bool:
        """
        授予访问权限

        Args:
            client_id: 客户端ID
            memory_types: 允许的记忆类型
            permissions: 权限列表
            expires_at: 过期时间戳

        Returns:
            是否成功
        """
        async with self._lock:
            perms = set(permissions) if permissions else self._default_permissions.copy()

            self._rules[client_id] = AccessRule(
                client_id=client_id,
                memory_types=set(memory_types),
                permissions=perms,
                expires_at=expires_at
            )

            return True

    async def revoke_access(self, client_id: str, memory_type: Optional[str] = None) -> bool:
        """
        撤销访问权限

        Args:
            client_id: 客户端ID
            memory_type: 可选的记忆类型,None表示全部撤销

        Returns:
            是否成功
        """
        async with self._lock:
            if client_id not in self._rules:
                return False

            if memory_type is None:
                del self._rules[client_id]
            else:
                rule = self._rules[client_id]
                rule.memory_types.discard(memory_type)

            return True

    async def check_access(
        self,
        client_id: str,
        memory_type: str,
        required_permission: Permission = Permission.READ
    ) -> bool:
        """
        检查访问权限

        Args:
            client_id: 客户端ID
            memory_type: 记忆类型
            required_permission: 所需权限

        Returns:
            是否有权限
        """
        async with self._lock:
            rule = self._rules.get(client_id)

            # 没有规则,拒绝访问
            if rule is None:
                return False

            # 检查是否过期
            if self._is_expired(rule):
                return False

            # 检查记忆类型
            if memory_type not in rule.memory_types:
                return False

            # 检查权限
            return required_permission in rule.permissions

    async def get_client_permissions(self, client_id: str) -> Dict[str, Any]:
        """获取客户端权限"""
        rule = self._rules.get(client_id)

        if rule is None:
            return {"has_access": False}

        return {
            "has_access": True,
            "memory_types": list(rule.memory_types),
            "permissions": [p.value for p in rule.permissions],
            "expires_at": rule.expires_at,
            "is_expired": self._is_expired(rule)
        }


class DataSanitizer:
    """
    数据清理器

    职责:
    - 敏感数据脱敏
    - 输入验证
    - 数据清洗
    """

    def __init__(self):
        self._sensitive_patterns = [
            "password",
            "secret",
            "api_key",
            "token",
            "credential"
        ]

    def sanitize_key(self, key: str) -> str:
        """
        清理键

        Args:
            key: 原始键

        Returns:
            清理后的键
        """
        # 移除空白
        key = key.strip()

        # 限制长度
        if len(key) > 256:
            key = key[:256]

        # 只允许字母数字下划线
        import re
        key = re.sub(r'[^a-zA-Z0-9_.-]', '_', key)

        return key

    def sanitize_value(self, value: Any) -> Any:
        """
        清理值

        Args:
            value: 原始值

        Returns:
            清理后的值
        """
        if isinstance(value, str):
            # 限制长度
            if len(value) > 100000:
                value = value[:100000] + "...[truncated]"

        return value

    def contains_sensitive_data(self, data: Dict[str, Any]) -> bool:
        """
        检查是否包含敏感数据

        Args:
            data: 数据字典

        Returns:
            是否包含敏感数据
        """
        data_str = str(data).lower()

        for pattern in self._sensitive_patterns:
            if pattern in data_str:
                return True

        return False

    def mask_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        屏蔽敏感字段

        Args:
            data: 原始数据

        Returns:
            屏蔽后的数据
        """
        masked = data.copy()

        for key in list(masked.keys()):
            key_lower = key.lower()

            for pattern in self._sensitive_patterns:
                if pattern in key_lower:
                    masked[key] = "***REDACTED***"
                    break

        return masked


class AuditLogger:
    """
    审计日志

    职责:
    - 记录所有记忆操作
    - 安全事件追踪
    - 合规性支持
    """

    def __init__(self, access_control: Optional[MemoryAccessControl] = None):
        self._access_control = access_control or MemoryAccessControl()
        self._audit_log: List[AuditEntry] = []
        self._max_entries = 10000

    def log_operation(
        self,
        client_id: str,
        operation: str,
        memory_key: str,
        memory_type: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录操作

        Args:
            client_id: 客户端ID
            operation: 操作类型
            memory_key: 记忆键
            memory_type: 记忆类型
            success: 是否成功
            details: 额外详情
        """
        entry = AuditEntry(
            timestamp=time.time(),
            client_id=client_id,
            operation=operation,
            memory_key=memory_key,
            memory_type=memory_type,
            success=success,
            details=details or {}
        )

        self._audit_log.append(entry)

        if len(self._audit_log) > self._max_entries:
            self._audit_log = self._audit_log[-self._max_entries:]

    def get_audit_trail(
        self,
        client_id: Optional[str] = None,
        since_timestamp: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取审计轨迹

        Args:
            client_id: 可选的客户端过滤
            since_timestamp: 可选的起始时间
            limit: 返回数量

        Returns:
            审计条目列表
        """
        entries = self._audit_log

        if client_id:
            entries = [e for e in entries if e.client_id == client_id]

        if since_timestamp:
            entries = [e for e in entries if e.timestamp >= since_timestamp]

        entries = entries[-limit:]
        entries.reverse()

        return [
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.timestamp)),
                "client_id": e.client_id,
                "operation": e.operation,
                "memory_key": e.memory_key,
                "memory_type": e.memory_type,
                "success": e.success,
                "details": e.details
            }
            for e in entries
        ]

    def get_security_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取安全事件

        Args:
            limit: 返回数量

        Returns:
            安全事件列表
        """
        # 失败的操作视为安全事件
        security_events = [
            {
                "timestamp": e.timestamp,
                "client_id": e.client_id,
                "operation": e.operation,
                "memory_key": e.memory_key,
                "details": e.details
            }
            for e in self._audit_log
            if not e.success
        ]

        security_events = security_events[-limit:]
        security_events.reverse()

        return security_events

    def clear_old_entries(self, before_timestamp: float) -> int:
        """
        清理旧条目

        Args:
            before_timestamp: 清理此时间之前的条目

        Returns:
            删除的条目数
        """
        original_count = len(self._audit_log)
        self._audit_log = [
            e for e in self._audit_log
            if e.timestamp >= before_timestamp
        ]
        return original_count - len(self._audit_log)


class SecurityManager:
    """
    安全管理器

    整合访问控制、数据清理、审计日志
    """

    def __init__(self):
        self.access_control = MemoryAccessControl()
        self.sanitizer = DataSanitizer()
        self.audit_logger = AuditLogger(self.access_control)

    async def check_and_log(
        self,
        client_id: str,
        operation: str,
        memory_key: str,
        memory_type: str,
        check_write: bool = False
    ) -> bool:
        """
        检查权限并记录

        Args:
            client_id: 客户端ID
            operation: 操作类型
            memory_key: 记忆键
            memory_type: 记忆类型
            check_write: 是否检查写权限

        Returns:
            是否有权限
        """
        permission = Permission.WRITE if check_write else Permission.READ
        has_access = await self.access_control.check_access(
            client_id, memory_type, permission
        )

        # 记录到审计日志
        self.audit_logger.log_operation(
            client_id=client_id,
            operation=operation,
            memory_key=memory_key,
            memory_type=memory_type,
            success=has_access
        )

        return has_access

    def sanitize_and_validate(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """
        清理和验证数据

        Args:
            key: 记忆键
            value: 记忆值
            metadata: 元数据

        Returns:
            (清理后的键, 清理后的值, 是否有效)
        """
        sanitized_key = self.sanitizer.sanitize_key(key)
        sanitized_value = self.sanitizer.sanitize_value(value)

        # 检查敏感数据
        has_sensitive = False
        if metadata:
            has_sensitive = self.sanitizer.contains_sensitive_data(metadata)
            if has_sensitive:
                metadata = self.sanitizer.mask_sensitive_fields(metadata)

        return sanitized_key, sanitized_value, metadata, has_sensitive
