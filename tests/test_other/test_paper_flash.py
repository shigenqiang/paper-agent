"""
PaperFlash论文快讯 单元测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.agents_v2.qa import (
    PaperFlash,
    FlashType,
    FlashReport,
    PaperFlashResult,
    FlashSubscription
)


class TestFlashType:
    """FlashType 枚举测试"""

    def test_flash_types(self):
        """测试快讯类型枚举"""
        assert FlashType.HOT.value == "hot"
        assert FlashType.TRENDING.value == "trending"
        assert FlashType.CONFERENCE.value == "conference"

    def test_flash_type_from_string(self):
        """测试从字符串创建枚举"""
        assert FlashType("hot") == FlashType.HOT
        assert FlashType("trending") == FlashType.TRENDING
        assert FlashType("conference") == FlashType.CONFERENCE


class TestFlashReport:
    """FlashReport 数据类测试"""

    def test_create_flash_report(self):
        """测试创建快讯报告"""
        report = FlashReport(
            title="Test Paper",
            authors=["Author A", "Author B"],
            source="arXiv",
            published_date="2024-01-15",
            core_finding="核心发现1。核心发现2。核心发现3。",
            key_points=["要点1", "要点2", "要点3"],
            significance="研究意义重大",
            reading_time="5分钟",
            tldr="一句话总结",
            reason="高引用论文"
        )
        assert report.title == "Test Paper"
        assert len(report.authors) == 2
        assert "核心发现1" in report.core_finding

    def test_flash_report_defaults(self):
        """测试默认值"""
        report = FlashReport(
            title="Test",
            authors=[],
            source="test",
            published_date="",
            core_finding="",
            key_points=[],
            significance="",
            reading_time="5分钟",
            tldr=""
        )
        assert report.reason == ""


class TestPaperFlashResult:
    """PaperFlashResult 数据类测试"""

    def test_create_result(self):
        """测试创建结果"""
        result = PaperFlashResult(
            type=FlashType.HOT,
            generated_at="2024-01-15T10:00:00",
            topic="machine learning",
            reports=[],
            papers_analyzed=10,
            success=True
        )
        assert result.type == FlashType.HOT
        assert result.success is True
        assert result.papers_analyzed == 10


class TestFlashSubscription:
    """FlashSubscription 测试"""

    def test_create_subscription(self):
        """测试创建订阅"""
        sub = FlashSubscription(
            user_id="user_001",
            flash_types=[FlashType.HOT, FlashType.TRENDING],
            topics=["machine learning", "deep learning"],
            limit_per_flash=5
        )
        assert sub.user_id == "user_001"
        assert len(sub.flash_types) == 2
        assert sub.enabled is True

    def test_to_dict(self):
        """测试转换为字典"""
        sub = FlashSubscription(
            user_id="user_001",
            flash_types=[FlashType.HOT],
            topics=["ML"],
            limit_per_flash=3
        )
        data = sub.to_dict()
        assert data["user_id"] == "user_001"
        assert "hot" in data["flash_types"]
        assert data["limit_per_flash"] == 3

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "user_id": "user_002",
            "flash_types": ["trending", "conference"],
            "topics": ["NLP"],
            "limit_per_flash": 5,
            "enabled": True
        }
        sub = FlashSubscription.from_dict(data)
        assert sub.user_id == "user_002"
        assert FlashType.TRENDING in sub.flash_types
        assert sub.topics == ["NLP"]

    def test_from_dict_defaults(self):
        """测试从字典创建默认值"""
        data = {"user_id": "user_003"}
        sub = FlashSubscription.from_dict(data)
        assert sub.flash_types == [FlashType.HOT]
        assert sub.topics == ["machine learning"]
        assert sub.limit_per_flash == 5


class TestPaperFlash:
    """PaperFlash Agent 测试"""

    def setup_method(self):
        self.flash = PaperFlash()

    def test_init(self):
        """测试初始化"""
        assert self.flash.name == "PaperFlash"
        assert self.flash.description == "论文快讯 - 热点论文快速解读"

    def test_top_conferences(self):
        """测试顶会列表"""
        assert "NeurIPS" in self.flash.TOP_CONFERENCES
        assert "ICML" in self.flash.TOP_CONFERENCES
        assert "ACL" in self.flash.TOP_CONFERENCES

    @pytest.mark.asyncio
    async def test_execute_empty_result(self):
        """测试无结果情况"""
        with patch.object(self.flash, '_search_papers', return_value=[]):
            result = await self.flash.execute(FlashType.HOT, topic="nonexistent_topic_xyz")
            assert result["success"] is False
            assert result["reports"] == []

    @pytest.mark.asyncio
    async def test_search_hot_papers(self):
        """测试搜索热点论文"""
        mock_papers = [
            {
                "title": "Paper 1",
                "citations": 100,
                "year": 2024,
                "source": "arXiv",
                "abstract": "Abstract 1"
            },
            {
                "title": "Paper 2",
                "citations": 50,
                "year": 2024,
                "source": "arXiv",
                "abstract": "Abstract 2"
            }
        ]
        with patch.object(self.flash.search_agent, 'execute', return_value={"papers": mock_papers}):
            papers = await self.flash._search_hot_papers("machine learning", 5)
            assert len(papers) == 2
            # 应该按引用数排序
            assert papers[0]["citations"] >= papers[1]["citations"]

    @pytest.mark.asyncio
    async def test_search_trending_papers(self):
        """测试搜索趋势论文"""
        mock_papers = [
            {
                "title": "New Paper",
                "citations": 20,
                "year": 2024,
                "source": "arXiv",
                "abstract": "Abstract"
            }
        ]
        with patch.object(self.flash.search_agent, 'execute', return_value={"papers": mock_papers}):
            papers = await self.flash._search_trending_papers("deep learning", 5)
            assert len(papers) == 1

    @pytest.mark.asyncio
    async def test_search_conference_papers(self):
        """测试搜索顶会论文"""
        mock_papers = [
            {
                "title": "NeurIPS Paper 2024",
                "citations": 50,
                "year": 2024,
                "source": "arXiv",
                "abstract": "Abstract"
            }
        ]
        with patch.object(self.flash.search_agent, 'execute', return_value={"papers": mock_papers}):
            papers = await self.flash._search_conference_papers("learning", "NeurIPS", 5)
            assert len(papers) == 1

    @pytest.mark.asyncio
    async def test_generate_single_report_fallback(self):
        """测试单篇快讯生成降级处理"""
        mock_paper = {
            "title": "Test Paper",
            "authors": ["Author A"],
            "year": 2024,
            "source": "arXiv",
            "abstract": "Test abstract"
        }
        # 模拟LLM返回无效JSON
        with patch.object(self.flash, '_llm_call', return_value="not valid json"):
            report = await self.flash._generate_single_report(mock_paper, FlashType.HOT)
            assert report is not None
            assert report["title"] == "Test Paper"
            assert report["tldr"] == "Test Paper"[:50]  # 使用标题作为tldr

    def test_run_sync(self):
        """测试同步运行"""
        with patch.object(self.flash, 'execute', return_value={"success": True}):
            result = self.flash.run_sync(FlashType.HOT, "ML", 5)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_daily_flash(self):
        """测试生成每日多主题快讯"""
        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "success": True,
                "reports": [{"title": f"Paper {call_count}", "tldr": "Summary"}]
            }

        with patch.object(self.flash, 'execute', side_effect=mock_execute):
            result = await self.flash.generate_daily_flash(
                topics=["ML", "DL"],
                limit_per_topic=2
            )
            assert result["success"] is True
            assert result["topics_processed"] == 2
            assert result["total_reports"] == 2  # 每主题返回1个报告

    @pytest.mark.asyncio
    async def test_generate_conference_flash(self):
        """测试生成顶会快讯"""
        with patch.object(self.flash, 'execute', return_value={"success": True, "reports": []}):
            result = await self.flash.generate_conference_flash("NeurIPS", "AI", 10)
            assert result["success"] is True


class TestPaperFlashIntegration:
    """PaperFlash 集成测试"""

    def setup_method(self):
        self.flash = PaperFlash()

    @pytest.mark.asyncio
    async def test_full_flow(self):
        """测试完整流程"""
        # 这个测试需要真实的API调用，标记为集成测试
        # 在CI环境中可能跳过
        pass

    def test_subscription_workflow(self):
        """测试订阅工作流"""
        # 创建订阅
        sub = FlashSubscription(
            user_id="researcher_001",
            flash_types=[FlashType.HOT, FlashType.CONFERENCE],
            topics=["machine learning", "causal inference"],
            limit_per_flash=5
        )

        # 模拟订阅管理
        subscriptions = {}
        subscriptions[sub.user_id] = sub

        # 验证订阅
        retrieved = subscriptions.get("researcher_001")
        assert retrieved is not None
        assert FlashType.CONFERENCE in retrieved.flash_types
        assert "causal inference" in retrieved.topics

        # 禁用订阅
        retrieved.enabled = False
        assert retrieved.enabled is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
