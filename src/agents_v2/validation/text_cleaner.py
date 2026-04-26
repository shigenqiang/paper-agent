"""
Text Cleaner - 文本清理器

提供文本清理、标准化和预处理功能。
支持去除特殊字符、HTML标签、空白字符、URL、电话号码等。
"""
import re
import html
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from ..exceptions import ValidationError


class CleanLevel(str, Enum):
    """清理级别"""
    MINIMAL = "minimal"      # 最小清理，只去除明显的问题字符
    NORMAL = "normal"       # 普通清理，去除常见噪声
    THOROUGH = "thorough"   # 彻底清理，去除所有噪声
    SANITIZE = "sanitize"   # 消毒处理，高度清理


@dataclass
class CleanResult:
    """清理结果"""
    original: str
    cleaned: str
    changes: List[Dict[str, Any]] = field(default_factory=list)
    level: CleanLevel = CleanLevel.NORMAL

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0

    @property
    def change_summary(self) -> str:
        if not self.changes:
            return "No changes made"
        return f"Made {len(self.changes)} changes: {', '.join(c['type'] for c in self.changes)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "cleaned": self.cleaned,
            "changes": self.changes,
            "level": self.level.value if isinstance(self.level, Enum) else self.level,
            "has_changes": self.has_changes
        }


