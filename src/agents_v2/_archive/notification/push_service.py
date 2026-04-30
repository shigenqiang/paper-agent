"""推送服务 - 多渠道发送报告通知"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import json

logger = logging.getLogger(__name__)


class PushChannel(ABC):
    """推送渠道基类"""

    @abstractmethod
    async def send(self, recipient: str, content: str, title: str = "") -> bool:
        """发送消息"""
        pass

    @abstractmethod
    def format_report(self, report: Dict[str, Any], format_type: str) -> str:
        """格式化报告内容"""
        pass


class EmailChannel(PushChannel):
    """邮件推送渠道"""

    def __init__(self, smtp_host: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    async def send(self, recipient: str, content: str, title: str = "") -> bool:
        """发送邮件"""
        try:
            # 实际实现需要集成smtplib
            logger.info(f"[Email] 发送邮件到 {recipient}: {title}")
            # 模拟发送成功
            return True
        except Exception as e:
            logger.error(f"[Email] 发送失败: {e}")
            return False

    def format_report(self, report: Dict[str, Any], format_type: str = "html") -> str:
        """格式化邮件内容"""
        if format_type == "html":
            return self._format_html(report)
        else:
            return self._format_text(report)

    def _format_html(self, report: Dict[str, Any]) -> str:
        """HTML格式"""
        title = report.get("topic", report.get("title", "论文报告"))
        summary = report.get("summary", "")

        html = f"""
        <html>
        <body>
        <h1>{title}</h1>
        <h2>摘要</h2>
        <p>{summary}</p>
        """

        if "papers_found" in report:
            html += f"<p><strong>论文数量:</strong> {report['papers_found']}</p>"

        if "top_papers" in report and report["top_papers"]:
            html += "<h2>精选论文</h2><ul>"
            for paper in report["top_papers"][:5]:
                html += f"<li><strong>{paper.get('title', 'N/A')}</strong>"
                if paper.get("key_contribution"):
                    html += f"<br/>{paper.get('key_contribution')}"
                html += "</li>"
            html += "</ul>"

        html += "</body></html>"
        return html

    def _format_text(self, report: Dict[str, Any]) -> str:
        """纯文本格式"""
        lines = [
            f"=== {report.get('topic', report.get('title', '论文报告'))} ===",
            "",
            report.get("summary", ""),
            ""
        ]

        if "papers_found" in report:
            lines.append(f"论文数量: {report['papers_found']}")

        if "top_papers" in report and report["top_papers"]:
            lines.append("")
            lines.append("精选论文:")
            for i, paper in enumerate(report["top_papers"][:5], 1):
                lines.append(f"{i}. {paper.get('title', 'N/A')}")

        return "\n".join(lines)


class SlackChannel(PushChannel):
    """Slack推送渠道"""

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    async def send(self, recipient: str, content: str, title: str = "") -> bool:
        """发送Slack消息"""
        try:
            logger.info(f"[Slack] 发送消息到 {recipient}")
            # 实际实现需要集成requests
            return True
        except Exception as e:
            logger.error(f"[Slack] 发送失败: {e}")
            return False

    def format_report(self, report: Dict[str, Any], format_type: str = "blocks") -> str:
        """格式化Slack消息"""
        title = report.get("topic", report.get("title", "论文报告"))
        summary = report.get("summary", "")

        if format_type == "blocks":
            return self._format_blocks(report, title, summary)
        else:
            return self._format_text(report, title, summary)

    def _format_blocks(self, report: Dict[str, Any], title: str, summary: str) -> str:
        """Slack Block Kit格式"""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title[:100]}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": summary[:300]}
            }
        ]

        if "papers_found" in report:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"📚 {report['papers_found']} 篇论文"}]
            })

        if "top_papers" in report and report["top_papers"]:
            papers_text = "\n".join([
                f"• *{p.get('title', 'N/A')[:80]}*" for p in report["top_papers"][:3]
            ])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*精选论文:*\n{papers_text}"}
            })

        return json.dumps(blocks)

    def _format_text(self, report: Dict[str, Any], title: str, summary: str) -> str:
        """纯文本格式"""
        lines = [f"*{title}*", "", summary[:200]]
        if "papers_found" in report:
            lines.append(f"📚 {report['papers_found']} 篇论文")
        return "\n".join(lines)


class FeishuChannel(PushChannel):
    """飞书推送渠道"""

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    async def send(self, recipient: str, content: str, title: str = "") -> bool:
        """发送飞书消息"""
        try:
            logger.info(f"[Feishu] 发送消息到 {recipient}")
            return True
        except Exception as e:
            logger.error(f"[Feishu] 发送失败: {e}")
            return False

    def format_report(self, report: Dict[str, Any], format_type: str = "card") -> str:
        """格式化飞书消息"""
        title = report.get("topic", report.get("title", "论文报告"))
        summary = report.get("summary", "")

        if format_type == "card":
            return self._format_card(report, title, summary)
        else:
            return self._format_text(report, title, summary)

    def _format_card(self, report: Dict[str, Any], title: str, summary: str) -> str:
        """飞书卡片格式"""
        elements = [
            {"tag": "markdown", "content": f"**{title}**"},
            {"tag": "hr"},
            {"tag": "markdown", "content": summary[:200]}
        ]

        if "papers_found" in report:
            elements.append({
                "tag": "note",
                "elements": [{"tag": "text", "content": f"📚 {report['papers_found']} 篇论文"}]
            })

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": "📰 论文快讯"}},
                "elements": elements
            }
        }
        return json.dumps(card, ensure_ascii=False)

    def _format_text(self, report: Dict[str, Any], title: str, summary: str) -> str:
        """纯文本格式"""
        lines = [f"*{title}*", "", summary[:200]]
        return "\n".join(lines)


class DingTalkChannel(PushChannel):
    """钉钉推送渠道"""

    def __init__(self, webhook_url: str = "", secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret

    async def send(self, recipient: str, content: str, title: str = "") -> bool:
        """发送钉钉消息"""
        try:
            logger.info(f"[DingTalk] 发送消息")
            return True
        except Exception as e:
            logger.error(f"[DingTalk] 发送失败: {e}")
            return False

    def format_report(self, report: Dict[str, Any], format_type: str = "markdown") -> str:
        """格式化钉钉消息"""
        title = report.get("topic", report.get("title", "论文报告"))
        summary = report.get("summary", "")

        msg = {
            "msgtype": format_type,
            format_type: {
                "title": title,
                "text": summary[:200]
            }
        }
        return json.dumps(msg, ensure_ascii=False)


class PushService:
    """
    统一推送服务

    功能：
    - 多渠道管理
    - 报告推送
    - 推送历史记录
    """

    def __init__(self):
        self._channels: Dict[str, PushChannel] = {}
        self._push_history: List[Dict[str, Any]] = []

        # 初始化默认渠道
        self._register_default_channels()

    def _register_default_channels(self):
        """注册默认渠道"""
        self.register_channel("email", EmailChannel())
        self.register_channel("slack", SlackChannel())
        self.register_channel("feishu", FeishuChannel())
        self.register_channel("dingtalk", DingTalkChannel())

    def register_channel(self, name: str, channel: PushChannel):
        """注册推送渠道"""
        self._channels[name] = channel
        logger.info(f"注册推送渠道: {name}")

    def get_channel(self, name: str) -> Optional[PushChannel]:
        """获取推送渠道"""
        return self._channels.get(name)

    def list_channels(self) -> List[str]:
        """列出所有渠道"""
        return list(self._channels.keys())

    async def push_report(
        self,
        report: Dict[str, Any],
        channels: List[str],
        recipients: List[str],
        format_type: str = "default"
    ) -> Dict[str, Any]:
        """
        推送报告到多个渠道

        Args:
            report: 报告内容
            channels: 渠道列表 (email, slack, feishu, dingtalk)
            recipients: 接收人列表
            format_type: 格式化类型

        Returns:
            推送结果
        """
        results = []
        success_count = 0
        failure_count = 0

        for channel_name in channels:
            channel = self.get_channel(channel_name)
            if not channel:
                logger.warning(f"未找到渠道: {channel_name}")
                results.append({
                    "channel": channel_name,
                    "success": False,
                    "error": "Channel not found"
                })
                failure_count += 1
                continue

            formatted_content = channel.format_report(report, format_type)

            for recipient in recipients:
                success = await channel.send(recipient, formatted_content, report.get("title", ""))
                results.append({
                    "channel": channel_name,
                    "recipient": recipient,
                    "success": success
                })
                if success:
                    success_count += 1
                else:
                    failure_count += 1

        # 记录推送历史
        self._push_history.append({
            "timestamp": asyncio.get_event_loop().time(),
            "report_topic": report.get("topic", report.get("title", "")),
            "channels": channels,
            "recipients": recipients,
            "success_count": success_count,
            "failure_count": failure_count
        })

        return {
            "total": len(channels) * len(recipients),
            "success": success_count,
            "failure": failure_count,
            "results": results
        }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取推送历史"""
        return self._push_history[-limit:]

    def clear_history(self):
        """清空推送历史"""
        self._push_history.clear()


# 全局推送服务实例
_global_push_service: Optional[PushService] = None


def get_push_service() -> PushService:
    """获取全局推送服务"""
    global _global_push_service
    if _global_push_service is None:
        _global_push_service = PushService()
    return _global_push_service
