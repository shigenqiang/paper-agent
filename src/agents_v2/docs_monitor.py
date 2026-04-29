"""
实时文档监控器 - Real-time Docs Monitor

功能:
1. 监控docs目录文件变化
2. 检测文档完整性
3. 生成文档健康报告
4. 后台持续运行
"""
import os
import time
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import logging
import watchdog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)


class DocStatus(str, Enum):
    """文档状态"""
    HEALTHY = "healthy"
    CHANGED = "changed"
    NEW = "new"
    DELETED = "deleted"
    MISSING = "missing"


@dataclass
class DocInfo:
    """文档信息"""
    path: str
    name: str
    size: int
    modified_time: float
    checksum: str
    status: DocStatus = DocStatus.HEALTHY
    lines: int = 0
    headings: List[str] = field(default_factory=list)


@dataclass
class DocsHealthReport:
    """文档健康报告"""
    timestamp: float
    total_docs: int
    healthy_count: int
    changed_count: int
    new_count: int
    total_size: int
    avg_size: float
    largest_doc: Optional[str] = None
    smallest_doc: Optional[str] = None
    docs_by_status: Dict[str, int] = field(default_factory=dict)
    doc_list: List[Dict[str, Any]] = field(default_factory=list)


class DocChangeHandler(FileSystemEventHandler):
    """文档变化处理器"""

    def __init__(self, monitor: 'DocsMonitor'):
        self.monitor = monitor
        super().__init__()

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"文档修改: {event.src_path}")
            self.monitor.on_doc_changed(event.src_path)

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"文档创建: {event.src_path}")
            self.monitor.on_doc_created(event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"文档删除: {event.src_path}")
            self.monitor.on_doc_deleted(event.src_path)


