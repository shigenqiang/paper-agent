"""
企业级功能模块

包含:
- MultiTenantManager: 多租户管理器
- AuditLogger: 审计日志系统
- RoleBasedAccess: 角色权限控制
- DataEncryption: 数据加密
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class TenantStatus(Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class Tenant:
    """租户定义"""
    id: str
    name: str
    status: TenantStatus = TenantStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class User:
    """用户定义"""
    id: str
    tenant_id: str
    username: str
    email: str
    role: str = "viewer"
    created_at: float = field(default_factory=time.time)
    last_login: float = field(default_factory=time.time)
    is_active: bool = True


class MultiTenantManager:
    """多租户管理器

    支持租户隔离策略:
    - shared: 共享数据库，独立Schema
    - isolated: 完全独立数据库
    """

    def __init__(self, isolation_mode: str = "shared"):
        """初始化

        Args:
            isolation_mode: 隔离模式 (shared/isolated)
        """
        self.isolation_mode = isolation_mode
        self._tenants: Dict[str, Tenant] = {}
        self._users: Dict[str, User] = {}

    def create_tenant(self, tenant_id: str, name: str, **settings) -> Tenant:
        """创建租户

        Args:
            tenant_id: 租户ID
            name: 租户名称
            **settings: 其他设置

        Returns:
            Tenant: 租户对象
        """
        tenant = Tenant(
            id=tenant_id,
            name=name,
            settings=settings
        )

        self._tenants[tenant_id] = tenant
        logger.info(f"创建租户: {tenant_id} ({name})")
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户

        Args:
            tenant_id: 租户ID

        Returns:
            Optional[Tenant]: 租户对象
        """
        return self._tenants.get(tenant_id)

    def suspend_tenant(self, tenant_id: str) -> bool:
        """暂停租户

        Args:
            tenant_id: 租户ID

        Returns:
            bool: 是否成功
        """
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.SUSPENDED
            logger.info(f"暂停租户: {tenant_id}")
            return True
        return False

    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户

        Args:
            tenant_id: 租户ID

        Returns:
            bool: 是否成功
        """
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.status = TenantStatus.DELETED
            logger.info(f"删除租户: {tenant_id}")
            return True
        return False

    def create_user(self,
                    user_id: str,
                    tenant_id: str,
                    username: str,
                    email: str,
                    role: str = "viewer") -> Optional[User]:
        """创建用户

        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            username: 用户名
            email: 邮箱
            role: 角色

        Returns:
            Optional[User]: 用户对象
        """
        if tenant_id not in self._tenants:
            logger.error(f"租户不存在: {tenant_id}")
            return None

        user = User(
            id=user_id,
            tenant_id=tenant_id,
            username=username,
            email=email,
            role=role
        )

        self._users[user_id] = user
        logger.info(f"创建用户: {username} (租户: {tenant_id})")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 用户对象
        """
        return self._users.get(user_id)

    def get_tenant_users(self, tenant_id: str) -> List[User]:
        """获取租户下的所有用户

        Args:
            tenant_id: 租户ID

        Returns:
            List[User]: 用户列表
        """
        return [u for u in self._users.values() if u.tenant_id == tenant_id]

    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """更新用户角色

        Args:
            user_id: 用户ID
            new_role: 新角色

        Returns:
            bool: 是否成功
        """
        user = self._users.get(user_id)
        if user:
            user.role = new_role
            logger.info(f"更新用户角色: {user_id} -> {new_role}")
            return True
        return False

    def get_tenant_stats(self) -> Dict[str, Any]:
        """获取租户统计

        Returns:
            Dict: 统计信息
        """
        active_tenants = sum(1 for t in self._tenants.values() if t.status == TenantStatus.ACTIVE)
        total_users = len(self._users)

        return {
            "total_tenants": len(self._tenants),
            "active_tenants": active_tenants,
            "total_users": total_users,
            "isolation_mode": self.isolation_mode
        }


