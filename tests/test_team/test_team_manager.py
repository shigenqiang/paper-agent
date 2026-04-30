"""
团队管理 单元测试
"""
import pytest

from src.agents_v2._archive.team import (
    UserRole,
    TeamRole,
    User,
    Team,
    SharedSubscription,
    TeamDiscussion,
    TeamManager,
    get_team_manager
)


class TestUserRole:
    """UserRole 测试"""

    def test_roles(self):
        """测试角色枚举"""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.MEMBER.value == "member"
        assert UserRole.GUEST.value == "guest"


class TestTeamRole:
    """TeamRole 测试"""

    def test_roles(self):
        """测试角色枚举"""
        assert TeamRole.OWNER.value == "owner"
        assert TeamRole.ADMIN.value == "admin"
        assert TeamRole.MEMBER.value == "member"
        assert TeamRole.VIEWER.value == "viewer"


class TestUser:
    """User 测试"""

    def test_create_user(self):
        """测试创建用户"""
        user = User(
            user_id="user_001",
            username="testuser",
            email="test@example.com"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.MEMBER
        assert len(user.team_ids) == 0


class TestTeam:
    """Team 测试"""

    def test_create_team(self):
        """测试创建团队"""
        team = Team(
            team_id="team_001",
            name="Research Team",
            owner_id="user_001"
        )
        assert team.name == "Research Team"
        assert team.owner_id == "user_001"
        assert "user_001" in team.member_ids


class TestSharedSubscription:
    """SharedSubscription 测试"""

    def test_create(self):
        """测试创建订阅"""
        sub = SharedSubscription(
            subscription_id="sub_001",
            team_id="team_001",
            created_by="user_001",
            keywords=["ML", "DL"],
            channels=["email"],
            frequency="daily"
        )
        assert sub.keywords == ["ML", "DL"]
        assert sub.enabled is True


class TestTeamDiscussion:
    """TeamDiscussion 测试"""

    def test_create(self):
        """测试创建讨论"""
        discussion = TeamDiscussion(
            discussion_id="disc_001",
            team_id="team_001",
            author_id="user_001",
            title="Paper Discussion",
            content="Great paper on ML"
        )
        assert discussion.title == "Paper Discussion"
        assert discussion.paper_id is None


class TestTeamManager:
    """TeamManager 测试"""

    def setup_method(self):
        self.manager = TeamManager()

    # 用户管理测试

    def test_create_user(self):
        """测试创建用户"""
        user = self.manager.create_user("Alice", "alice@example.com")
        assert user.username == "Alice"
        assert user.email == "alice@example.com"
        assert len(user.user_id) > 0

    def test_get_user(self):
        """测试获取用户"""
        created = self.manager.create_user("Bob", "bob@example.com")
        retrieved = self.manager.get_user(created.user_id)
        assert retrieved is not None
        assert retrieved.username == "Bob"

    def test_get_user_by_email(self):
        """测试通过邮箱获取用户"""
        self.manager.create_user("Charlie", "charlie@example.com")
        user = self.manager.get_user_by_email("charlie@example.com")
        assert user is not None
        assert user.username == "Charlie"

    def test_update_user(self):
        """测试更新用户"""
        user = self.manager.create_user("Dave", "dave@example.com")
        updated = self.manager.update_user(user.user_id, username="David")
        assert updated is not None
        assert updated.username == "David"

    def test_delete_user(self):
        """测试删除用户"""
        user = self.manager.create_user("Eve", "eve@example.com")
        result = self.manager.delete_user(user.user_id)
        assert result is True
        assert self.manager.get_user(user.user_id) is None

    # 团队管理测试

    def test_create_team(self):
        """测试创建团队"""
        user = self.manager.create_user("Owner", "owner@example.com")
        team = self.manager.create_team("Research Team", user.user_id, "For research")
        assert team.name == "Research Team"
        assert user.user_id in team.member_ids

    def test_get_team(self):
        """测试获取团队"""
        user = self.manager.create_user("User2", "user2@example.com")
        team = self.manager.create_team("Team B", user.user_id)
        retrieved = self.manager.get_team(team.team_id)
        assert retrieved is not None
        assert retrieved.name == "Team B"

    def test_delete_team(self):
        """测试删除团队"""
        user = self.manager.create_user("User3", "user3@example.com")
        team = self.manager.create_team("Team C", user.user_id)
        result = self.manager.delete_team(team.team_id)
        assert result is True
        assert self.manager.get_team(team.team_id) is None

    # 成员管理测试

    def test_add_team_member(self):
        """测试添加成员"""
        owner = self.manager.create_user("Owner4", "owner4@example.com")
        member = self.manager.create_user("Member4", "member4@example.com")
        team = self.manager.create_team("Team D", owner.user_id)

        result = self.manager.add_team_member(team.team_id, member.user_id)
        assert result is True
        assert member.user_id in self.manager.get_team(team.team_id).member_ids

    def test_remove_team_member(self):
        """测试移除成员"""
        owner = self.manager.create_user("Owner5", "owner5@example.com")
        member = self.manager.create_user("Member5", "member5@example.com")
        team = self.manager.create_team("Team E", owner.user_id)
        self.manager.add_team_member(team.team_id, member.user_id)

        result = self.manager.remove_team_member(team.team_id, member.user_id)
        assert result is True
        assert member.user_id not in self.manager.get_team(team.team_id).member_ids

    def test_remove_owner_fails(self):
        """测试移除所有者失败"""
        owner = self.manager.create_user("Owner6", "owner6@example.com")
        team = self.manager.create_team("Team F", owner.user_id)

        result = self.manager.remove_team_member(team.team_id, owner.user_id)
        assert result is False  # 不能移除所有者

    def test_get_team_members(self):
        """测试获取团队成员"""
        owner = self.manager.create_user("Owner7", "owner7@example.com")
        member = self.manager.create_user("Member7", "member7@example.com")
        team = self.manager.create_team("Team G", owner.user_id)
        self.manager.add_team_member(team.team_id, member.user_id)

        members = self.manager.get_team_members(team.team_id)
        assert len(members) == 2

    def test_get_user_teams(self):
        """测试获取用户所在团队"""
        user = self.manager.create_user("User8", "user8@example.com")
        team1 = self.manager.create_team("Team H", user.user_id)
        team2 = self.manager.create_team("Team I", user.user_id)

        teams = self.manager.get_user_teams(user.user_id)
        assert len(teams) == 2

    # 共享订阅测试

    def test_create_shared_subscription(self):
        """测试创建共享订阅"""
        user = self.manager.create_user("User9", "user9@example.com")
        team = self.manager.create_team("Team J", user.user_id)

        sub = self.manager.create_shared_subscription(
            team_id=team.team_id,
            created_by=user.user_id,
            keywords=["ML", "AI"],
            channels=["email", "slack"],
            frequency="weekly"
        )
        assert sub.keywords == ["ML", "AI"]

    def test_get_team_subscriptions(self):
        """测试获取团队订阅"""
        user = self.manager.create_user("User10", "user10@example.com")
        team = self.manager.create_team("Team K", user.user_id)

        self.manager.create_shared_subscription(
            team_id=team.team_id,
            created_by=user.user_id,
            keywords=["NLP"],
            channels=["email"],
            frequency="daily"
        )

        subs = self.manager.get_team_subscriptions(team.team_id)
        assert len(subs) == 1

    # 讨论测试

    def test_create_discussion(self):
        """测试创建讨论"""
        user = self.manager.create_user("User11", "user11@example.com")
        team = self.manager.create_team("Team L", user.user_id)

        discussion = self.manager.create_discussion(
            team_id=team.team_id,
            author_id=user.user_id,
            title="Great Paper",
            content="I found this paper very insightful..."
        )
        assert discussion.title == "Great Paper"

    def test_get_team_discussions(self):
        """测试获取团队讨论"""
        user = self.manager.create_user("User12", "user12@example.com")
        team = self.manager.create_team("Team M", user.user_id)

        self.manager.create_discussion(
            team_id=team.team_id,
            author_id=user.user_id,
            title="Discussion 1",
            content="Content 1"
        )

        discussions = self.manager.get_team_discussions(team.team_id)
        assert len(discussions) == 1

    # 权限检查测试

    def test_is_team_member(self):
        """测试成员检查"""
        owner = self.manager.create_user("Owner13", "owner13@example.com")
        member = self.manager.create_user("Member13", "member13@example.com")
        team = self.manager.create_team("Team N", owner.user_id)
        self.manager.add_team_member(team.team_id, member.user_id)

        assert self.manager.is_team_member(team.team_id, member.user_id) is True
        assert self.manager.is_team_member(team.team_id, "nonexistent") is False

    def test_is_team_owner(self):
        """测试所有者检查"""
        owner = self.manager.create_user("Owner14", "owner14@example.com")
        team = self.manager.create_team("Team O", owner.user_id)

        assert self.manager.is_team_owner(team.team_id, owner.user_id) is True
        assert self.manager.is_team_owner(team.team_id, "other") is False

    def test_can_manage_team(self):
        """测试管理权限检查"""
        owner = self.manager.create_user("Owner15", "owner15@example.com")
        team = self.manager.create_team("Team P", owner.user_id)

        assert self.manager.can_manage_team(team.team_id, owner.user_id) is True


class TestGlobalInstance:
    """全局实例测试"""

    def test_get_team_manager_singleton(self):
        """测试团队管理器单例"""
        mgr1 = get_team_manager()
        mgr2 = get_team_manager()
        assert mgr1 is mgr2


class TestIntegration:
    """集成测试"""

    def setup_method(self):
        self.manager = TeamManager()

    @pytest.mark.asyncio
    async def test_full_team_workflow(self):
        """测试完整团队工作流"""
        # 1. 创建团队成员
        owner = self.manager.create_user("TeamOwner", "owner@team.com")
        member1 = self.manager.create_user("Member1", "member1@team.com")
        member2 = self.manager.create_user("Member2", "member2@team.com")

        # 2. 创建团队
        team = self.manager.create_team(
            "AI Research Team",
            owner.user_id,
            "研究AI最新论文"
        )

        # 3. 添加成员
        self.manager.add_team_member(team.team_id, member1.user_id)
        self.manager.add_team_member(team.team_id, member2.user_id)

        # 4. 创建共享订阅
        sub = self.manager.create_shared_subscription(
            team_id=team.team_id,
            created_by=owner.user_id,
            keywords=["machine learning", "deep learning"],
            channels=["email"],
            frequency="daily"
        )

        # 5. 创建讨论
        discussion = self.manager.create_discussion(
            team_id=team.team_id,
            author_id=member1.user_id,
            paper_id="paper_123",
            title="关于Transformer的讨论",
            content="我认为这篇论文的创新点在于..."
        )

        # 6. 验证
        assert len(self.manager.get_team_members(team.team_id)) == 3
        assert len(self.manager.get_team_subscriptions(team.team_id)) == 1
        assert len(self.manager.get_team_discussions(team.team_id)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