class DocsMonitor:
    """
    文档监控器

    功能:
    - 扫描文档目录
    - 计算文档Checksum
    - 检测文档变化
    - 生成健康报告
    - 后台持续监控
    """

    def __init__(self, docs_path: str = "docs"):
        self.docs_path = Path(docs_path)
        self.docs: Dict[str, DocInfo] = {}
        self._running = False
        self._observer: Optional[Observer] = None
        self._lock = threading.RLock()
        self._callbacks: List[callable] = []

    def scan(self) -> Dict[str, DocInfo]:
        """扫描文档目录"""
        with self._lock:
            self.docs.clear()

            if not self.docs_path.exists():
                logger.warning(f"文档目录不存在: {self.docs_path}")
                return self.docs

            for md_file in self.docs_path.rglob("*.md"):
                try:
                    doc_info = self._read_doc_info(md_file)
                    self.docs[str(md_file)] = doc_info
                except Exception as e:
                    logger.error(f"读取文档失败 {md_file}: {e}")

            return self.docs

    def _read_doc_info(self, path: Path) -> DocInfo:
        """读取单个文档信息"""
        stat = path.stat()
        content = path.read_text(encoding='utf-8')
        checksum = hashlib.md5(content.encode()).hexdigest()
        lines = len(content.splitlines())

        # 提取标题
        headings = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('#'):
                headings.append(line[:80])

        return DocInfo(
            path=str(path),
            name=path.name,
            size=stat.st_size,
            modified_time=stat.st_mtime,
            checksum=checksum,
            lines=lines,
            headings=headings
        )

    def get_health_report(self) -> DocsHealthReport:
        """生成健康报告"""
        with self._lock:
            total = len(self.docs)
            if total == 0:
                return DocsHealthReport(
                    timestamp=time.time(),
                    total_docs=0,
                    healthy_count=0,
                    changed_count=0,
                    new_count=0,
                    total_size=0,
                    avg_size=0
                )

            total_size = sum(d.size for d in self.docs.values())
            by_status: Dict[str, int] = {}

            doc_list = []
            for doc in self.docs.values():
                status_key = doc.status.value
                by_status[status_key] = by_status.get(status_key, 0) + 1

                doc_list.append({
                    "name": doc.name,
                    "path": doc.path,
                    "size": doc.size,
                    "size_kb": round(doc.size / 1024, 2),
                    "lines": doc.lines,
                    "status": doc.status.value,
                    "modified": datetime.fromtimestamp(doc.modified_time).isoformat(),
                    "headings_count": len(doc.headings)
                })

            # 找最大和最小文档
            sorted_docs = sorted(self.docs.values(), key=lambda d: d.size)
            smallest = sorted_docs[0].name if sorted_docs else None
            largest = sorted_docs[-1].name if sorted_docs else None

            return DocsHealthReport(
                timestamp=time.time(),
                total_docs=total,
                healthy_count=by_status.get('healthy', 0),
                changed_count=by_status.get('changed', 0),
                new_count=by_status.get('new', 0),
                total_size=total_size,
                avg_size=total_size / total,
                largest_doc=largest,
                smallest_doc=smallest,
                docs_by_status=by_status,
                doc_list=sorted(doc_list, key=lambda x: x['size'], reverse=True)
            )

    def start_watching(self, callback: Optional[callable] = None):
        """开始监控"""
        if self._running:
            logger.warning("监控已在运行")
            return

        if callback:
            self._callbacks.append(callback)

        # 先扫描一次
        self.scan()

        # 启动观察者
        self._observer = Observer()
        handler = DocChangeHandler(self)
        self._observer.schedule(handler, str(self.docs_path), recursive=True)
        self._observer.start()
        self._running = True

        logger.info(f"开始监控文档目录: {self.docs_path}")

    def stop_watching(self):
        """停止监控"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._running = False
            logger.info("停止文档监控")

    def on_doc_changed(self, path: str):
        """文档变化回调"""
        with self._lock:
            if path in self.docs:
                old_doc = self.docs[path]
                try:
                    new_doc = self._read_doc_info(Path(path))
                    new_doc.status = DocStatus.CHANGED
                    self.docs[path] = new_doc
                    self._notify_callbacks({
                        "type": "changed",
                        "doc": old_doc.name,
                        "path": path
                    })
                except Exception as e:
                    logger.error(f"更新文档失败 {path}: {e}")

    def on_doc_created(self, path: str):
        """文档创建回调"""
        with self._lock:
            try:
                doc_info = self._read_doc_info(Path(path))
                doc_info.status = DocStatus.NEW
                self.docs[path] = doc_info
                self._notify_callbacks({
                    "type": "created",
                    "doc": doc_info.name,
                    "path": path
                })
            except Exception as e:
                logger.error(f"创建文档记录失败 {path}: {e}")

    def on_doc_deleted(self, path: str):
        """文档删除回调"""
        with self._lock:
            if path in self.docs:
                del self.docs[path]
                self._notify_callbacks({
                    "type": "deleted",
                    "path": path
                })

    def add_callback(self, callback: callable):
        """添加变化回调"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, event: dict):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")

    @property
    def is_running(self) -> bool:
        return self._running


def run_monitor_terminal():
    """终端运行监控"""
    monitor = DocsMonitor("docs")
    monitor.scan()

    def print_change(event):
        print(f"\n📝 [{event['type']}] {event.get('doc', event['path'])}")
        print(f"   报告: {json.dumps(monitor.get_health_report().__dict__, ensure_ascii=False, indent=2)[:500]}...")

    monitor.add_callback(print_change)
    monitor.start_watching()

    print("📚 文档实时监控已启动 (Ctrl+C 退出)")
    print(f"📁 监控目录: {monitor.docs_path.absolute()}")
    print()

    try:
        while True:
            time.sleep(5)
            report = monitor.get_health_report()
            print(f"\r[{datetime.now().strftime('%H:%M:%S')}] 文档: {report.total_docs} | 健康: {report.healthy_count} | 变化: {report.changed_count}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\n🛑 停止监控...")
        monitor.stop_watching()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_monitor_terminal()