class TextCleaner:
    """
    文本清理器

    支持的清理操作:
    - 去除HTML标签
    - 去除URL
    - 去除邮箱地址
    - 去除电话号码
    - 去除特殊字符
    - 规范化空白字符
    - 去除控制字符
    - Unicode规范化
    - 去除表情符号（可选）
    - 大小写规范化
    - 去除多余标点

    使用示例:
        cleaner = TextCleaner()

        # 基本清理
        result = cleaner.clean("  Hello   World  ")
        print(result.cleaned)  # "Hello World"

        # 深度清理
        result = cleaner.clean(
            "<p>Check this: https://example.com</p>",
            level=CleanLevel.THOROUGH,
            remove_urls=True,
            remove_html=True
        )
        print(result.cleaned)  # "Check this"

        # 自定义清理
        result = cleaner.clean(
            "Hello!!!",
            remove_excessive_punctuation=True,
            max_punctuation=2
        )
        print(result.cleaned)  # "Hello!"
    """

    # 常用正则模式
    URL_PATTERN = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE
    )
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(
        r'(\+\d{1,3}[-.\s]?)?(\d{1,4}[-.\s]?)?(\d{1,4}[-.\s]?)?\d{1,9}',
        re.IGNORECASE
    )
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    HTML_ENTITY_PATTERN = re.compile(r'&[a-zA-Z]+;|&#\d+;')
    CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]')
    WHITESPACE_PATTERN = re.compile(r'[ \t]+')
    NEWLINE_PATTERN = re.compile(r'\n{3,}')
    EXCESSIVE_PUNCTUATION_PATTERN = re.compile(r'([!?.])\1{2,}')
    ACCENTED_CHARACTERS = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a', 'æ': 'ae',
        'ç': 'c', 'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i', 'ð': 'd',
        'ñ': 'n', 'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ø': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u', 'ý': 'y', 'ÿ': 'y',
        'ß': 'ss', 'þ': 'th', 'æ': 'ae', 'œ': 'oe',
        'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A', 'Æ': 'AE',
        'Ç': 'C', 'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
        'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I', 'Ð': 'D',
        'Ñ': 'N', 'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O', 'Ø': 'O',
        'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U', 'Ý': 'Y', 'Ÿ': 'Y',
    }

    def __init__(
        self,
        default_level: CleanLevel = CleanLevel.NORMAL,
        preserve_newlines: bool = True,
        strip_whitespace: bool = True
    ):
        """
        初始化文本清理器

        Args:
            default_level: 默认清理级别
            preserve_newlines: 是否保留换行符
            strip_whitespace: 是否去除首尾空白
        """
        self.default_level = default_level
        self.preserve_newlines = preserve_newlines
        self.strip_whitespace = strip_whitespace

    def clean(
        self,
        text: str,
        level: Optional[CleanLevel] = None,
        remove_urls: bool = False,
        remove_emails: bool = False,
        remove_phones: bool = False,
        remove_html: bool = False,
        remove_accents: bool = False,
        lowercase: bool = False,
        remove_emojis: bool = False,
        remove_excessive_punctuation: bool = False,
        max_punctuation: int = 2,
        normalize_whitespace: bool = True,
        preserve_newlines: Optional[bool] = None,
        strip: bool = True
    ) -> CleanResult:
        """
        清理文本

        Args:
            text: 待清理的文本
            level: 清理级别（如果指定，忽略其他选项）
            remove_urls: 是否移除URL
            remove_emails: 是否移除邮箱
            remove_phones: 是否移除电话号码
            remove_html: 是否移除HTML标签
            remove_accents: 是否移除重音字符
            lowercase: 是否转为小写
            remove_emojis: 是否移除表情符号
            remove_excessive_punctuation: 是否移除过多标点
            max_punctuation: 最大连续标点数
            normalize_whitespace: 是否规范化空白
            preserve_newlines: 是否保留换行
            strip: 是否去除首尾空白

        Returns:
            CleanResult: 清理结果
        """
        if text is None:
            return CleanResult(original="", cleaned="", level=level or self.default_level)

        if not text:
            return CleanResult(original=text, cleaned=text, level=level or self.default_level)

        original = text
        changes = []

        # 确定清理级别
        if level:
            preserve_newlines = self.preserve_newlines if preserve_newlines is None else preserve_newlines
            strip = self.strip_whitespace if strip is None else strip
        else:
            level = self.default_level
            if preserve_newlines is None:
                preserve_newlines = self.preserve_newlines

        # 如果指定了级别，应用预设
        if level:
            if level == CleanLevel.MINIMAL:
                # 最小清理
                pass
            elif level == CleanLevel.NORMAL:
                # 普通清理
                remove_html = remove_html or True
                normalize_whitespace = True
            elif level == CleanLevel.THOROUGH:
                # 彻底清理
                remove_urls = remove_urls or True
                remove_emails = remove_emails or True
                remove_html = remove_html or True
                normalize_whitespace = True
                remove_control_chars = True
            elif level == CleanLevel.SANITIZE:
                # 消毒处理
                remove_urls = True
                remove_emails = True
                remove_phones = True
                remove_html = True
                remove_emojis = True
                normalize_whitespace = True
                lowercase = True

        # 执行各项清理

        # 去除HTML标签
        if remove_html:
            new_text = self.HTML_TAG_PATTERN.sub(' ', text)
            if new_text != text:
                changes.append({"type": "html_tags_removed", "count": len(self.HTML_TAG_PATTERN.findall(text))})
                text = new_text

            # 转换HTML实体
            new_text = html.unescape(text)
            if new_text != text:
                changes.append({"type": "html_entities_decoded"})
                text = new_text

        # 去除URL
        if remove_urls:
            urls = self.URL_PATTERN.findall(text)
            if urls:
                changes.append({"type": "urls_removed", "count": len(urls)})
                text = self.URL_PATTERN.sub(' ', text)

        # 去除邮箱
        if remove_emails:
            emails = self.EMAIL_PATTERN.findall(text)
            if emails:
                changes.append({"type": "emails_removed", "count": len(emails)})
                text = self.EMAIL_PATTERN.sub(' ', text)

        # 去除电话号码（保守检测）
        if remove_phones:
            # 只移除匹配的电话号码模式
            phone_matches = self.PHONE_PATTERN.findall(text)
            # 过滤掉太短的匹配
            valid_phones = [m for m in phone_matches if len(re.sub(r'\D', '', m)) >= 7]
            if valid_phones:
                changes.append({"type": "phones_removed", "count": len(valid_phones)})
                for phone in valid_phones:
                    text = text.replace(phone, ' ')

        # 去除控制字符
        new_text = self.CONTROL_CHAR_PATTERN.sub('', text)
        if new_text != text:
            changes.append({"type": "control_chars_removed"})
            text = new_text

        # 去除重音字符
        if remove_accents:
            new_text = self._remove_accents(text)
            if new_text != text:
                changes.append({"type": "accents_removed"})
                text = new_text

        # 转小写
        if lowercase:
            new_text = text.lower()
            if new_text != text:
                changes.append({"type": "lowercased"})
                text = new_text

        # 去除表情符号
        if remove_emojis:
            new_text = self._remove_emojis(text)
            if new_text != text:
                changes.append({"type": "emojis_removed"})
                text = new_text

        # 规范化空白
        if normalize_whitespace:
            # 先规范化制表符等
            text = text.replace('\t', ' ')
            # 合并多个空格
            new_text = self.WHITESPACE_PATTERN.sub(' ', text)
            if new_text != text:
                changes.append({"type": "whitespace_normalized"})
                text = new_text

        # 处理换行符
        if preserve_newlines:
            # 保留换行，但合并多个换行
            text = self.NEWLINE_PATTERN.sub('\n\n', text)
        else:
            # 将换行替换为空格
            text = text.replace('\n', ' ').replace('\r', ' ')
            changes.append({"type": "newlines_removed"})

        # 去除过多标点
        if remove_excessive_punctuation:
            new_text = self.EXCESSIVE_PUNCTUATION_PATTERN.sub(r'\1' * max_punctuation, text)
            if new_text != text:
                changes.append({"type": "excessive_punctuation_removed"})
                text = new_text

        # 最终strip
        if strip:
            new_text = text.strip()
            if new_text != text:
                text = new_text

        return CleanResult(
            original=original,
            cleaned=text,
            changes=changes,
            level=level
        )

    def _remove_accents(self, text: str) -> str:
        """移除重音字符"""
        return ''.join(self.ACCENTED_CHARACTERS.get(c, c) for c in text)

    def _remove_emojis(self, text: str) -> str:
        """移除表情符号"""
        # Emoji Unicode ranges
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"  # enclosed characters
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002600-\U000026FF"  # Miscellaneous Symbols
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', text)

    def clean_for_search(self, text: str) -> str:
        """为搜索清理文本（优化搜索相关性）"""
        # 去除搜索噪声词
        noise_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        words = text.split()
        filtered = [w for w in words if w.lower() not in noise_words]
        return ' '.join(filtered)

    def clean_for_display(self, text: str, max_length: Optional[int] = None) -> str:
        """为显示清理文本"""
        result = self.clean(text, level=CleanLevel.NORMAL)
        cleaned = result.cleaned

        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rsplit(' ', 1)[0] + '...'

        return cleaned

    def truncate(self, text: str, max_length: int, suffix: str = '...') -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix

    def normalize_quotes(self, text: str) -> str:
        """规范化引号"""
        # 中文引号转换
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        # 英文引号统一为半角
        text = text.replace('', "'").replace('', "'")
        return text

    def normalize_dashes(self, text: str) -> str:
        """规范化破折号"""
        # 转换多种破折号为标准短横线
        text = text.replace('—', '-').replace('–', '-').replace('―', '-')
        # 合并多个破折号
        text = re.sub(r'-{3,}', '-', text)
        return text


def clean_text(
    text: str,
    level: CleanLevel = CleanLevel.NORMAL,
    **kwargs
) -> CleanResult:
    """便捷函数：清理文本"""
    cleaner = TextCleaner()
    return cleaner.clean(text, level=level, **kwargs)


def sanitize_input(text: str) -> str:
    """便捷函数：消毒处理用户输入"""
    if text is None:
        return ""
    cleaner = TextCleaner()
    result = cleaner.clean(text, level=CleanLevel.SANITIZE)
    return result.cleaned