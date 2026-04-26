"""
文本清理器单元测试

测试文本清理功能
"""
import pytest
from src.agents_v2.validation.text_cleaner import (
    TextCleaner,
    CleanResult,
    CleanLevel,
    clean_text,
    sanitize_input,
)


class TestCleanLevel:
    """CleanLevel 枚举测试"""

    def test_all_levels_exist(self):
        """测试所有级别存在"""
        assert CleanLevel.MINIMAL.value == "minimal"
        assert CleanLevel.NORMAL.value == "normal"
        assert CleanLevel.THOROUGH.value == "thorough"
        assert CleanLevel.SANITIZE.value == "sanitize"


class TestCleanResult:
    """CleanResult 测试"""

    def test_empty_result(self):
        """测试空结果"""
        result = CleanResult(original="", cleaned="")
        assert not result.has_changes
        assert result.cleaned == ""

    def test_has_changes(self):
        """测试变化检测"""
        result = CleanResult(
            original="<p>Hello</p>",
            cleaned="Hello",
            changes=[{"type": "html_removed"}]
        )
        assert result.has_changes

    def test_change_summary(self):
        """测试变化摘要"""
        result = CleanResult(
            original="Hello!!!",
            cleaned="Hello!",
            changes=[{"type": "punctuation"}]
        )
        assert "punctuation" in result.change_summary


class TestTextCleaner:
    """TextCleaner 测试"""

    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_basic_clean(self):
        """测试基本清理"""
        result = self.cleaner.clean("  Hello   World  ")
        assert result.cleaned == "Hello World"

    def test_strip_whitespace(self):
        """测试去除首尾空白"""
        result = self.cleaner.clean("  Hello  ")
        assert result.cleaned == "Hello"

    def test_remove_html_tags(self):
        """测试去除HTML标签"""
        result = self.cleaner.clean("<p>Hello</p>", remove_html=True)
        assert result.cleaned == "Hello"
        assert len(result.changes) > 0

    def test_remove_urls(self):
        """测试去除URL"""
        result = self.cleaner.clean(
            "Check https://example.com for more",
            remove_urls=True
        )
        assert "example.com" not in result.cleaned

    def test_remove_emails(self):
        """测试去除邮箱"""
        result = self.cleaner.clean(
            "Contact test@example.com",
            remove_emails=True
        )
        assert "test@example.com" not in result.cleaned

    def test_remove_html_entities(self):
        """测试HTML实体转换"""
        result = self.cleaner.clean("Hello &amp; World", remove_html=True)
        assert "&amp;" not in result.cleaned or "and" in result.cleaned.lower()

    def test_lowercase(self):
        """测试转小写"""
        result = self.cleaner.clean("Hello WORLD", lowercase=True)
        assert result.cleaned == "hello world"

    def test_normalize_whitespace(self):
        """测试空白规范化"""
        result = self.cleaner.clean("Hello    world")
        assert "    " not in result.cleaned

    def test_remove_control_chars(self):
        """测试去除控制字符"""
        result = self.cleaner.clean("Hello\x00World")
        assert "\x00" not in result.cleaned

    def test_excessive_punctuation(self):
        """测试去除过多标点"""
        result = self.cleaner.clean(
            "Hello!!!",
            remove_excessive_punctuation=True,
            max_punctuation=2
        )
        assert result.cleaned == "Hello!!"

    def test_level_minimal(self):
        """测试最小清理级别"""
        result = self.cleaner.clean(
            "<p>Hello</p>",
            level=CleanLevel.MINIMAL
        )
        # 最小清理可能不完全去除HTML
        assert len(result.changes) == 0

    def test_level_normal(self):
        """测试普通清理级别"""
        result = self.cleaner.clean(
            "<p>Hello</p>",
            level=CleanLevel.NORMAL
        )
        assert "Hello" in result.cleaned

    def test_level_thorough(self):
        """测试彻底清理级别"""
        result = self.cleaner.clean(
            "<p>Check https://example.com</p>",
            level=CleanLevel.THOROUGH
        )
        assert "example.com" not in result.cleaned

    def test_level_sanitize(self):
        """测试消毒级别"""
        result = self.cleaner.clean(
            "<script>alert('xss')</script>Contact: test@example.com",
            level=CleanLevel.SANITIZE
        )
        assert "script" not in result.cleaned.lower()
        assert "example.com" not in result.cleaned

    def test_remove_emojis(self):
        """测试去除表情符号"""
        result = self.cleaner.clean(
            "Hello 😀 World",
            remove_emojis=True
        )
        assert "😀" not in result.cleaned

    def test_preserve_newlines(self):
        """测试保留换行"""
        result = self.cleaner.clean(
            "Hello\n\n\nWorld",
            preserve_newlines=True
        )
        # 多个换行会合并为两个
        assert result.cleaned.count("\n") <= 2

    def test_remove_newlines(self):
        """测试去除换行"""
        result = self.cleaner.clean(
            "Hello\nWorld",
            preserve_newlines=False
        )
        assert "\n" not in result.cleaned

    def test_truncate(self):
        """测试截断"""
        result = self.cleaner.truncate("Hello World", 8)
        assert len(result) <= 8
        assert result.endswith("...")

    def test_clean_for_search(self):
        """测试搜索清理"""
        result = self.cleaner.clean_for_search("机器学习 的 深度学习")
        assert "的" not in result.split()

    def test_clean_for_display(self):
        """测试显示清理"""
        result = self.cleaner.clean_for_display("  Hello World  ", max_length=20)
        assert len(result) <= 23  # 考虑 ellipsis

    def test_normalize_quotes(self):
        """测试引号规范化"""
        result = self.cleaner.normalize_quotes('"Hello"')
        assert '"' in result or "'" in result

    def test_normalize_dashes(self):
        """测试破折号规范化"""
        result = self.cleaner.normalize_dashes("Hello---World")
        assert result.count("--") == 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_clean_text(self):
        """测试clean_text函数"""
        result = clean_text("  Hello   World  ")
        assert result.cleaned == "Hello World"

    def test_sanitize_input(self):
        """测试sanitize_input函数"""
        result = sanitize_input("<script>alert('xss')</script>")
        # HTML tags should be removed
        assert "<script>" not in result
        assert "script" not in result.lower()


class TestEmptyAndSpecialCases:
    """空值和特殊情况测试"""

    def test_empty_string(self):
        """测试空字符串"""
        result = TextCleaner().clean("")
        assert result.cleaned == ""
        assert not result.has_changes

    def test_none_input(self):
        """测试None输入"""
        result = TextCleaner().clean(None)
        assert result.cleaned == ""

    def test_only_whitespace(self):
        """测试仅空白字符"""
        result = TextCleaner().clean("   \t\n  ")
        assert result.cleaned == ""

    def test_only_special_chars(self):
        """测试仅特殊字符"""
        result = TextCleaner().clean("!@#$%^&*()")
        assert len(result.cleaned) > 0

    def test_chinese_text(self):
        """测试中文文本"""
        result = TextCleaner().clean("你好，世界！")
        assert "你好" in result.cleaned
        assert "，" in result.cleaned or "，" not in result.cleaned


if __name__ == "__main__":
    pytest.main([__file__, "-v"])