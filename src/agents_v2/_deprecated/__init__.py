"""
Deprecated 模块 - 已废弃的代码

此目录包含从主代码库迁移的废弃代码。

警告: 此目录中的代码已弃用，不应在新代码中使用。

迁移的历史:
- paper_agents/deprecated/* -> _deprecated/
- writing/deprecated/* -> _deprecated/
- knowledge_graph/deprecated/* -> _deprecated/
- memory/deprecated/* -> _deprecated/

对于新代码，请使用:
- src.agents_v2.agents.roles.* (Agent角色模块)
- src.agents_v2.orchestration.* (编排逻辑)
- src.agents_v2.harness.* (质量保障)
"""
import warnings

def _warn_deprecated():
    """发出弃用警告"""
    warnings.warn(
        "从 src.agents_v2._deprecated 导入的方式已弃用。"
        "这些文件是为向后兼容而保留的，不应在新代码中使用。",
        DeprecationWarning,
        stacklevel=2
    )

# 提供一个便捷的警告函数
def get_deprecated_files():
    """返回已废弃的文件列表"""
    return [
        "annotations.py",
        "chapter_strategies.py",
        "editor_agent.py",
        "reviewer_agent.py",
        "self_rag_writer.py",
        "thesis_agent.py",
        "versioning.py",
        "writing_pipeline.py",
    ]