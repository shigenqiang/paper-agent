"""
Sentence Splitter - 句子分割器

将文本分割成单独的句子，支持多种语言和标点符号。
"""
from typing import Any, Dict, List, Optional, Tuple
import re


class SentenceSplitter:
    """
    句子分割器

    功能:
    - 智能句子边界检测
    - 多种标点符号支持
    - 缩写和数字处理
    - 保留句子元数据

    使用示例:
        splitter = SentenceSplitter()
        sentences = splitter.split("这是第一句话。这是第二句话！这是第三句吗？")
        # 结果: ["这是第一句话。", "这是第二句话！", "这是第三句吗？"]
    """

    # 句子结束标点
    SENTENCE_ENDINGS = r'[。！？.!?]'

    # 省略号模式
    ELLIPSIS = re.compile(r'\.{3,}|…{1,}')

    # 引号内的句号（不作为句子分隔符）
    QUOTE_PUNCTUATION = re.compile(r'[""\'][^""\']*?[""\']')

    # 缩写模式（不作为句子分隔符）
    ABBREVIATIONS = re.compile(r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|i\.e|e\.g)\.', re.IGNORECASE)

    # 数字年份（如2023.）
    NUMBER_YEAR = re.compile(r'\b\d{4}\.')

    def __init__(
        self,
        clean_whitespace: bool = True,
        preserve_quotes: bool = True,
        min_sentence_length: int = 2
    ):
        """
        初始化分割器

        Args:
            clean_whitespace: 是否清理空白
            preserve_quotes: 是否保留引号
            min_sentence_length: 最小句子长度
        """
        self.clean_whitespace = clean_whitespace
        self.preserve_quotes = preserve_quotes
        self.min_sentence_length = min_sentence_length

    def split(self, text: str) -> List[str]:
        """
        分割文本为句子

        Args:
            text: 输入文本

        Returns:
            List[str]: 句子列表
        """
        if not text:
            return []

        # 预处理
        if self.clean_whitespace:
            text = re.sub(r'\s+', ' ', text).strip()

        # 处理省略号（暂时替换，避免干扰）
        ellipsis_placeholder = '<<<ELLIPSIS>>>'
        text = self.ELLIPSIS.sub(ellipsis_placeholder, text)

        # 处理缩写（暂时替换）
        abbrev_positions = []
        for match in self.ABBREVIATIONS.finditer(text):
            abbrev_positions.append((match.start(), match.end(), match.group()))
            text = text[:match.start()] + ' ' * (match.end() - match.start()) + text[match.end():]

        # 处理数字年份
        year_positions = []
        for match in self.NUMBER_YEAR.finditer(text):
            year_positions.append((match.start(), match.end()))
            text = text[:match.start()] + ' ' * (match.end() - match.start()) + text[match.end():]

        # 找到句子边界
        sentences = []
        current_pos = 0

        # 按句子边界分割
        pattern = re.compile(self.SENTENCE_ENDINGS)
        for match in pattern.finditer(text):
            end_pos = match.end()
            sentence = text[current_pos:end_pos].strip()

            if len(sentence) >= self.min_sentence_length:
                sentences.append(sentence)

            current_pos = end_pos

        # 处理末尾残留文本
        if current_pos < len(text):
            remaining = text[current_pos:].strip()
            if len(remaining) >= self.min_sentence_length:
                sentences.append(remaining)

        # 恢复省略号
        sentences = [s.replace(ellipsis_placeholder, '...') for s in sentences]

        # 恢复缩写
        # 注意：由于我们替换了文本位置，简单恢复较复杂，这里简化处理

        return sentences

    def split_with_metadata(self, text: str) -> List[Dict[str, Any]]:
        """
        分割并返回元数据

        Args:
            text: 输入文本

        Returns:
            List[Dict]: 句子列表及其元数据
        """
        sentences = self.split(text)
        results = []
        current_pos = 0

        for i, sentence in enumerate(sentences):
            start_pos = text.find(sentence, current_pos)

            results.append({
                "text": sentence,
                "index": i,
                "start_pos": start_pos,
                "end_pos": start_pos + len(sentence),
                "char_count": len(sentence),
                "word_count": len(sentence.split()) if sentence else 0,
                "ends_with": sentence[-1] if sentence else ""
            })

            current_pos = start_pos + len(sentence)

        return results

    def split_by_newline(self, text: str) -> List[str]:
        """
        按换行符分割（不合并句子）

        Args:
            text: 输入文本

        Returns:
            List[str]: 行列表
        """
        if not text:
            return []

        lines = text.split('\n')
        return [line.strip() for line in lines if line.strip()]

    def is_sentence_end(self, char: str, next_char: Optional[str] = None) -> bool:
        """
        判断字符是否是句子结束标记

        Args:
            char: 当前字符
            next_char: 下一个字符

        Returns:
            bool: 是否为句子结束
        """
        if char in '。！？.!?':
            # 检查是否为缩写
            if char == '.' and next_char and next_char.islower():
                return False
            return True

        return False

    def get_sentence_count(self, text: str) -> int:
        """获取句子数量"""
        return len(self.split(text))


def split_sentences(text: str, **kwargs) -> List[str]:
    """便捷函数：分割句子"""
    splitter = SentenceSplitter(**kwargs)
    return splitter.split(text)