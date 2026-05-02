"""Agent Roles - 按角色分类的Agent模块

Roles:
- searcher: 搜索和文献相关Agent
- planner: 规划和大纲相关Agent
- writer: 写作和初稿相关Agent
- polisher: 润色和修改相关Agent
- reviewer: 审核和质量保障Agent
- specialist: 专业化任务Agent（图表、方法论、查重等）

迁移状态:
- paper_agents/* -> agents/roles/* (进行中)
- writing/* -> agents/roles/* (进行中)
- problem_oriented/* -> agents/roles/* (进行中)
"""
import warnings

# 检测旧导入路径并警告
def _warn_roles_migration():
    warnings.warn(
        "从 src.agents_v2.paper_agents/writing/problem_oriented 导入的方式已弃用。"
        "请使用新的 roles 路径："
        "\n  - src.agents_v2.agents.roles.searcher (文献搜索)"
        "\n  - src.agents_v2.agents.roles.planner (大纲规划)"
        "\n  - src.agents_v2.agents.roles.writer (初稿撰写)"
        "\n  - src.agents_v2.agents.roles.polisher (语言润色)"
        "\n  - src.agents_v2.agents.roles.reviewer (质量审核)"
        "\n  - src.agents_v2.agents.roles.specialist (专业工具)",
        DeprecationWarning,
        stacklevel=2
    )

# 导出所有子模块
from . import searcher
from . import planner
from . import writer
from . import polisher
from . import reviewer
from . import specialist

__all__ = [
    "searcher",
    "planner",
    "writer",
    "polisher",
    "reviewer",
    "specialist",
]