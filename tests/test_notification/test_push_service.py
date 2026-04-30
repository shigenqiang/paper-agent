"""
推送服务 单元测试
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from src.agents_v2._archive.notification import (
    PushChannel,
    EmailChannel,
    SlackChannel,
    FeishuChannel,
    DingTalkChannel,
    PushService,
    get_push_service
)


class TestEmailChannel:
    """EmailChannel 测试"""

    def setup_method(self):
        self.channel = EmailChannel()

    def test_init(self):
        """测试初始化"""
        assert self.channel.smtp_host == "smtp.gmail.com"
        assert self.channel.smtp_port == 587

    @pytest.mark.asyncio
    async def test_send(self):
        """测试发送"""
        result = await self.channel.send("test@example.com", "Test content", "Test title")
        assert result is True

    def test_format_html(self):
        """测试HTML格式化"""
        report = {
            "topic": "Machine Learning",
            "summary": "This is a summary",
            "papers_found": 45,
            "top_papers": [
                {"title": "Paper 1", "key_contribution": "Contribution 1"},
                {"title": "Paper 2", "key_contribution": "Contribution 2"}
            ]
        }
        html = self.channel.format_report(report, "html")
        assert "Machine Learning" in html
        assert "This is a summary" in html
        assert "45" in html
        assert "Paper 1" in html

    def test_format_text(self):
        """测试纯文本格式化"""
        report = {
            "topic": "Deep Learning",
            "summary": "DL summary",
            "papers_found": 30
        }
        text = self.channel.format_report(report, "text")
        assert "Deep Learning" in text
        assert "DL summary" in text


class TestSlackChannel:
    """SlackChannel 测试"""

    def setup_method(self):
        self.channel = SlackChannel()

    def test_init(self):
        """测试初始化"""
        assert self.channel.webhook_url == ""

    @pytest.mark.asyncio
    async def test_send(self):
        """测试发送"""
        result = await self.channel.send("#general", "Test", "Title")
        assert result is True

    def test_format_blocks(self):
        """测试Block格式"""
        report = {
            "topic": "NLP",
            "summary": "NLP summary",
            "papers_found": 25,
            "top_papers": [
                {"title": "Transformer Paper"}
            ]
        }
        blocks_str = self.channel.format_report(report, "blocks")
        blocks = json.loads(blocks_str)
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"

    def test_format_text(self):
        """测试纯文本格式"""
        report = {"topic": "CV", "summary": "CV summary", "papers_found": 20}
        text = self.channel.format_report(report, "text")
        assert "CV" in text


class TestFeishuChannel:
    """FeishuChannel 测试"""

    def setup_method(self):
        self.channel = FeishuChannel()

    @pytest.mark.asyncio
    async def test_send(self):
        """测试发送"""
        result = await self.channel.send("user_123", "Content", "Title")
        assert result is True

    def test_format_card(self):
        """测试卡片格式"""
        report = {
            "topic": "Causal Inference",
            "summary": "Important findings",
            "papers_found": 15
        }
        card_str = self.channel.format_report(report, "card")
        card = json.loads(card_str)
        assert card["msg_type"] == "interactive"
        assert "elements" in card["card"]


class TestDingTalkChannel:
    """DingTalkChannel 测试"""

    def setup_method(self):
        self.channel = DingTalkChannel(webhook_url="https://oapi.dingtalk.com/robot/send")

    @pytest.mark.asyncio
    async def test_send(self):
        """测试发送"""
        result = await self.channel.send("group_123", "Message")
        assert result is True

    def test_format_markdown(self):
        """测试Markdown格式"""
        report = {"title": "Report", "summary": "Summary"}
        msg_str = self.channel.format_report(report, "markdown")
        msg = json.loads(msg_str)
        assert msg["msgtype"] == "markdown"


class TestPushService:
    """PushService 测试"""

    def setup_method(self):
        self.service = PushService()

    def test_init(self):
        """测试初始化"""
        channels = self.service.list_channels()
        assert "email" in channels
        assert "slack" in channels
        assert "feishu" in channels

    def test_register_channel(self):
        """测试注册渠道"""
        new_channel = EmailChannel()
        self.service.register_channel("custom_email", new_channel)
        assert "custom_email" in self.service.list_channels()

    def test_get_channel(self):
        """测试获取渠道"""
        channel = self.service.get_channel("email")
        assert channel is not None
        assert isinstance(channel, EmailChannel)

    def test_get_channel_not_found(self):
        """测试获取不存在的渠道"""
        channel = self.service.get_channel("nonexistent")
        assert channel is None

    @pytest.mark.asyncio
    async def test_push_report(self):
        """测试推送报告"""
        report = {
            "topic": "Test Report",
            "summary": "Test summary",
            "papers_found": 10
        }
        result = await self.service.push_report(
            report=report,
            channels=["email"],
            recipients=["test@example.com"]
        )
        assert result["total"] == 1
        assert result["success"] >= 0

    @pytest.mark.asyncio
    async def test_push_report_multiple_channels(self):
        """测试多渠道推送"""
        report = {
            "topic": "Multi-channel Report",
            "summary": "Testing multiple channels"
        }
        result = await self.service.push_report(
            report=report,
            channels=["email", "slack"],
            recipients=["user1@example.com"]
        )
        assert result["total"] == 2  # 2 channels * 1 recipient

    def test_get_history(self):
        """测试获取历史"""
        history = self.service.get_history(limit=10)
        assert isinstance(history, list)

    def test_clear_history(self):
        """测试清空历史"""
        self.service.clear_history()
        assert len(self.service.get_history()) == 0


class TestGlobalInstance:
    """全局实例测试"""

    def test_get_push_service_singleton(self):
        """测试推送服务单例"""
        svc1 = get_push_service()
        svc2 = get_push_service()
        assert svc1 is svc2


class TestIntegration:
    """集成测试"""

    def setup_method(self):
        self.service = PushService()

    @pytest.mark.asyncio
    async def test_full_push_flow(self):
        """测试完整推送流程"""
        # 准备报告
        report = {
            "topic": "每日论文快讯",
            "summary": "今日共收集50篇论文",
            "papers_found": 50,
            "top_papers": [
                {"title": "Paper 1", "key_contribution": "创新点A"},
                {"title": "Paper 2", "key_contribution": "创新点B"}
            ],
            "trends": ["大模型", "因果推断"]
        }

        # 推送到邮件
        email_result = await self.service.push_report(
            report=report,
            channels=["email"],
            recipients=["researcher@example.com"],
            format_type="html"
        )
        assert email_result["total"] == 1

        # 推送到Slack
        slack_result = await self.service.push_report(
            report=report,
            channels=["slack"],
            recipients=["#paper-updates"],
            format_type="blocks"
        )
        assert slack_result["total"] == 1

        # 验证历史记录
        history = self.service.get_history()
        assert len(history) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
