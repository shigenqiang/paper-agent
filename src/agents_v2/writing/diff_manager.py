"""
Diff/Patch Manager - 文本对比与补丁管理

借鉴 PaperDebugger 的 Diff 补丁机制，提供：
1. Unified diff 生成（标准 unified diff 格式）
2. 结构化差异表示（DiffView，适合前端渲染）
3. 补丁应用（apply patch to original text）
4. 变更摘要（统计新增/删除/修改行数）
5. HITL 集成：在人工审核节点展示版本间差异

使用示例:
    from agents_v2.writing.diff_manager import DiffManager

    manager = DiffManager()

    # 生成 unified diff
    diff_text = manager.unified_diff(old_text, new_text, "v1", "v2")

    # 生成结构化差异（前端渲染用）
    view = manager.diff_view(old_text, new_text)

    # 应用补丁
    patched = manager.apply_patch(old_text, patch_text)

    # 变更摘要
    summary = manager.change_summary(old_text, new_text)
"""
from src.agents_v2.logging_config import get_logging_logger

import difflib

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

logger = get_logging_logger(__name__)


class DiffLineType(str, Enum):
    """差异行类型"""
    CONTEXT = "context"     # 未变更行
    ADDED = "added"         # 新增行
    REMOVED = "removed"     # 删除行
    SEPARATOR = "separator" # 分隔符 (@@ ... @@)


@dataclass
class DiffLine:
    """单行差异"""
    type: DiffLineType
    content: str
    old_line_no: Optional[int] = None  # 原文行号（removed/context 行有值）
    new_line_no: Optional[int] = None  # 新文行号（added/context 行有值）

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "content": self.content,
            "old_line_no": self.old_line_no,
            "new_line_no": self.new_line_no,
        }


@dataclass
class DiffHunk:
    """差异块（一段连续的变更区域）"""
    old_start: int          # 原文起始行
    old_count: int          # 原文行数
    new_start: int          # 新文起始行
    new_count: int          # 新文行数
    lines: List[DiffLine] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "lines": [l.to_dict() for l in self.lines],
        }


@dataclass
class DiffView:
    """结构化差异视图（适合前端渲染）"""
    hunks: List[DiffHunk] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    old_filename: str = ""
    new_filename: str = ""

    def to_dict(self) -> dict:
        return {
            "hunks": [h.to_dict() for h in self.hunks],
            "summary": self.summary,
            "old_filename": self.old_filename,
            "new_filename": self.new_filename,
        }


@dataclass
class ChangeSummary:
    """变更摘要"""
    total_old_lines: int = 0
    total_new_lines: int = 0
    added_lines: int = 0
    removed_lines: int = 0
    modified_hunks: int = 0
    similarity_ratio: float = 0.0  # 0.0 ~ 1.0

    def to_dict(self) -> dict:
        return {
            "total_old_lines": self.total_old_lines,
            "total_new_lines": self.total_new_lines,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
            "modified_hunks": self.modified_hunks,
            "similarity_ratio": round(self.similarity_ratio, 4),
        }


