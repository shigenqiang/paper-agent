"""
Text Segmenter - 文本分段器

将长文本分割成语义连贯的段落。
"""
from typing import Any, Dict, List, Optional, Tuple
import re


class TextSegmenter:
    """
    文本分段器

    功能:
    - 按段落分割
    - 按句子分割
    - 按主题分割
    - 保留上下文信息

    使用示例:
        segmenter = TextSegmenter()
        segments = segmenter.segment(text, max_length=500)
    """

    # 段落分隔符
    PARAGRAPH_SEP = re.compile(r'\n\s*\n')

    # 句子分隔符
    SENTENCE_SEP = re.compile(r'(?<=[。！？.!?])\s+')

    def __init__(
        self,
        max_segment_length: int = 1000,
        overlap: int = 50,
        min_segment_length: int = 50
    ):
        """
        初始化分段器

        Args:
            max_segment_length: 最大段落长度
            overlap: 重叠字符数
            min_segment_length: 最小段落长度
        """
        self.max_segment_length = max_segment_length
        self.overlap = overlap
        self.min_segment_length = min_segment_length

    def segment(self, text: str, mode: str = "paragraph") -> List[Dict[str, Any]]:
        """
        分割文本

        Args:
            text: 输入文本
            mode: 分割模式 ("paragraph", "sentence", "fixed")

        Returns:
            List[Dict]: 段落列表，每项包含text和metadata
        """
        if not text:
            return []

        if mode == "paragraph":
            return self._segment_by_paragraph(text)
        elif mode == "sentence":
            return self._segment_by_sentence(text)
        elif mode == "fixed":
            return self._segment_fixed(text)
        else:
            return self._segment_by_paragraph(text)

    def _segment_by_paragraph(self, text: str) -> List[Dict[str, Any]]:
        """按段落分割"""
        paragraphs = self.PARAGRAPH_SEP.split(text)
        segments = []
        current_pos = 0

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue

            # 如果段落过长，进一步分割
            if len(para) > self.max_segment_length:
                sub_segments = self._segment_fixed(para)
                for seg in sub_segments:
                    seg["start_pos"] = current_pos
                    current_pos += len(seg["text"]) + 1
                    segments.append(seg)
            else:
                segments.append({
                    "text": para,
                    "start_pos": current_pos,
                    "end_pos": current_pos + len(para),
                    "index": len(segments),
                    "is_truncated": False
                })
                current_pos += len(para) + 1

        return self._merge_short_segments(segments)

    def _segment_by_sentence(self, text: str) -> List[Dict[str, Any]]:
        """按句子分割"""
        sentences = self.SENTENCE_SEP.split(text)
        segments = []
        current_text = ""
        current_pos = 0

        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                continue

            # 如果加上这句话会超过限制
            if len(current_text) + len(sent) > self.max_segment_length:
                # 保存当前段落
                if current_text:
                    segments.append({
                        "text": current_text.strip(),
                        "start_pos": current_pos,
                        "end_pos": current_pos + len(current_text),
                        "index": len(segments),
                        "is_truncated": False
                    })
                    current_pos += len(current_text)

                # 如果单句话过长，按固定长度分割
                if len(sent) > self.max_segment_length:
                    current_text = sent
                    while len(current_text) > self.max_segment_length:
                        segments.append({
                            "text": current_text[:self.max_segment_length],
                            "start_pos": current_pos,
                            "end_pos": current_pos + self.max_segment_length,
                            "index": len(segments),
                            "is_truncated": True
                        })
                        current_pos += self.max_segment_length - self.overlap
                        current_text = current_text[self.max_segment_length - self.overlap:]
                    current_text = sent
                else:
                    current_text = sent
            else:
                current_text += " " + sent if current_text else sent

        # 保存最后一段
        if current_text.strip():
            segments.append({
                "text": current_text.strip(),
                "start_pos": current_pos,
                "end_pos": current_pos + len(current_text),
                "index": len(segments),
                "is_truncated": False
            })

        return segments

    def _segment_fixed(self, text: str) -> List[Dict[str, Any]]:
        """按固定长度分割"""
        if not text:
            return []

        segments = []
        start = 0

        while start < len(text):
            end = start + self.max_segment_length
            segment_text = text[start:end]

            # 尝试在句子边界处断开
            if end < len(text):
                break_point = self._find_break_point(segment_text)
                if break_point > self.min_segment_length:
                    segment_text = segment_text[:break_point]
                    end = start + break_point

            segments.append({
                "text": segment_text,
                "start_pos": start,
                "end_pos": end,
                "index": len(segments),
                "is_truncated": end < len(text)
            })

            start = end - self.overlap if end < len(text) else end

        return segments

    def _find_break_point(self, text: str) -> int:
        """找到合适的断点（句子边界）"""
        # 向前找最后一个标点
        for sep in ['。', '！', '？', '.', '!', '?', '，', ',', '；', ';']:
            idx = text.rfind(sep)
            if idx > self.min_segment_length // 2:
                return idx + 1

        return -1

    def _merge_short_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并过短的段落"""
        if not segments:
            return []

        merged = [segments[0]]

        for seg in segments[1:]:
            last = merged[-1]

            # 如果两个段落都短，合并
            if len(last["text"]) < self.min_segment_length and len(seg["text"]) < self.min_segment_length:
                merged[-1] = {
                    "text": last["text"] + " " + seg["text"],
                    "start_pos": last["start_pos"],
                    "end_pos": seg["end_pos"],
                    "index": last["index"],
                    "is_truncated": seg["is_truncated"]
                }
            else:
                merged.append(seg)

        # 更新索引
        for i, seg in enumerate(merged):
            seg["index"] = i

        return merged

    def segment_with_context(
        self,
        text: str,
        context_before: str = "",
        context_after: str = ""
    ) -> List[Dict[str, Any]]:
        """
        带上下文的分割

        Args:
            text: 输入文本
            context_before: 前置上下文
            context_after: 后置上下文

        Returns:
            List[Dict]: 段落列表
        """
        segments = self.segment(text)

        # 添加上下文
        for i, seg in enumerate(segments):
            seg["context"] = {
                "before": context_before if i == 0 else "",
                "after": context_after if i == len(segments) - 1 else ""
            }

        return segments


def segment_text(text: str, **kwargs) -> List[str]:
    """便捷函数：分割文本"""
    segmenter = TextSegmenter(**kwargs)
    segments = segmenter.segment(text)
    return [s["text"] for s in segments]