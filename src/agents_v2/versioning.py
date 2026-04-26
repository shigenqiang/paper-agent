"""
Versioning - 论文版本控制

管理论文版本、版本历史和版本对比
"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import hashlib


@dataclass
class PaperVersion:
    """论文版本"""
    version_id: str
    paper_id: str
    version_number: int
    content: str
    content_hash: str
    created_at: datetime
    created_by: str
    metadata: Dict = field(default_factory=dict)
    comment: str = ""

    @staticmethod
    def compute_hash(content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class Paper:
    """论文"""
    paper_id: str
    title: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    current_version_id: str
    metadata: Dict = field(default_factory=dict)


class PaperVersionManager:
    """论文版本管理器"""

    def __init__(self):
        self.papers: Dict[str, Paper] = {}
        self.versions: Dict[str, List[PaperVersion]] = {}  # paper_id -> versions

    def generate_paper_id(self) -> str:
        """生成论文ID"""
        return f"paper_{uuid.uuid4().hex[:16]}"

    def generate_version_id(self) -> str:
        """生成版本ID"""
        return f"v_{uuid.uuid4().hex[:16]}"

    async def create_paper(
        self,
        title: str,
        owner_id: str,
        initial_content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """创建新论文"""
        paper_id = self.generate_paper_id()
        version_id = await self.save_version(paper_id, initial_content, owner_id, "Initial version")

        paper = Paper(
            paper_id=paper_id,
            title=title,
            owner_id=owner_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            current_version_id=version_id,
            metadata=metadata or {}
        )
        self.papers[paper_id] = paper
        return paper_id

    async def save_version(
        self,
        paper_id: str,
        content: str,
        created_by: str,
        comment: str = ""
    ) -> str:
        """保存新版本"""
        if paper_id not in self.versions:
            self.versions[paper_id] = []

        version_number = len(self.versions[paper_id]) + 1
        version_id = self.generate_version_id()
        content_hash = PaperVersion.compute_hash(content)

        version = PaperVersion(
            version_id=version_id,
            paper_id=paper_id,
            version_number=version_number,
            content=content,
            content_hash=content_hash,
            created_at=datetime.now(),
            created_by=created_by,
            comment=comment
        )

        self.versions[paper_id].append(version)

        # 更新论文当前版本
        if paper_id in self.papers:
            self.papers[paper_id].current_version_id = version_id
            self.papers[paper_id].updated_at = datetime.now()

        return version_id

    async def get_version(self, paper_id: str, version_id: str) -> Optional[PaperVersion]:
        """获取指定版本"""
        versions = self.versions.get(paper_id, [])
        for v in versions:
            if v.version_id == version_id:
                return v
        return None

    async def get_version_by_number(self, paper_id: str, version_number: int) -> Optional[PaperVersion]:
        """通过版本号获取版本"""
        versions = self.versions.get(paper_id, [])
        for v in versions:
            if v.version_number == version_number:
                return v
        return None

    async def list_versions(self, paper_id: str) -> List[PaperVersion]:
        """列出论文所有版本"""
        return self.versions.get(paper_id, [])

    async def get_current_version(self, paper_id: str) -> Optional[PaperVersion]:
        """获取当前版本"""
        if paper_id not in self.papers:
            return None
        current_version_id = self.papers[paper_id].current_version_id
        return await self.get_version(paper_id, current_version_id)

    async def compare_versions(
        self,
        paper_id: str,
        version_id_1: str,
        version_id_2: str
    ) -> Optional[Dict]:
        """对比两个版本"""
        v1 = await self.get_version(paper_id, version_id_1)
        v2 = await self.get_version(paper_id, version_id_2)

        if not v1 or not v2:
            return None

        # 简单的行对比
        lines1 = v1.content.split('\n')
        lines2 = v2.content.split('\n')

        added = [l for l in lines2 if l not in lines1]
        removed = [l for l in lines1 if l not in lines2]

        return {
            "version_1": v1.version_id,
            "version_2": v2.version_id,
            "added_lines": added,
            "removed_lines": removed,
            "similarity": len(set(lines1) & set(lines2)) / max(len(set(lines1) | set(lines2)), 1)
        }

    async def get_paper(self, paper_id: str) -> Optional[Paper]:
        """获取论文信息"""
        return self.papers.get(paper_id)

    async def list_user_papers(self, user_id: str) -> List[Paper]:
        """列出用户的所有论文"""
        return [p for p in self.papers.values() if p.owner_id == user_id]

    async def delete_paper(self, paper_id: str):
        """删除论文"""
        if paper_id in self.papers:
            del self.papers[paper_id]
        if paper_id in self.versions:
            del self.versions[paper_id]


# 全局版本管理器实例
_version_manager: Optional[PaperVersionManager] = None


def get_version_manager() -> PaperVersionManager:
    """获取全局版本管理器"""
    global _version_manager
    if _version_manager is None:
        _version_manager = PaperVersionManager()
    return _version_manager