class DiffManager:
    """文本对比管理器

    提供 unified diff 生成、结构化差异表示、补丁应用等功能。
    所有方法为纯函数，无线程安全问题。
    """

    def __init__(self, context_lines: int = 3):
        """
        Args:
            context_lines: diff 上下文行数（默认 3，与标准 unified diff 一致）
        """
        self.context_lines = context_lines

    # ===== Diff 生成 =====

    def unified_diff(
        self,
        old_text: str,
        new_text: str,
        old_label: str = "original",
        new_label: str = "modified",
    ) -> str:
        """生成标准 unified diff 格式文本

        Args:
            old_text: 原始文本
            new_text: 修改后文本
            old_label: 原始文件标签
            new_label: 修改后文件标签

        Returns:
            str: 标准 unified diff 格式字符串
        """
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        # 确保每行都有换行符（避免 difflib 输出格式异常）
        old_lines = [l if l.endswith("\n") else l + "\n" for l in old_lines]
        new_lines = [l if l.endswith("\n") else l + "\n" for l in new_lines]

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=old_label,
            tofile=new_label,
            n=self.context_lines,
        )
        return "".join(diff)

    def diff_view(
        self,
        old_text: str,
        new_text: str,
        old_label: str = "original",
        new_label: str = "modified",
    ) -> DiffView:
        """生成结构化差异视图（适合前端渲染）

        Args:
            old_text: 原始文本
            new_text: 修改后文本
            old_label: 原始文件标签
            new_label: 修改后文件标签

        Returns:
            DiffView: 结构化差异对象
        """
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        hunks = []
        added = 0
        removed = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                # 上下文行：只保留 hunk 边缘的 context_lines 行
                context_before = old_lines[max(0, i1 - self.context_lines):i1]
                context_after = old_lines[i2:i2 + self.context_lines]

                if context_before or (i1 != i2):
                    hunk_lines = []
                    # 上下文行
                    for k, line in enumerate(context_before):
                        hunk_lines.append(DiffLine(
                            type=DiffLineType.CONTEXT,
                            content=line,
                            old_line_no=i1 - len(context_before) + k + 1,
                            new_line_no=j1 - len(context_before) + k + 1,
                        ))
                    hunks.append(DiffHunk(
                        old_start=i1 - len(context_before) + 1,
                        old_count=len(context_before),
                        new_start=j1 - len(context_before) + 1,
                        new_count=len(context_before),
                        lines=hunk_lines,
                    ))

            elif tag == "replace":
                hunk_lines = []
                old_start = max(0, i1 - self.context_lines)
                new_start = max(0, j1 - self.context_lines)

                # 上下文（前）
                for k in range(old_start, i1):
                    hunk_lines.append(DiffLine(
                        type=DiffLineType.CONTEXT,
                        content=old_lines[k],
                        old_line_no=k + 1,
                        new_line_no=new_start + (k - old_start) + 1,
                    ))

                # 删除行
                for k in range(i1, i2):
                    hunk_lines.append(DiffLine(
                        type=DiffLineType.REMOVED,
                        content=old_lines[k],
                        old_line_no=k + 1,
                    ))
                    removed += 1

                # 新增行
                for k in range(j1, j2):
                    hunk_lines.append(DiffLine(
                        type=DiffLineType.ADDED,
                        content=new_lines[k],
                        new_line_no=k + 1,
                    ))
                    added += 1

                # 上下文（后）
                for k in range(i2, min(len(old_lines), i2 + self.context_lines)):
                    hunk_lines.append(DiffLine(
                        type=DiffLineType.CONTEXT,
                        content=old_lines[k],
                        old_line_no=k + 1,
                    ))

                hunks.append(DiffHunk(
                    old_start=old_start + 1,
                    old_count=(i2 - i1) + min(self.context_lines, len(old_lines) - i2),
                    new_start=new_start + 1,
                    new_count=(j2 - j1) + min(self.context_lines, len(old_lines) - i2),
                    lines=hunk_lines,
                ))

            elif tag == "insert":
                hunk_lines = []
                new_start = max(0, j1 - self.context_lines)

                # 上下文（前）
                for k in range(max(0, i1 - self.context_lines), i1):
                    hunk_lines.append(DiffLine(
                        type=DiffLineType.CONTEXT,
                        content=old_lines[k],
                        old_line_no=k + 1,
                    ))

                # 新增行
                for k in range(j1, j2):
                    hunk_lines.append(DiffLine(
                        type=DiffLineType.ADDED,
                        content=new_lines[k],
                        new_line_no=k + 1,
                    ))
                    added += 1

                hunks.append(DiffHunk(
                    old_start=max(0, i1 - self.context_lines) + 1,
                    old_count=min(self.context_lines, i1),
                    new_start=new_start + 1,
                    new_count=(j2 - j1) + min(self.context_lines, new_start),
                    lines=hunk_lines,
                ))

            elif tag == "delete":
                hunk_lines = []

                # 上下文（前）
                for k in range(max(0, i1 - self.context_lines), i1):
                    hunk_lines.append(DiffLine(
                        type=DiffLineType.CONTEXT,
                        content=old_lines[k],
                        old_line_no=k + 1,
                    ))

                # 删除行
                for k in range(i1, i2):
                    hunk_lines.append(DiffLine(
                        type=DiffLineType.REMOVED,
                        content=old_lines[k],
                        old_line_no=k + 1,
                    ))
                    removed += 1

                hunks.append(DiffHunk(
                    old_start=max(0, i1 - self.context_lines) + 1,
                    old_count=(i2 - i1) + min(self.context_lines, i1),
                    new_start=max(0, j1 - self.context_lines) + 1,
                    new_count=min(self.context_lines, j1),
                    lines=hunk_lines,
                ))

        summary = ChangeSummary(
            total_old_lines=len(old_lines),
            total_new_lines=len(new_lines),
            added_lines=added,
            removed_lines=removed,
            modified_hunks=len(hunks),
            similarity_ratio=matcher.ratio(),
        )

        return DiffView(
            hunks=hunks,
            summary=summary.to_dict(),
            old_filename=old_label,
            new_filename=new_label,
        )

    # ===== 补丁应用 =====

    def apply_patch(self, original: str, patch: str) -> str:
        """应用 unified diff 补丁到原始文本

        Args:
            original: 原始文本
            patch: unified diff 格式的补丁

        Returns:
            str: 应用补丁后的文本

        Raises:
            ValueError: 补丁格式无效或应用失败
        """
        if not patch.strip():
            return original

        return self._manual_apply_patch(original, patch)

    def _manual_apply_patch(self, original: str, patch: str) -> str:
        """手动解析并应用 unified diff 补丁

        当 difflib.restore 不可用时的回退方案。
        """
        import re

        original_lines = original.splitlines()
        patch_lines = patch.splitlines()

        result = []
        orig_idx = 0

        i = 0
        while i < len(patch_lines):
            line = patch_lines[i]

            # 跳过文件头（--- 和 +++）
            if line.startswith("---") or line.startswith("+++"):
                i += 1
                continue

            # 解析 hunk 头 (@@ -a,b +c,d @@)
            if line.startswith("@@"):
                match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                if match:
                    old_start = int(match.group(1)) - 1  # 0-indexed
                    # 复制 hunk 之前的未变更行
                    while orig_idx < old_start and orig_idx < len(original_lines):
                        result.append(original_lines[orig_idx])
                        orig_idx += 1
                i += 1
                continue

            # 处理 diff 行
            if line.startswith("-"):
                # 删除行：跳过原文中的对应行
                orig_idx += 1
            elif line.startswith("+"):
                # 新增行：添加到结果
                result.append(line[1:])
            else:
                # 上下文行（无前缀或空格前缀）：复制原文行
                content = line[1:] if line.startswith(" ") else line
                if orig_idx < len(original_lines):
                    result.append(original_lines[orig_idx])
                    orig_idx += 1
                else:
                    result.append(content)

            i += 1

        # 复制 hunk 之后的剩余行
        while orig_idx < len(original_lines):
            result.append(original_lines[orig_idx])
            orig_idx += 1

        # 保留原始文本的尾部换行符
        output = "\n".join(result)
        if original.endswith("\n") and not output.endswith("\n"):
            output += "\n"
        return output

    def create_patch(
        self,
        old_text: str,
        new_text: str,
        old_label: str = "original",
        new_label: str = "modified",
    ) -> str:
        """创建补丁（unified diff 格式的别名）

        Args:
            old_text: 原始文本
            new_text: 修改后文本
            old_label: 原始文件标签
            new_label: 修改后文件标签

        Returns:
            str: unified diff 格式的补丁
        """
        return self.unified_diff(old_text, new_text, old_label, new_label)

    # ===== 变更分析 =====

    def change_summary(self, old_text: str, new_text: str) -> ChangeSummary:
        """生成变更摘要

        Args:
            old_text: 原始文本
            new_text: 修改后文本

        Returns:
            ChangeSummary: 变更统计信息
        """
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        added = 0
        removed = 0
        hunk_count = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                hunk_count += 1
                if tag in ("replace", "insert"):
                    added += j2 - j1
                if tag in ("replace", "delete"):
                    removed += i2 - i1

        return ChangeSummary(
            total_old_lines=len(old_lines),
            total_new_lines=len(new_lines),
            added_lines=added,
            removed_lines=removed,
            modified_hunks=hunk_count,
            similarity_ratio=matcher.ratio(),
        )

    def inline_diff(self, old_text: str, new_text: str) -> List[Dict[str, Any]]:
        """生成行内差异（word-level diff）

        用于在同一行内高亮具体修改的词语。

        Args:
            old_text: 原始文本
            new_text: 修改后文本

        Returns:
            list[dict]: 每行的行内差异，格式:
                [{"type": "equal"|"delete"|"insert", "text": "..."}]
        """
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        result = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for line in old_lines[i1:i2]:
                    result.append({"type": "equal", "text": line})
            elif tag == "replace":
                # 对替换的行做 word-level diff
                old_chunk = old_lines[i1:i2]
                new_chunk = new_lines[j1:j2]
                word_diffs = self._word_diff(
                    "\n".join(old_chunk),
                    "\n".join(new_chunk),
                )
                result.append({
                    "type": "replace",
                    "old_lines": old_chunk,
                    "new_lines": new_chunk,
                    "word_diffs": word_diffs,
                })
            elif tag == "delete":
                for line in old_lines[i1:i2]:
                    result.append({"type": "delete", "text": line})
            elif tag == "insert":
                for line in new_lines[j1:j2]:
                    result.append({"type": "insert", "text": line})

        return result

    def _word_diff(self, old_text: str, new_text: str) -> List[Dict[str, str]]:
        """word-level diff"""
        old_words = old_text.split()
        new_words = new_text.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words)
        result = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                result.append({"type": "equal", "text": " ".join(old_words[i1:i2])})
            elif tag == "replace":
                result.append({"type": "delete", "text": " ".join(old_words[i1:i2])})
                result.append({"type": "insert", "text": " ".join(new_words[j1:j2])})
            elif tag == "delete":
                result.append({"type": "delete", "text": " ".join(old_words[i1:i2])})
            elif tag == "insert":
                result.append({"type": "insert", "text": " ".join(new_words[j1:j2])})

        return result

    # ===== HITL 集成 =====

    def format_for_review(
        self,
        old_text: str,
        new_text: str,
        stage: str = "",
    ) -> Dict[str, Any]:
        """为 HITL 人工审核格式化差异信息

        Args:
            old_text: 原始文本（修改前）
            new_text: 修改后文本
            stage: 当前阶段名

        Returns:
            dict: 包含 diff_view、summary、unified_diff 的完整审核信息
        """
        view = self.diff_view(old_text, new_text, f"before_{stage}", f"after_{stage}")
        summary = self.change_summary(old_text, new_text)
        unified = self.unified_diff(old_text, new_text, f"before_{stage}", f"after_{stage}")

        return {
            "stage": stage,
            "diff_view": view.to_dict(),
            "summary": summary.to_dict(),
            "unified_diff": unified,
            "old_length": len(old_text),
            "new_length": len(new_text),
        }


# 全局单例
_diff_manager: Optional[DiffManager] = None


def get_diff_manager() -> DiffManager:
    """获取全局 DiffManager 实例"""
    global _diff_manager
    if _diff_manager is None:
        _diff_manager = DiffManager()
    return _diff_manager
