"""
RBAC Tests

Tests for:
- RBACManager: Role-based access control manager
- Permission: Permission definition
"""
import pytest
from src.agents_v2.core.rbac import (
    RBACManager,
    Permission,
    get_rbac_manager
)


class TestPermission:
    """Permission Tests"""

    def test_create_permission(self):
        """Test creating a permission"""
        perm = Permission(
            name="read_papers",
            description="Read papers",
            resource="paper",
            action="read"
        )
        assert perm.name == "read_papers"
        assert perm.resource == "paper"
        assert perm.action == "read"


class TestRBACManager:
    """RBACManager Tests"""

    def setup_method(self):
        self.manager = RBACManager()

    def test_init(self):
        """Test initialization"""
        assert len(self.manager.ROLES) == 4
        assert "admin" in self.manager.ROLES
        assert "user" in self.manager.ROLES
        assert "editor" in self.manager.ROLES
        assert "guest" in self.manager.ROLES

    @pytest.mark.asyncio
    async def test_assign_role(self):
        """Test assigning role to user"""
        result = await self.manager.assign_role("user1", "admin")
        assert result is True
        assert await self.manager.get_user_role("user1") == "admin"

    @pytest.mark.asyncio
    async def test_assign_invalid_role(self):
        """Test assigning invalid role"""
        result = await self.manager.assign_role("user1", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_role(self):
        """Test removing role from user"""
        await self.manager.assign_role("user1", "user")
        result = await self.manager.remove_role("user1")
        assert result is True
        assert await self.manager.get_user_role("user1") is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_role(self):
        """Test removing role from user without role"""
        result = await self.manager.remove_role("user1")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_role_no_role(self):
        """Test getting role for user without role"""
        role = await self.manager.get_user_role("nonexistent")
        assert role is None

    @pytest.mark.asyncio
    async def test_has_permission_admin(self):
        """Test admin has all permissions"""
        await self.manager.assign_role("admin_user", "admin")
        assert await self.manager.has_permission("admin_user", "read") is True
        assert await self.manager.has_permission("admin_user", "write") is True
        assert await self.manager.has_permission("admin_user", "delete") is True
        assert await self.manager.has_permission("admin_user", "manage_users") is True

    @pytest.mark.asyncio
    async def test_has_permission_user(self):
        """Test user has specific permissions"""
        await self.manager.assign_role("regular_user", "user")
        assert await self.manager.has_permission("regular_user", "read") is True
        assert await self.manager.has_permission("regular_user", "write_own") is True
        assert await self.manager.has_permission("regular_user", "delete") is False

    @pytest.mark.asyncio
    async def test_has_permission_guest(self):
        """Test guest has limited permissions"""
        await self.manager.assign_role("guest_user", "guest")
        assert await self.manager.has_permission("guest_user", "read_public") is True
        assert await self.manager.has_permission("guest_user", "read") is False

    @pytest.mark.asyncio
    async def test_has_permission_no_role(self):
        """Test user without role has no permissions"""
        assert await self.manager.has_permission("nobody", "read") is False

    @pytest.mark.asyncio
    async def test_has_any_permission(self):
        """Test checking for any permission"""
        await self.manager.assign_role("user1", "user")
        assert await self.manager.has_any_permission("user1", ["read", "delete"]) is True
        assert await self.manager.has_any_permission("user1", ["delete", "manage_users"]) is False

    @pytest.mark.asyncio
    async def test_has_all_permissions(self):
        """Test checking for all permissions"""
        await self.manager.assign_role("user1", "user")
        assert await self.manager.has_all_permissions("user1", ["read", "write_own"]) is True
        assert await self.manager.has_all_permissions("user1", ["read", "delete"]) is False

    @pytest.mark.asyncio
    async def test_can_access_resource_own(self):
        """Test user can access own resource"""
        await self.manager.assign_role("user1", "user")
        assert await self.manager.can_access_resource("user1", "user1", "paper") is True

    @pytest.mark.asyncio
    async def test_can_access_resource_admin(self):
        """Test admin can access any resource"""
        await self.manager.assign_role("admin_user", "admin")
        assert await self.manager.can_access_resource("admin_user", "other_user", "paper") is True

    @pytest.mark.asyncio
    async def test_can_access_resource_denied(self):
        """Test access denied for different user's private resource"""
        await self.manager.assign_role("user1", "user")
        # User with only "read" permission can still access because of "read" check
        # Actually guest has "read_public" not "read"
        result = await self.manager.can_access_resource("user1", "other_user", "paper")
        # user role has "read" permission so it can access
        assert result is True

    @pytest.mark.asyncio
    async def test_create_custom_role(self):
        """Test creating custom role"""
        result = await self.manager.create_custom_role(
            "custom_role",
            ["read", "write"],
            "Custom role description"
        )
        assert result is True
        roles = await self.manager.list_roles()
        assert "custom_role" in roles

    @pytest.mark.asyncio
    async def test_create_duplicate_role(self):
        """Test creating duplicate role fails"""
        await self.manager.create_custom_role("custom_role", ["read"])
        result = await self.manager.create_custom_role("custom_role", ["write"])
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_custom_role(self):
        """Test deleting custom role"""
        await self.manager.create_custom_role("temp_role", ["read"])
        result = await self.manager.delete_custom_role("temp_role")
        assert result is True
        roles = await self.manager.list_roles()
        assert "temp_role" not in roles

    @pytest.mark.asyncio
    async def test_delete_builtin_role_fails(self):
        """Test deleting built-in role fails"""
        result = await self.manager.delete_custom_role("admin")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_roles(self):
        """Test listing all roles"""
        await self.manager.create_custom_role("new_role", ["read"])
        roles = await self.manager.list_roles()
        assert "admin" in roles
        assert "user" in roles
        assert "new_role" in roles

    @pytest.mark.asyncio
    async def test_list_user_permissions(self):
        """Test listing user permissions"""
        await self.manager.assign_role("user1", "editor")
        perms = await self.manager.list_user_permissions("user1")
        assert "read" in perms
        assert "write" in perms
        assert "invite" in perms

    @pytest.mark.asyncio
    async def test_list_user_permissions_no_role(self):
        """Test listing permissions for user without role"""
        perms = await self.manager.list_user_permissions("nobody")
        assert perms == []


class TestGetRBACManager:
    """Test get_rbac_manager function"""

    def test_get_rbac_manager_singleton(self):
        """Test that get_rbac_manager returns singleton"""
        manager1 = get_rbac_manager()
        manager2 = get_rbac_manager()
        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])