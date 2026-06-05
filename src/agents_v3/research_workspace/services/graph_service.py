"""知识图谱服务 - 门面类

组合所有 Mixin 模块，对外暴露统一的 GraphService API。
实际逻辑分布在：
- graph_utils.py     : 纯函数、常量
- graph_builders.py  : 图构建（全量/增量）
- graph_query.py     : 读取/查询/上下文
- graph_gaps.py      : Gap 检测
- graph_communities.py: 社区检测 + Global Search
- graph_merge.py     : 实体消歧
- graph_validation.py: 验证/指标/Consensus Meter
"""

from __future__ import annotations

from src.agents_v3.research_workspace.storage import get_storage

from .graph_builders import GraphBuilderMixin
from .graph_communities import GraphCommunityMixin
from .graph_gaps import GraphGapMixin
from .graph_merge import GraphMergeMixin
from .graph_query import GraphQueryMixin
from .graph_validation import GraphValidationMixin


class GraphService(
    GraphBuilderMixin,
    GraphQueryMixin,
    GraphGapMixin,
    GraphCommunityMixin,
    GraphMergeMixin,
    GraphValidationMixin,
):
    """知识图谱构建与查询"""

    def __init__(self, storage=None):
        self.storage = storage or get_storage()

    def _save_graph(self, project_id: str, graph) -> None:
        """保存到统一 graphs collection"""
        graph_data = graph.model_dump()
        graph_data["graph_id"] = f"kg_{project_id}"
        graph_data["version"] = 1
        self.storage.upsert_item("graphs", f"kg_{project_id}", graph_data)
        self.storage.save_collection(f"graph_{project_id}", [graph_data])


# 重新导出，保持向后兼容
from .graph_utils import (  # noqa: E402,F401
    _ALIASES,
    _LIMITATION_TYPE_KEYWORDS,
    _cosine_similarity,
    _levenshtein,
    classify_limitation_type,
    compute_gap_confidence,
    resolve_alias,
)

from src.agents_v3.research_workspace.utils import normalize_label, stable_hash  # noqa: F401
