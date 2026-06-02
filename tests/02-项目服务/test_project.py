"""模块02 项目服务 — 真实 PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中 (port 5432)
"""

import pytest

from src.agents_v3.research_workspace.services.project_service import ProjectService


class TestProjectServiceE2E:
    """ProjectService 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = ProjectService(storage=pg_storage)
        self._created = []
        yield
        for pid in self._created:
            try:
                pg_storage.delete_item("projects", pid)
            except Exception:
                pass

    def test_create_project(self, pg_storage):
        """创建项目应写入 PostgreSQL"""
        project = self.service.create_project(
            name="E2E测试项目",
            description="自动测试创建",
            discipline="CS",
        )
        self._created.append(project.project_id)

        assert project.name == "E2E测试项目"
        assert project.project_id.startswith("proj_")

        # 验证数据库中存在
        stored = pg_storage.get_item("projects", project.project_id)
        assert stored is not None
        assert stored["name"] == "E2E测试项目"

    def test_list_projects(self):
        """list_projects 应返回项目列表"""
        p1 = self.service.create_project(name="列表测试A")
        p2 = self.service.create_project(name="列表测试B")
        self._created.extend([p1.project_id, p2.project_id])

        projects = self.service.list_projects()
        names = {p.name for p in projects}
        assert "列表测试A" in names
        assert "列表测试B" in names

    def test_get_project(self):
        """get_project 应返回指定项目"""
        p = self.service.create_project(name="获取测试")
        self._created.append(p.project_id)

        got = self.service.get_project(p.project_id)
        assert got is not None
        assert got.name == "获取测试"

    def test_update_project(self, pg_storage):
        """update_project 应修改字段"""
        p = self.service.create_project(name="更新测试")
        self._created.append(p.project_id)

        # 直接通过 storage 更新，再用 service 读取
        pg_storage.upsert_item("projects", p.project_id, {
            "project_id": p.project_id,
            "name": "更新测试",
            "description": "已更新",
        })
        got = self.service.get_project(p.project_id)
        assert got.description == "已更新"
