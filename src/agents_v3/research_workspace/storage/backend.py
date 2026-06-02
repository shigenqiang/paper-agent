"""存储后端协议定义"""

from __future__ import annotations

from typing import Any, Protocol


class StorageBackend(Protocol):
    """存储后端统一接口"""

    def upsert(self, table: str, item_id: str, data: dict[str, Any]) -> None:
        """插入或更新一条记录"""
        ...

    def get(self, table: str, item_id: str) -> dict[str, Any] | None:
        """获取单条记录"""
        ...

    def query(self, table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """按条件查询"""
        ...

    def delete(self, table: str, item_id: str) -> bool:
        """删除一条记录"""
        ...

    def list_all(self, table: str) -> list[dict[str, Any]]:
        """列出表中所有记录"""
        ...

    def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        """统计记录数"""
        ...