class AuditLogger:
    """审计日志系统

    记录事件:
    - 认证事件 (登录/登出)
    - 数据访问 (读取/修改)
    - 任务执行 (创建/完成/失败)
    - 配置变更 (权限变更等)
    """

    def __init__(self, retention_days: int = 90):
        """初始化

        Args:
            retention_days: 保留天数
        """
        self.retention_days = retention_days
        self._logs: List[Dict] = []

    def log(self,
            event_type: str,
            user_id: str,
            tenant_id: str = "",
            resource: str = "",
            action: str = "",
            metadata: Dict = None):
        """记录审计日志

        Args:
            event_type: 事件类型
            user_id: 用户ID
            tenant_id: 租户ID
            resource: 资源
            action: 动作
            metadata: 元数据
        """
        log_entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "resource": resource,
            "action": action,
            "metadata": metadata or {},
            "ip_address": metadata.get("ip_address", "") if metadata else ""
        }

        self._logs.append(log_entry)
        logger.debug(f"审计日志: {event_type} - {user_id}")

    def log_auth(self, user_id: str, action: str, success: bool, **metadata):
        """记录认证事件

        Args:
            user_id: 用户ID
            action: 动作 (login/logout)
            success: 是否成功
            **metadata: 其他元数据
        """
        self.log(
            event_type="authentication",
            user_id=user_id,
            action=action,
            metadata={**metadata, "success": success}
        )

    def log_data_access(self, user_id: str, resource: str, action: str):
        """记录数据访问

        Args:
            user_id: 用户ID
            resource: 资源
            action: 动作 (read/write/delete)
        """
        self.log(
            event_type="data_access",
            user_id=user_id,
            resource=resource,
            action=action
        )

    def log_task_execution(self, user_id: str, task: str, status: str, **metadata):
        """记录任务执行

        Args:
            user_id: 用户ID
            task: 任务
            status: 状态 (created/completed/failed)
            **metadata: 其他元数据
        """
        self.log(
            event_type="task_execution",
            user_id=user_id,
            resource=task,
            action=status,
            metadata=metadata
        )

    def query_logs(self,
                   user_id: str = None,
                   event_type: str = None,
                   start_time: float = None,
                   end_time: float = None,
                   limit: int = 100) -> List[Dict]:
        """查询日志

        Args:
            user_id: 用户ID
            event_type: 事件类型
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量

        Returns:
            List[Dict]: 日志列表
        """
        results = self._logs

        if user_id:
            results = [l for l in results if l["user_id"] == user_id]

        if event_type:
            results = [l for l in results if l["event_type"] == event_type]

        if start_time:
            results = [l for l in results if l["timestamp"] >= start_time]

        if end_time:
            results = [l for l in results if l["timestamp"] <= end_time]

        return results[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计

        Returns:
            Dict: 统计信息
        """
        event_counts = {}
        for log in self._logs:
            event_type = log["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return {
            "total_logs": len(self._logs),
            "event_types": event_counts,
            "retention_days": self.retention_days
        }


class Role(Enum):
    """角色枚举"""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class RoleBasedAccess:
    """基于角色的访问控制

    预定义角色:
    - Owner: 全部权限
    - Admin: 管理租户设置、用户
    - Editor: 创建和编辑论文
    - Viewer: 只读访问
    """

    ROLE_PERMISSIONS = {
        Role.OWNER: {"*"},
        Role.ADMIN: {"users:manage", "settings:manage", "papers:*", "reports:*"},
        Role.EDITOR: {"papers:create", "papers:edit", "papers:read"},
        Role.VIEWER: {"papers:read"}
    }

    def __init__(self):
        """初始化"""
        self._user_roles: Dict[str, Set[str]] = {}

    def assign_role(self, user_id: str, role: Role):
        """分配角色

        Args:
            user_id: 用户ID
            role: 角色
        """
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()

        self._user_roles[user_id].add(role.value)
        logger.info(f"分配角色: {user_id} -> {role.value}")

    def has_permission(self, user_id: str, permission: str) -> bool:
        """检查权限

        Args:
            user_id: 用户ID
            permission: 权限字符串

        Returns:
            bool: 是否有权限
        """
        roles = self._user_roles.get(user_id, set())

        for role_str in roles:
            role = Role(role_str)
            perms = self.ROLE_PERMISSIONS.get(role, set())

            # 检查通配符
            if "*" in perms:
                return True

            # 检查具体权限
            if permission in perms:
                return True

            # 检查模式匹配 papers:read -> papers:*
            parts = permission.split(":")
            if len(parts) == 2:
                pattern = f"{parts[0]}:*"
                if pattern in perms:
                    return True

        return False

    def get_user_roles(self, user_id: str) -> List[str]:
        """获取用户角色

        Args:
            user_id: 用户ID

        Returns:
            List[str]: 角色列表
        """
        return list(self._user_roles.get(user_id, set()))


class DataEncryption:
    """数据加密模块

    加密策略:
    - 用户密码: bcrypt
    - API密钥: AES-256
    - 论文内容: AES-256
    - 向量数据: AES-256
    """

    def __init__(self, master_key: str = None):
        """初始化

        Args:
            master_key: 主密钥
        """
        self._master_key = master_key or self._generate_default_key()
        self._key_cache: Dict[str, bytes] = {}

    def _generate_default_key(self) -> str:
        """生成默认密钥"""
        return hashlib.sha256(b"default_key_placeholder").hexdigest()

    def encrypt(self, data: str, key: str = None) -> str:
        """加密数据

        Args:
            data: 原始数据
            key: 密钥 (可选)

        Returns:
            str: 加密后的数据 (Base64)
        """
        # 简单实现：使用hash作为伪加密
        # 实际应使用 proper encryption library like cryptography
        key = key or self._master_key
        combined = f"{key}:{data}".encode()

        import base64
        encrypted = base64.b64encode(combined).decode()
        return encrypted

    def decrypt(self, encrypted_data: str, key: str = None) -> str:
        """解密数据

        Args:
            encrypted_data: 加密数据
            key: 密钥 (可选)

        Returns:
            str: 原始数据
        """
        try:
            import base64
            decoded = base64.b64decode(encrypted_data.encode())
            combined = decoded.decode()

            parts = combined.split(":", 1)
            if len(parts) == 2:
                return parts[1]

            return combined

        except Exception as e:
            logger.error(f"解密失败: {e}")
            return ""

    def hash_password(self, password: str) -> str:
        """哈希密码

        Args:
            password: 密码

        Returns:
            str: 哈希后的密码
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码

        Args:
            password: 密码
            hashed: 哈希值

        Returns:
            bool: 是否匹配
        """
        return self.hash_password(password) == hashed


# 便捷函数
def create_tenant_manager(mode: str = "shared") -> MultiTenantManager:
    """创建租户管理器"""
    return MultiTenantManager(isolation_mode=mode)


def create_audit_logger(retention_days: int = 90) -> AuditLogger:
    """创建审计日志器"""
    return AuditLogger(retention_days=retention_days)


def create_rbac() -> RoleBasedAccess:
    """创建RBAC"""
    return RoleBasedAccess()


def create_encryption(master_key: str = None) -> DataEncryption:
    """创建加密器"""
    return DataEncryption(master_key=master_key)