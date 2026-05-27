"""
学术文档分块器 - Academic Document Chunker

支持多种分块策略：
- 递归字符分块 (recursive)
- 语义分块 (semantic)
- 父子块分块 (parent_child)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.agents_v2.logging_config import get_logging_logger

import re

logger = get_logging_logger(__name__)


@dataclass
class Chunk:
    """文档块"""
    content: str
    chunk_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    position: int = 0


class AcademicChunker:
    """学术文档分块器

    专门针对学术文档结构进行优化，保持语义完整性。
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        split_by: str = "semantic",
        min_chunk_size: int = 50,
    ):
        """初始化分块器

        Args:
            chunk_size: 目标块大小（token近似）
            chunk_overlap: 块之间的重叠大小
            split_by: 分块策略 ("recursive", "semantic", "parent_child")
            min_chunk_size: 最小块大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.split_by = split_by
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """分块处理

        Args:
            text: 文档文本
            metadata: 文档元数据

        Returns:
            List[Chunk]: 分块结果
        """
        if not text or len(text.strip()) == 0:
            return []

        metadata = metadata or {}

        if self.split_by == "recursive":
            return self._recursive_chunk(text, metadata)
        elif self.split_by == "semantic":
            return self._semantic_chunk(text, metadata)
        elif self.split_by == "parent_child":
            return self._parent_child_chunk(text, metadata)
        else:
            return self._recursive_chunk(text, metadata)

    def _recursive_chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """递归字符分块

        优先按语义边界（段落、句子）分割，
        再按字符数限制分块。
        """
        chunks = []

        # 首先尝试按段落分割
        paragraphs = self._split_by_paragraphs(text)

        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)

            # 如果单个段落超过最大大小，进一步分割
            if para_tokens > self.chunk_size * 1.5:
                # 保存当前chunk
                if current_chunk:
                    chunks.append(self._create_chunk(
                        "\n".join(current_chunk),
                        metadata,
                        len(chunks)
                    ))
                    current_chunk = []
                    current_tokens = 0

                # 分割大段落
                sub_chunks = self._split_long_paragraph(para, metadata, len(chunks))
                chunks.extend(sub_chunks)
                continue

            # 检查是否超出大小
            if current_tokens + para_tokens > self.chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        "\n".join(current_chunk),
                        metadata,
                        len(chunks)
                    ))

                    # 开始新chunk，保留overlap
                    overlap_text = current_chunk[-1][-self.chunk_overlap:] if current_chunk else ""
                    current_chunk = [overlap_text + "\n" + para]
                    current_tokens = self._estimate_tokens(current_chunk[0])
                else:
                    current_chunk = [para]
                    current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

        # 处理最后一个chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                "\n".join(current_chunk),
                metadata,
                len(chunks)
            ))

        return chunks

    def _semantic_chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """语义分块

        尊重学术文档结构，按章节、段落分割。
        """
        chunks = []

        # 按章节分割
        sections = self._split_by_sections(text)

        for section in sections:
            section_text = section["text"]
            section_meta = section.get("metadata", {})

            # 如果章节太大，进一步分割
            if self._estimate_tokens(section_text) > self.chunk_size * 2:
                # 按段落分割
                paragraphs = self._split_by_paragraphs(section_text)
                current_chunk = []
                current_tokens = 0

                for para in paragraphs:
                    para_tokens = self._estimate_tokens(para)

                    if current_tokens + para_tokens > self.chunk_size:
                        if current_chunk:
                            chunk_text = "\n".join(current_chunk)
                            chunk_meta = {**metadata, **section_meta}
                            chunks.append(self._create_chunk(chunk_text, chunk_meta, len(chunks)))

                            # overlap
                            overlap_text = current_chunk[-1][-self.chunk_overlap:] if current_chunk else ""
                            current_chunk = [overlap_text + "\n" + para]
                            current_tokens = self._estimate_tokens(current_chunk[0])
                        else:
                            current_chunk = [para]
                            current_tokens = para_tokens
                    else:
                        current_chunk.append(para)
                        current_tokens += para_tokens

                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunk_meta = {**metadata, **section_meta}
                    chunks.append(self._create_chunk(chunk_text, chunk_meta, len(chunks)))
            else:
                # 章节大小合适，直接添加
                chunk_meta = {**metadata, **section_meta}
                chunks.append(self._create_chunk(section_text, chunk_meta, len(chunks)))

        return chunks

    def _parent_child_chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """父子块分块

        大块作为父块，包含多个子块的引用。
        """
        chunks = []

        # 先做语义分块
        semantic_chunks = self._semantic_chunk(text, metadata)

        # 创建父块（更大的块）
        parent_chunks = []
        current_parent = []
        current_parent_tokens = 0

        for chunk in semantic_chunks:
            if current_parent_tokens + chunk.token_count > self.chunk_size * 3:
                # 创建父块
                if current_parent:
                    parent_text = "\n".join(c.content for c in current_parent)
                    parent_meta = {
                        **metadata,
                        "child_ids": [c.chunk_id for c in current_parent],
                        "is_parent": True,
                    }
                    parent_chunks.append(self._create_chunk(parent_text, parent_meta, len(parent_chunks)))

                current_parent = [chunk]
                current_parent_tokens = chunk.token_count
            else:
                current_parent.append(chunk)
                current_parent_tokens += chunk.token_count

        # 处理最后一个父块
        if current_parent:
            parent_text = "\n".join(c.content for c in current_parent)
            parent_meta = {
                **metadata,
                "child_ids": [c.chunk_id for c in current_parent],
                "is_parent": True,
            }
            parent_chunks.append(self._create_chunk(parent_text, parent_meta, len(parent_chunks)))

        # 合并父子块
        chunks.extend(parent_chunks)
        chunks.extend(semantic_chunks)

        return chunks

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落分割"""
        # 处理换行符统一
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 按双换行或单换行分割
        paragraphs = re.split(r"\n{2,}", text)

        # 清理空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # 如果没有找到段落，按单换行分割
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        return paragraphs

    def _split_by_sections(self, text: str) -> List[Dict[str, Any]]:
        """按章节分割

        识别学术文档的章节结构。
        """
        sections = []

        # 章节标题模式
        section_patterns = [
            # 数字编号: 1. xxx, 2. xxx
            r"(?m)^(\d+\.\s+[^\n]+)\n",
            # 中文: 一、xxx, 二、xxx
            r"(?m)^([一二三四五六七八九十]+、\s*[^\n]+)\n",
            # Markdown: # xxx, ## xxx
            r"(?m)^(#{1,6}\s+[^\n]+)\n",
            # 英文大写标题
            r"(?m)^([A-Z][A-Z\s]{3,})\n",
        ]

        section_boundaries = []

        for pattern in section_patterns:
            for match in re.finditer(pattern, text):
                title = match.group(1).strip()
                if len(title) > 2:
                    section_boundaries.append({
                        "position": match.start(),
                        "title": title,
                        "level": len(match.group(0)) - len(match.group(0).lstrip("# ")),
                    })

        # 按位置排序
        section_boundaries.sort(key=lambda x: x["position"])

        # 去除嵌套的重复标题
        filtered_boundaries = []
        for boundary in section_boundaries:
            if not filtered_boundaries or boundary["position"] > filtered_boundaries[-1]["position"] + 10:
                filtered_boundaries.append(boundary)

        # 提取每个章节的内容
        for i, boundary in enumerate(filtered_boundaries):
            start = boundary["position"]
            if i + 1 < len(filtered_boundaries):
                end = filtered_boundaries[i + 1]["position"]
            else:
                end = len(text)

            section_text = text[start:end].strip()

            sections.append({
                "text": section_text,
                "title": boundary["title"],
                "level": boundary.get("level", 1),
                "metadata": {
                    "section_title": boundary["title"],
                    "section_level": boundary.get("level", 1),
                }
            })

        # 如果没有识别到章节，返回整个文本
        if not sections:
            sections = [{"text": text, "title": "Full Document", "level": 0, "metadata": {}}]

        return sections

    def _split_long_paragraph(self, text: str, metadata: Dict[str, Any], start_id: int) -> List[Chunk]:
        """分割长段落

        尝试按句子边界分割。
        """
        # 按句子分割
        sentences = re.split(r"(?<=[。！？.!?])\s+", text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)

            if current_tokens + sentence_tokens > self.chunk_size:
                if current_chunk:
                    chunk_text = "".join(current_chunk)
                    chunks.append(self._create_chunk(chunk_text, metadata, start_id + len(chunks)))

                    # overlap
                    overlap_text = current_chunk[-1][-self.chunk_overlap:] if current_chunk else ""
                    current_chunk = [overlap_text + sentence]
                    current_tokens = self._estimate_tokens(current_chunk[0])
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        if current_chunk:
            chunks.append(self._create_chunk("".join(current_chunk), metadata, start_id + len(chunks)))

        return chunks if chunks else [self._create_chunk(text[:self.chunk_size], metadata, start_id)]

    def _create_chunk(self, content: str, metadata: Dict[str, Any], index: int) -> Chunk:
        """创建Chunk对象"""
        chunk_id = f"chunk_{metadata.get('doc_id', 'doc')}_{index}"

        return Chunk(
            content=content,
            chunk_id=chunk_id,
            metadata={
                **metadata,
                "index": index,
            },
            token_count=self._estimate_tokens(content),
            position=index,
        )

    def _estimate_tokens(self, text: str) -> int:
        """估算token数量

        简单估算：中文每字约1.5 tokens，英文每词约1.3 tokens。
        更精确的估算需要使用tiktoken等库。
        """
        if not text:
            return 0

        # 统计中英文混合文本的token
        chinese_chars = len(re.findall(r"[一-鿿]", text))
        english_words = len(re.findall(r"[a-zA-Z]+", text))
        other_chars = len(text) - chinese_chars - english_words

        # 估算
        estimated = chinese_chars * 1.5 + english_words * 1.3 + other_chars * 1.0

        return int(estimated)


# 便捷函数
def chunk_text(text: str, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> List[Chunk]:
    """分块的便捷函数"""
    chunker = AcademicChunker(**kwargs)
    return chunker.chunk(text, metadata)