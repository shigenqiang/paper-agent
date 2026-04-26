"""
Annotations - 协作标注/评论

支持对论文特定位置添加评论和标注
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class Annotation:
    """论文评论/标注"""
    annotation_id: str
    paper_id: str
    version_id: str
    user_id: str
    position: Dict  # {"start": int, "end": int, "type": "text"|"paragraph"}
    content: str
    annotation_type: str  # "comment", "suggestion", "question", "highlight"
    created_at: datetime
    updated_at: datetime
    resolved: bool = False
    parent_id: Optional[str] = None  # 用于回复

    @staticmethod
    def create_id():
        return f"ann_{uuid.uuid4().hex[:16]}"


@dataclass
class AnnotationThread:
    """标注线程（用于组织回复）"""
    thread_id: str
    root_annotation_id: str
    paper_id: str
    version_id: str
    created_at: datetime
    updated_at: datetime
    resolved: bool = False

    @staticmethod
    def create_id():
        return f"thread_{uuid.uuid4().hex[:16]}"


class AnnotationManager:
    """标注管理器"""

    def __init__(self):
        self.annotations: List[Annotation] = []
        self.threads: List[AnnotationThread] = []
        self._annotation_index: Dict[str, int] = {}  # annotation_id -> index
        self._paper_index: Dict[str, List[str]] = {}  # paper_id -> annotation_ids

    async def add_annotation(
        self,
        paper_id: str,
        version_id: str,
        user_id: str,
        position: Dict,
        content: str,
        annotation_type: str = "comment",
        parent_id: Optional[str] = None
    ) -> Annotation:
        """
        添加标注

        Args:
            paper_id: 论文ID
            version_id: 版本ID
            user_id: 用户ID
            position: 位置 {"start": int, "end": int, "type": str}
            content: 标注内容
            annotation_type: 标注类型
            parent_id: 父标注ID（用于回复）

        Returns:
            创建的Annotation对象
        """
        annotation_id = Annotation.create_id()
        now = datetime.now()

        annotation = Annotation(
            annotation_id=annotation_id,
            paper_id=paper_id,
            version_id=version_id,
            user_id=user_id,
            position=position,
            content=content,
            annotation_type=annotation_type,
            created_at=now,
            updated_at=now,
            parent_id=parent_id
        )

        self.annotations.append(annotation)
        self._annotation_index[annotation_id] = len(self.annotations) - 1

        # 更新论文索引
        if paper_id not in self._paper_index:
            self._paper_index[paper_id] = []
        self._paper_index[paper_id].append(annotation_id)

        return annotation

    async def add_reply(
        self,
        parent_id: str,
        user_id: str,
        content: str
    ) -> Optional[Annotation]:
        """添加回复"""
        parent = await self.get_annotation(parent_id)
        if not parent:
            return None

        return await self.add_annotation(
            paper_id=parent.paper_id,
            version_id=parent.version_id,
            user_id=user_id,
            position=parent.position,
            content=content,
            annotation_type="comment",
            parent_id=parent_id
        )

    async def get_annotation(self, annotation_id: str) -> Optional[Annotation]:
        """获取标注"""
        index = self._annotation_index.get(annotation_id)
        if index is not None and index < len(self.annotations):
            return self.annotations[index]
        return None

    async def get_annotations(
        self,
        paper_id: str,
        version_id: Optional[str] = None,
        user_id: Optional[str] = None,
        annotation_type: Optional[str] = None,
        include_resolved: bool = True
    ) -> List[Annotation]:
        """
        获取论文的标注列表

        Args:
            paper_id: 论文ID
            version_id: 版本ID（可选）
            user_id: 用户ID（可选）
            annotation_type: 标注类型（可选）
            include_resolved: 是否包含已解决的标注

        Returns:
            标注列表
        """
        results = []

        annotation_ids = self._paper_index.get(paper_id, [])
        for ann_id in annotation_ids:
            ann = await self.get_annotation(ann_id)
            if not ann:
                continue

            # 过滤条件
            if version_id and ann.version_id != version_id:
                continue
            if user_id and ann.user_id != user_id:
                continue
            if annotation_type and ann.annotation_type != annotation_type:
                continue
            if not include_resolved and ann.resolved:
                continue

            results.append(ann)

        return results

    async def get_thread(self, root_annotation_id: str) -> List[Annotation]:
        """获取标注线程（根标注及其所有回复）"""
        root = await self.get_annotation(root_annotation_id)
        if not root:
            return []

        thread = [root]
        annotation_ids = self._paper_index.get(root.paper_id, [])

        for ann_id in annotation_ids:
            ann = await self.get_annotation(ann_id)
            if ann and ann.parent_id == root_annotation_id:
                thread.append(ann)

        return thread

    async def update_annotation(
        self,
        annotation_id: str,
        content: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> Optional[Annotation]:
        """更新标注"""
        annotation = await self.get_annotation(annotation_id)
        if not annotation:
            return None

        if content is not None:
            annotation.content = content
        if resolved is not None:
            annotation.resolved = resolved

        annotation.updated_at = datetime.now()
        return annotation

    async def delete_annotation(self, annotation_id: str) -> bool:
        """删除标注"""
        annotation = await self.get_annotation(annotation_id)
        if not annotation:
            return False

        paper_id = annotation.paper_id
        if paper_id in self._paper_index and annotation_id in self._paper_index[paper_id]:
            self._paper_index[paper_id].remove(annotation_id)

        index = self._annotation_index.get(annotation_id)
        if index is not None:
            del self.annotations[index]
            del self._annotation_index[annotation_id]
            # 重建索引（简化处理）
            self._rebuild_index()

        return True

    async def resolve_annotation(self, annotation_id: str) -> Optional[Annotation]:
        """标记标注为已解决"""
        return await self.update_annotation(annotation_id, resolved=True)

    async def unresolve_annotation(self, annotation_id: str) -> Optional[Annotation]:
        """标记标注为未解决"""
        return await self.update_annotation(annotation_id, resolved=False)

    async def get_unresolved_count(self, paper_id: str, version_id: Optional[str] = None) -> int:
        """获取未解决的标注数量"""
        annotations = await self.get_annotations(
            paper_id,
            version_id=version_id,
            include_resolved=False
        )
        return len(annotations)

    def _rebuild_index(self):
        """重建索引"""
        self._annotation_index.clear()
        for i, ann in enumerate(self.annotations):
            self._annotation_index[ann.annotation_id] = i


# 全局标注管理器实例
_annotation_manager: Optional[AnnotationManager] = None


def get_annotation_manager() -> AnnotationManager:
    """获取全局标注管理器"""
    global _annotation_manager
    if _annotation_manager is None:
        _annotation_manager = AnnotationManager()
    return _annotation_manager
