"""
安全模块 - 安全加固

提供:
1. InputSanitizer: 输入清理
2. 安全配置
3. 敏感信息处理
"""
import re
import html
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class InputSanitizer:
    """
    输入清理器 - 防止XSS、注入等攻击

    使用方式:
        sanitizer = InputSanitizer()
        clean_input = sanitizer.sanitize(user_input)
    """

    # HTML标签黑名单
    DANGEROUS_TAGS = [
        "script", "iframe", "object", "embed", "form",
        "input", "button", "select", "textarea"
    ]

    # 危险事件属性
    DANGEROUS_ATTRS = [
        "onerror", "onload", "onclick", "onmouseover",
        "onfocus", "onblur", "onchange", "onsubmit"
    ]

    def __init__(self, allow_html: bool = False):
        self.allow_html = allow_html

    def sanitize(self, text: str) -> str:
        """
        清理输入文本

        Args:
            text: 原始输入

        Returns:
            清理后的文本
        """
        if not text:
            return ""

        # 基础清理
        text = self._remove_null_bytes(text)
        text = self._normalize_whitespace(text)

        if self.allow_html:
            text = self._sanitize_html(text)
        else:
            text = self._escape_html(text)

        # 移除潜在危险字符序列
        text = self._remove_dangerous_patterns(text)

        return text.strip()

    def _remove_null_bytes(self, text: str) -> str:
        """移除空字节"""
        return text.replace("\x00", "").replace("\0", "")

    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        text = re.sub(r"[\t\n\r]+", " ", text)
        text = re.sub(r" +", " ", text)
        return text

    def _escape_html(self, text: str) -> str:
        """转义HTML"""
        return html.escape(text, quote=True)

    def _sanitize_html(self, text: str) -> str:
        """清理HTML（保留部分标签）"""
        # 先转义所有
        text = html.escape(text, quote=True)

        # 允许的标签白名单
        allowed_tags = ["p", "br", "strong", "em", "u", "ol", "ul", "li", "h1", "h2", "h3"]

        for tag in self.DANGEROUS_TAGS:
            text = re.sub(f"<{tag}[^>]*>.*?</{tag}>", "", text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(f"<{tag}[^>]*/?>", "", text, flags=re.IGNORECASE)

        # 移除危险属性
        for attr in self.DANGEROUS_ATTRS:
            text = re.sub(f'{attr}="[^"]*"', "", text, flags=re.IGNORECASE)
            text = re.sub(f"{attr}='[^']*'", "", text, flags=re.IGNORECASE)

        return text

    def _remove_dangerous_patterns(self, text: str) -> str:
        """移除危险模式"""
        dangerous_patterns = [
            r"javascript:",
            r"vbscript:",
            r"data:text/html",
            r"<[^\s]*[\s\S]*?feed[\s\S]*?>",
            r"[\s\S]*?eval\s*\(",
            r"[\s\S]*?document\.cookie",
            r"[\s\S]*?document\.write",
        ]

        for pattern in dangerous_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理字典中的所有字符串值"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [self.sanitize(v) if isinstance(v, str) else v for v in value]
            else:
                sanitized[key] = value
        return sanitized


class SecretManager:
    """
    敏感信息管理

    使用方式:
        secrets = SecretManager()
        secrets.set("OPENAI_API_KEY", "sk-xxx")
        api_key = secrets.get("OPENAI_API_KEY")  # 从环境变量或存储获取
    """

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._env_prefix = "PAPER_AGENT_"

    def set(self, key: str, value: str):
        """设置密钥"""
        self._secrets[key] = value

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取密钥（优先从环境变量）"""
        # 先检查环境变量
        env_key = f"{self._env_prefix}{key}"
        import os
        env_value = os.environ.get(env_key) or os.environ.get(key)
        if env_value:
            return env_value

        # 回退到内存存储
        return self._secrets.get(key, default)

    def get_or_raise(self, key: str) -> str:
        """获取密钥，不存在则抛出异常"""
        value = self.get(key)
        if not value:
            from .exceptions import ConfigurationError
            raise ConfigurationError(f"Required secret not found: {key}")
        return value

    def clear(self):
        """清空所有密钥"""
        self._secrets.clear()


class SecurityConfig:
    """安全配置"""

    def __init__(
        self,
        sanitize_input: bool = True,
        allow_html: bool = False,
        max_input_length: int = 10000,
        rate_limit: int = 100,
        rate_window: int = 60
    ):
        self.sanitize_input = sanitize_input
        self.allow_html = allow_html
        self.max_input_length = max_input_length
        self.rate_limit = rate_limit  # 每窗口最大请求数
        self.rate_window = rate_window  # 窗口大小（秒）


# 全局实例
_secrets = SecretManager()


def get_secrets() -> SecretManager:
    """获取全局密钥管理器"""
    return _secrets


def sanitize_input(text: str, sanitizer: Optional[InputSanitizer] = None) -> str:
    """快捷输入清理函数"""
    if sanitizer is None:
        sanitizer = InputSanitizer()
    return sanitizer.sanitize(text)
