"""
RBAC - 基于角色的访问控制

实现权限管理、用户角色分配和权限检查
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Permission:
    """权限定义"""
    name: str
    description: str
    resource: str
    action: str


class RBACManager:
    """基于角色的访问控制管理器"""

    # 预定义角色和权限
    ROLES = {
        "admin": {
            "permissions": ["read", "write", "delete", "manage_users", "manage_settings"],
            "description": "Administrator with full access"
        },
        "editor": {
            "permissions": ["read", "write", "invite"],
            "description": "Editor who can edit papers and invite collaborators"
        },
        "user": {
            "permissions": ["read", "write_own"],
            "description": "Regular user who can read and write own papers"
        },
        "guest": {
            "permissions": ["read_public"],
            "description": "Guest who can only read public papers"
        }
    }

    def __init__(self):
        self.user_roles: Dict[str, str] = {}  # user_id -> role
        self.custom_roles: Dict[str, Dict] = {}  # custom role name -> config
        self.role_permissions: Dict[str, List[str]] = {
            role: data["permissions"] for role, data in self.ROLES.items()
        }

    async def assign_role(self, user_id: str, role: str) -> bool:
        """分配角色给用户"""
        if role not in self.ROLES and role not in self.custom_roles:
            return False
        self.user_roles[user_id] = role
        return True

    async def remove_role(self, user_id: str) -> bool:
        """移除用户角色"""
        if user_id in self.user_roles:
            del self.user_roles[user_id]
            return True
        return False

    async def get_user_role(self, user_id: str) -> Optional[str]:
        """获取用户角色"""
        return self.user_roles.get(user_id)

    async def has_permission(self, user_id: str, permission: str) -> bool:
        """检查用户是否有指定权限"""
        role = self.user_roles.get(user_id)
        if not role:
            return False

        permissions = self.role_permissions.get(role, [])
        return permission in permissions

    async def has_any_permission(self, user_id: str, permissions: List[str]) -> bool:
        """检查用户是否有任一指定权限"""
        for perm in permissions:
            if await self.has_permission(user_id, perm):
                return True
        return False

    async def has_all_permissions(self, user_id: str, permissions: List[str]) -> bool:
        """检查用户是否有所有指定权限"""
        for perm in permissions:
            if not await self.has_permission(user_id, perm):
                return False
        return True

    async def can_access_resource(self, user_id: str, resource_owner: str, resource: str) -> bool:
        """
        检查用户是否可以访问资源

        Args:
            user_id: 用户ID
            resource_owner: 资源所有者ID
            resource: 资源类型 (paper, user, etc.)
        """
        # Admin can access everything
        if await self.has_permission(user_id, "manage_users"):
            return True

        # Users can access their own resources
        if user_id == resource_owner:
            return True

        # Check specific resource permissions
        if resource == "paper":
            if await self.has_permission(user_id, "read"):
                return True

        return False

    async def create_custom_role(self, role_name: str, permissions: List[str], description: str = "") -> bool:
        """创建自定义角色"""
        if role_name in self.ROLES or role_name in self.custom_roles:
            return False
        self.custom_roles[role_name] = {
            "permissions": permissions,
            "description": description
        }
        self.role_permissions[role_name] = permissions
        return True

    async def delete_custom_role(self, role_name: str) -> bool:
        """删除自定义角色"""
        if role_name not in self.custom_roles:
            return False
        del self.custom_roles[role_name]
        del self.role_permissions[role_name]
        return True

    async def list_roles(self) -> Dict[str, Dict]:
        """列出所有角色"""
        return {
            **self.ROLES,
            **self.custom_roles
        }

    async def list_user_permissions(self, user_id: str) -> List[str]:
        """列出用户的所有权限"""
        role = self.user_roles.get(user_id)
        if not role:
            return []
        return self.role_permissions.get(role, [])


# 全局RBAC管理器
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """获取全局RBAC管理器"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager
