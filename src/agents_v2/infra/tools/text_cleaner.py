"""
Text Cleaner - 文本清洗器

清洗文本中的噪声、格式问题和无关字符。
"""
from typing import Any, Dict, List, Optional, Tuple
import re
import html


class TextCleaner:
    """
    文本清洗器

    功能:
    - 移除HTML标签
    - 清理多余空白
    - 标准化标点
    - 移除控制字符

    使用示例:
        cleaner = TextCleaner()
        cleaned = cleaner.clean("some <b>text</b>   with  extra   spaces")
        # 结果: "some text with extra spaces"
    """

    # 控制字符正则
    CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

    # 多余空白正则
    MULTI_SPACE = re.compile(r'\s+')

    # HTML标签正则
    HTML_TAG = re.compile(r'<[^>]+>')

    # URL正则
    URL_PATTERN = re.compile(r'https?://\S+')

    def __init__(self, remove_urls: bool = False, strip_html: bool = True):
        """
        初始化清洗器

        Args:
            remove_urls: 是否移除URL
            strip_html: 是否移除HTML标签
        """
        self.remove_urls = remove_urls
        self.strip_html = strip_html

    def clean(self, text: str) -> str:
        """
        清洗文本

        Args:
            text: 输入文本

        Returns:
            str: 清洗后的文本
        """
        if not text:
            return ""

        # 1. HTML解码
        text = html.unescape(text)

        # 2. 移除HTML标签
        if self.strip_html:
            text = self.HTML_TAG.sub(' ', text)

        # 3. 移除控制字符
        text = self.CONTROL_CHARS.sub('', text)

        # 4. 处理URL
        if self.remove_urls:
            text = self.URL_PATTERN.sub('', text)

        # 5. 标准化空白
        text = self.MULTI_SPACE.sub(' ', text)

        # 6. 清理首尾空白
        text = text.strip()

        return text

    def clean_batch(self, texts: List[str]) -> List[str]:
        """批量清洗"""
        return [self.clean(t) for t in texts]

    def remove_special_chars(self, text: str, keep_chars: str = "") -> str:
        """
        移除特殊字符

        Args:
            text: 输入文本
            keep_chars: 要保留的额外字符

        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""

        # 允许的字符：字母、数字、常用标点、空白、用户指定字符
        allowed = set(f"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?;:'\"-() {{}}{keep_chars}")

        result = []
        for char in text:
            if char in allowed or char.isspace():
                result.append(char)
            elif char in ['\n', '\t', '\r']:
                result.append(' ')

        return ''.join(result).strip()

    def normalize_punctuation(self, text: str) -> str:
        """
        规范化标点符号

        Args:
            text: 输入文本

        Returns:
            str: 规范化后的文本
        """
        if not text:
            return ""

        # 全角转半角
        result = []
        for char in text:
            code = ord(char)
            if 0xFF01 <= code <= 0xFF5E:  # 全角字符范围
                result.append(chr(code - 0xFEE0))
            elif char == '　':  # 全角空格
                result.append(' ')
            else:
                result.append(char)

        text = ''.join(result)

        # 标准化引号
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # 移除标点前的空格
        text = re.sub(r'\s+([.,!?;:)])', r'\1', text)

        # 标点后加空格（如果没有）
        text = re.sub(r'([.,!?;)])([a-zA-Z])', r'\1 \2', text)

        # 规范化逗号周围的空格
        text = re.sub(r'([,;])\s+', r'\1 ', text)
        text = re.sub(r'\s+([,;])', r' \1', text)

        return text

    def get_stats(self, text: str) -> Dict[str, Any]:
        """
        获取文本统计信息

        Returns:
            Dict: 统计信息
        """
        if not text:
            return {
                "length": 0,
                "words": 0,
                "chars": 0,
                "has_html": False,
                "has_urls": False,
                "has_control_chars": False
            }

        return {
            "length": len(text),
            "words": len(text.split()),
            "chars": len(text.replace(' ', '')),
            "has_html": bool(self.HTML_TAG.search(text)),
            "has_urls": bool(self.URL_PATTERN.search(text)),
            "has_control_chars": bool(self.CONTROL_CHARS.search(text))
        }


def clean_text(text: str, **kwargs) -> str:
    """便捷函数：清洗文本"""
    cleaner = TextCleaner(**kwargs)
    return cleaner.clean(text)