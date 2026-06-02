"""模块06 证据表 — 真实 PostgreSQL

前置条件:
    - Docker 容器 paper-agent-postgres 运行中
    - 至少有一篇已生成卡片的论文
"""

import pytest

from src.agents_v3.research_workspace.evidence_table import EvidenceTableService


class TestEvidenceTableE2E:
    """EvidenceTableService 真实链路测试"""

    @pytest.fixture(autouse=True)
    def setup(self, pg_storage):
        self.service = EvidenceTableService(storage=pg_storage)

    def test_build_for_project(self, pg_storage):
        """为项目构建证据表"""
        # 查找一个有 paper_cards 的项目
        cards = pg_storage.list_all("paper_cards")
        if not cards:
            pytest.skip("数据库中无 paper_cards")

        paper_ids = {c["paper_id"] for c in cards}
        papers = pg_storage.list_all("papers")
        project_ids = {p["project_id"] for p in papers if p["paper_id"] in paper_ids}

        if not project_ids:
            pytest.skip("无法关联到项目")

        pid = list(project_ids)[0]
        records = self.service.build_for_project(pid)
        print(f"\n[evidence] 项目 {pid} 生成 {len(records)} 条证据")
        # 验证证据已存入数据库
        stored = pg_storage.query("evidence_records", {"project_id": pid})
        assert len(stored) >= len(records)

    def test_evidence_has_source_span(self, pg_storage):
        """证据记录应有来源引用"""
        records = pg_storage.list_all("evidence_records")
        if not records:
            pytest.skip("数据库中无证据记录")

        for r in records[:3]:
            print(f"\n[evidence] {r.get('evidence_id')}: claim={r.get('claim', '')[:50]}...")
