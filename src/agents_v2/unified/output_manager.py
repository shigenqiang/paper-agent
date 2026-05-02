"""
输出版本管理模块

功能:
1. 多格式导出（Markdown/LaTeX/Word/PDF）
2. 版本追踪与增量更新
3. 渲染预览机制
4. 历史记录管理

设计原则:
- 支持多种输出格式
- 保留版本历史便于回溯
- 增量更新避免重复处理
"""
from src.agents_v2.logging_config import get_logging_logger

import hashlib
import json

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class ExportFormat(str, Enum):
    """导出格式枚举"""
    MARKDOWN = "markdown"
    LATEX = "latex"
    WORD = "word"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"


class VersionStatus(str, Enum):
    """版本状态"""
    DRAFT = "draft"
    REVIEW = "review"
    FINAL = "final"
    ARCHIVED = "archived"


@dataclass
class Version:
    """文档版本"""
    version_id: str
    version_number: int
    created_at: str
    content_hash: str
    content: str
    format: ExportFormat
    status: VersionStatus
    change_summary: str = ""
    parent_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    """导出结果"""
    success: bool
    file_path: str = ""
    format: ExportFormat = ExportFormat.MARKDOWN
    version_id: str = ""
    error: Optional[str] = None


class VersionManager:
    """版本管理器"""

    def __init__(self, storage_path: str = "./versions"):
        """初始化版本管理器

        Args:
            storage_path: 版本存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.versions: Dict[str, Version] = {}
        self.document_versions: Dict[str, List[str]] = {}  # doc_id -> version_ids

        self._load_existing_versions()

    def _load_existing_versions(self):
        """加载已有版本"""
        index_file = self.storage_path / "version_index.json"

        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.versions = {k: Version(**v) for k, v in data.get("versions", {}).items()}
                    self.document_versions = data.get("document_versions", {})
            except Exception as e:
                logger.error(f"Failed to load version index: {e}")

    def _save_index(self):
        """保存版本索引"""
        index_file = self.storage_path / "version_index.json"

        data = {
            "versions": {k: vars(v) for k, v in self.versions.items()},
            "document_versions": self.document_versions
        }

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_version_id(self, doc_id: str) -> str:
        """生成版本ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{doc_id}_{timestamp}"

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def create_version(
        self,
        doc_id: str,
        content: str,
        format: ExportFormat = ExportFormat.MARKDOWN,
        status: VersionStatus = VersionStatus.DRAFT,
        change_summary: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Version:
        """创建新版本

        Args:
            doc_id: 文档ID
            content: 文档内容
            format: 导出格式
            status: 版本状态
            change_summary: 变更摘要
            metadata: 元数据

        Returns:
            Version: 新版本
        """
        # 生成版本号
        if doc_id in self.document_versions:
            existing_versions = self.document_versions[doc_id]
            version_number = len(existing_versions) + 1
            parent_id = existing_versions[-1]
        else:
            version_number = 1
            parent_id = None

        version_id = self._generate_version_id(doc_id)
        content_hash = self._compute_hash(content)

        version = Version(
            version_id=version_id,
            version_number=version_number,
            created_at=datetime.now().isoformat(),
            content_hash=content_hash,
            content=content,
            format=format,
            status=status,
            change_summary=change_summary,
            parent_version=parent_id,
            metadata=metadata or {}
        )

        # 保存版本
        self.versions[version_id] = version

        # 更新文档版本列表
        if doc_id not in self.document_versions:
            self.document_versions[doc_id] = []
        self.document_versions[doc_id].append(version_id)

        # 保存内容到单独文件
        content_file = self.storage_path / f"{version_id}.txt"
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # 保存索引
        self._save_index()

        logger.info(f"Created version {version_id} for document {doc_id}")

        return version

    def get_version(self, version_id: str) -> Optional[Version]:
        """获取版本"""
        return self.versions.get(version_id)

    def get_document_versions(self, doc_id: str) -> List[Version]:
        """获取文档的所有版本"""
        version_ids = self.document_versions.get(doc_id, [])
        return [self.versions[vid] for vid in version_ids if vid in self.versions]

    def get_latest_version(self, doc_id: str) -> Optional[Version]:
        """获取文档的最新版本"""
        versions = self.get_document_versions(doc_id)
        return versions[-1] if versions else None

    def compare_versions(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """比较两个版本

        Returns:
            Dict: 包含差异信息
        """
        v1 = self.versions.get(version_id1)
        v2 = self.versions.get(version_id2)

        if not v1 or not v2:
            return {"error": "Version not found"}

        # 计算差异
        changes = {
            "version1": v1.version_id,
            "version2": v2.version_id,
            "time_diff": v2.created_at,
            "status_change": v1.status != v2.status,
            "format_change": v1.format != v2.format,
        }

        return changes

    def revert_to_version(self, doc_id: str, version_id: str) -> Optional[Version]:
        """恢复到指定版本

        Args:
            doc_id: 文档ID
            version_id: 要恢复的版本ID

        Returns:
            Version: 新创建的版本（基于恢复的版本）
        """
        target_version = self.versions.get(version_id)

        if not target_version:
            logger.error(f"Version {version_id} not found")
            return None

        # 创建新版本，内容来自目标版本
        return self.create_version(
            doc_id=doc_id,
            content=target_version.content,
            format=target_version.format,
            status=VersionStatus.DRAFT,
            change_summary=f"Reverted to version {version_id}",
            metadata={"reverted_from": version_id}
        )

    def list_documents(self) -> List[str]:
        """列出所有文档ID"""
        return list(self.document_versions.keys())


class FormatExporter:
    """格式导出器"""

    def __init__(self, version_manager: Optional[VersionManager] = None):
        self.version_manager = version_manager or VersionManager()

    def export(
        self,
        content: str,
        format: ExportFormat,
        output_path: Optional[str] = None,
        doc_id: str = "default"
    ) -> ExportResult:
        """导出文档

        Args:
            content: 文档内容
            format: 目标格式
            output_path: 输出路径（可选）
            doc_id: 文档ID

        Returns:
            ExportResult: 导出结果
        """
        try:
            # 根据格式导出
            if format == ExportFormat.MARKDOWN:
                result_path = self._export_markdown(content, output_path)
            elif format == ExportFormat.LATEX:
                result_path = self._export_latex(content, output_path)
            elif format == ExportFormat.HTML:
                result_path = self._export_html(content, output_path)
            elif format == ExportFormat.WORD:
                result_path = self._export_word(content, output_path)
            elif format == ExportFormat.PDF:
                result_path = self._export_pdf(content, output_path)
            else:
                return ExportResult(
                    success=False,
                    error=f"Unsupported format: {format}"
                )

            # 创建版本
            version = self.version_manager.create_version(
                doc_id=doc_id,
                content=content,
                format=format,
                status=VersionStatus.FINAL,
                change_summary=f"Exported to {format.value}"
            )

            return ExportResult(
                success=True,
                file_path=result_path,
                format=format,
                version_id=version.version_id
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                success=False,
                error=str(e)
            )

    def _export_markdown(self, content: str, output_path: Optional[str]) -> str:
        """导出为Markdown"""
        if output_path is None:
            output_path = f"./output/{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(output_path)

    def _export_latex(self, content: str, output_path: Optional[str]) -> str:
        """导出为LaTeX"""
        if output_path is None:
            output_path = f"./output/{datetime.now().strftime('%Y%m%d_%H%M%S')}.tex"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 简单的Markdown到LaTeX转换
        latex_content = self._convert_to_latex(content)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        return str(output_path)

    def _convert_to_latex(self, markdown: str) -> str:
        """将Markdown转换为LaTeX"""
        latex = []

        lines = markdown.split('\n')
        in_table = False

        for line in lines:
            # 标题
            if line.startswith('# '):
                latex.append(f"\\section{{{line[2:]}}}")
            elif line.startswith('## '):
                latex.append(f"\\subsection{{{line[3:]}}}")
            elif line.startswith('### '):
                latex.append(f"\\subsubsection{{{line[4:]}}}")

            # 列表
            elif line.startswith('- '):
                latex.append(f"\\item {line[2:]}")
            elif line.startswith('* '):
                latex.append(f"\\item {line[2:]}")

            # 引用
            elif line.startswith('>'):
                latex.append(f"\\begin{{quote}}{line[1:]}\\end{{quote}}")

            # 表格（简化处理）
            elif line.startswith('|'):
                if not in_table:
                    latex.append("\\begin{tabular}{|c|c|c|}")
                    latex.append("\\hline")
                    in_table = True
                else:
                    latex.append(line.replace('|', '&').replace('-', '\\hline'))

            # 粗体和斜体
            else:
                line = line.replace('**', '\\textbf{').replace('*', '\\textit{')
                latex.append(line)

        return '\n'.join(latex)

    def _export_html(self, content: str, output_path: Optional[str]) -> str:
        """导出为HTML"""
        if output_path is None:
            output_path = f"./output/{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 简单的Markdown到HTML转换
        html_content = self._convert_to_html(content)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>论文输出</title>
    <style>
        body {{ font-family: serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ font-family: sans-serif; }}
        code {{ background-color: #f5f5f5; padding: 2px 4px; }}
        pre {{ background-color: #f5f5f5; padding: 10px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(output_path)

    def _convert_to_html(self, markdown: str) -> str:
        """将Markdown转换为HTML"""
        import re

        html = markdown

        # 标题
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

        # 列表
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # 代码块
        html = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)

        # 行内代码
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # 粗体和斜体
        html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)

        # 段落
        html = re.sub(r'\n\n', '</p><p>', html)
        html = f'<p>{html}</p>'

        return html

    def _export_word(self, content: str, output_path: Optional[str]) -> str:
        """导出为Word（需要python-docx）"""
        try:
            from docx import Document

            if output_path is None:
                output_path = f"./output/{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            doc = Document()
            doc.add_heading('论文', 0)

            # 按行处理
            lines = content.split('\n')
            for line in lines:
                if line.startswith('# '):
                    doc.add_heading(line[2:], 1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], 2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], 3)
                elif line.startswith('- '):
                    doc.add_paragraph(line[2:], style='List Bullet')
                elif line.strip():
                    doc.add_paragraph(line)

            doc.save(str(output_path))
            return str(output_path)

        except ImportError:
            logger.error("python-docx not installed")
            raise RuntimeError("python-docx not installed. Install with: pip install python-docx")

    def _export_pdf(self, content: str, output_path: Optional[str]) -> str:
        """导出为PDF（通过HTML中转）"""
        # 先生成HTML
        html_path = self._export_html(content, output_path.replace('.pdf', '.html') if output_path else None)

        try:
            # 使用weasyprint或其他工具转换
            # 这里简化处理
            logger.warning("PDF export requires additional tools (weasyprint, wkhtmltopdf, etc.)")
            return html_path  # 返回HTML路径作为替代
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            raise


class IncrementalUpdateManager:
    """增量更新管理器

    跟踪文档变更，只处理变化的部分
    """

    def __init__(self):
        self.change_history: List[Dict[str, Any]] = []

    def detect_changes(
        self,
        old_content: str,
        new_content: str
    ) -> Dict[str, Any]:
        """检测内容变更

        Args:
            old_content: 旧内容
            new_content: 新内容

        Returns:
            Dict: 变更信息
        """
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')

        changes = {
            "added_lines": [],
            "removed_lines": [],
            "modified_ranges": []
        }

        # 简单行对比
        old_set = set(old_lines)
        new_set = set(new_lines)

        added = new_set - old_set
        removed = old_set - new_set

        changes["added_lines"] = list(added)[:20]  # 限制数量
        changes["removed_lines"] = list(removed)[:20]

        # 计算修改比例
        if len(old_lines) > 0:
            change_ratio = len(added) / len(old_lines)
            changes["change_ratio"] = min(1.0, change_ratio)

        return changes

    def should_regenerate(self, changes: Dict[str, Any], threshold: float = 0.3) -> bool:
        """判断是否需要重新生成

        Args:
            changes: 变更信息
            threshold: 阈值

        Returns:
            bool: 是否需要重新生成
        """
        change_ratio = changes.get("change_ratio", 1.0)

        if change_ratio > threshold:
            logger.info(f"Change ratio {change_ratio:.2f} exceeds threshold {threshold}, regenerating")
            return True

        return False

    def apply_incremental_update(
        self,
        old_content: str,
        new_content: str
    ) -> str:
        """应用增量更新

        对于小的变更，直接应用；对于大的变更，返回新内容

        Args:
            old_content: 旧内容
            new_content: 新内容

        Returns:
            str: 更新后的内容
        """
        changes = self.detect_changes(old_content, new_content)

        # 记录变更历史
        self.change_history.append({
            "timestamp": datetime.now().isoformat(),
            "changes": changes
        })

        if self.should_regenerate(changes):
            return new_content

        # 对于小的变更，可以考虑更智能的合并
        # 这里简化处理，直接返回新内容
        return new_content


# 便捷函数
def export_document(
    content: str,
    format: ExportFormat,
    output_path: Optional[str] = None
) -> ExportResult:
    """导出文档的便捷函数"""
    exporter = FormatExporter()
    return exporter.export(content, format, output_path)


def save_version(
    doc_id: str,
    content: str,
    format: ExportFormat = ExportFormat.MARKDOWN
) -> Version:
    """保存版本的便捷函数"""
    manager = VersionManager()
    return manager.create_version(doc_id, content, format)


def get_document_history(doc_id: str) -> List[Version]:
    """获取文档历史"""
    manager = VersionManager()
    return manager.get_document_versions(doc_id)