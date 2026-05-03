"""
文本预处理器
Text Preprocessor
"""

import re
from typing import List, Tuple, Optional


class TextPreprocessor:
    """文本预处理器"""

    def __init__(self, language: str = "en"):
        self.language = language

        # 英文停用词
        self.en_stopwords = {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
            'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him',
            'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its',
            'itself', 'they', 'them', 'their', 'theirs', 'themselves',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
            'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an',
            'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while',
            'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
            'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there',
            'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can',
            'will', 'just', 'don', 'should', 'now'
        }

        # 中文停用词（常用）
        self.zh_stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '它',
            '来', '中', '大', '为', '对', '与', '但', '或', '等', '于'
        }

    def preprocess(self, text: str) -> str:
        """预处理文本"""
        if not text:
            return ""

        # 移除特殊字符
        text = self.remove_special_chars(text)

        # 规范化空白字符
        text = self.normalize_whitespace(text)

        # 移除HTML标签
        text = self.remove_html_tags(text)

        return text.strip()

    def split_sentences(self, text: str) -> List[str]:
        """分句"""
        if not text:
            return []

        # 英文句子分割
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'

        # 使用换行符作为辅助分割
        lines = text.split('\n')
        sentences = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 进一步分割
            parts = re.split(sentence_pattern, line)
            sentences.extend([s.strip() for s in parts if s.strip()])

        return sentences

    def split_paragraphs(self, text: str) -> List[str]:
        """分段落"""
        if not text:
            return []

        # 按连续换行符分割
        paragraphs = re.split(r'\n\s*\n', text)

        return [p.strip() for p in paragraphs if p.strip()]

    def tokenize(self, text: str) -> List[str]:
        """分词"""
        if not text:
            return []

        text = self.preprocess(text)

        if self.language == "en":
            # 英文分词：按空格和标点分割
            tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower())
            return [t for t in tokens if t not in self.en_stopwords and len(t) > 1]
        else:
            # 中文分词：简单按字符分割（实际应用中应使用jieba）
            chars = list(text)
            return [c for c in chars if not self._is_stopword(c)]

    def _is_stopword(self, char: str) -> bool:
        """检查是否为停用词"""
        return char in self.zh_stopwords

    @staticmethod
    def remove_special_chars(text: str, keep_chinese: bool = True) -> str:
        """移除特殊字符"""
        if keep_chinese:
            # 保留中英文、数字、部分标点
            pattern = r'[^\w\s.,;:!?，。；：！？、一-鿿-]'
        else:
            # 只保留字母、数字和基本标点
            pattern = r'[^\w\s.,;:!?]'

        return re.sub(pattern, ' ', text)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """规范化空白字符"""
        return re.sub(r'\s+', ' ', text)

    @staticmethod
    def remove_html_tags(text: str) -> str:
        """移除HTML标签"""
        return re.sub(r'<[^>]+>', '', text)

    def extract_numbers(self, text: str) -> List[str]:
        """提取数字"""
        return re.findall(r'\d+\.?\d*', text)

    def extract_urls(self, text: str) -> List[str]:
        """提取URL"""
        url_pattern = r'https?://[^\s]+'
        return re.findall(url_pattern, text)

    def extract_emails(self, text: str) -> List[str]:
        """提取邮箱"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)

    def detect_language(self, text: str) -> str:
        """检测语言"""
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        total_chars = len(text)

        if total_chars == 0:
            return "en"

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.3:
            return "zh"
        else:
            return "en"

    def clean_reference_format(self, text: str) -> str:
        """清理参考文献格式"""
        # 移除多余的空格
        text = re.sub(r'\[\s]+', ' ', text)

        # 规范化DOI格式
        text = re.sub(r'doi:\s*', 'doi:', text)
        text = re.sub(r'DOI:\s*', 'doi:', text)

        return text.strip()

    def extract_citations(self, text: str) -> List[str]:
        """提取引用标记"""
        # 提取方括号引用 [1], [2,3], [1-5]
        bracket_citations = re.findall(r'\[[\d,\-\s]+\]', text)

        # 提取圆括号引用 (Author, 2024)
        paren_citations = re.findall(r'\([A-Z][a-z]+ et al\., \d{4}\)', text)

        return bracket_citations + paren_citations
