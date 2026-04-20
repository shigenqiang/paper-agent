"""记忆管理器测试"""
import pytest
import asyncio
from src.memory.memory_manager import MemoryManager, MemoryItem
from datetime import datetime, timedelta


@pytest.fixture
def memory_manager():
    """创建记忆管理器fixture"""
    return MemoryManager()


def test_add_memory(memory_manager):
    """测试添加记忆"""
    memory_id = memory_manager.add_memory(
        content="这是一条测试记忆",
        importance=0.8
    )

    assert memory_id.startswith("mem_")
    assert len(memory_manager.memories) == 1


def test_retrieve_relevant(memory_manager):
    """测试检索相关记忆"""
    # 添加多条记忆
    memory_manager.add_memory("机器学习是人工智能的一个分支", importance=0.9)
    memory_manager.add_memory("深度学习是机器学习的一个分支", importance=0.8)
    memory_manager.add_memory("这是一个不相关的记忆", importance=0.3)

    # 异步检索
    async def test():
        results = await memory_manager.retrieve_relevant("机器学习", top_k=2)
        assert len(results) <= 2
        # 检查是否返回了相关记忆
        content_list = [r.content for r in results]
        assert any("机器学习" in c for c in content_list)

    asyncio.run(test())


def test_search_by_content(memory_manager):
    """测试根据内容搜索记忆"""
    memory_manager.add_memory("机器学习相关的内容", importance=0.9)
    memory_manager.add_memory("深度学习相关的内容", importance=0.8)

    async def test():
        results = await memory_manager.search_by_content("机器学习")
        assert len(results) == 1
        assert "机器学习" in results[0].content

    asyncio.run(test())


def test_access_memory(memory_manager):
    """测试访问记忆"""
    memory_id = memory_manager.add_memory("测试记忆", importance=0.5)

    # 第一次访问
    memory = memory_manager.access_memory(memory_id)
    assert memory is not None
    assert memory.access_count == 1

    # 第二次访问
    memory = memory_manager.access_memory(memory_id)
    assert memory.access_count == 2


def test_update_memory(memory_manager):
    """测试更新记忆"""
    memory_id = memory_manager.add_memory("原始内容", importance=0.5)

    # 更新内容
    success = memory_manager.update_memory(
        memory_id,
        content="更新后的内容",
        importance=0.8
    )

    assert success is True

    memory = memory_manager.get_memory(memory_id)
    assert memory.content == "更新后的内容"
    assert memory.importance == 0.8


def test_delete_memory(memory_manager):
    """测试删除记忆"""
    memory_id = memory_manager.add_memory("要删除的记忆", importance=0.5)

    success = memory_manager.delete_memory(memory_id)
    assert success is True
    assert len(memory_manager.memories) == 0


def test_cleanup_old_memories(memory_manager):
    """测试清理旧记忆"""
    # 添加一条旧记忆
    old_memory = MemoryItem(
        id="old_mem",
        content="旧记忆",
        importance=0.5,
        created_at=datetime.now() - timedelta(days=40),
        accessed_at=datetime.now() - timedelta(days=40),
        access_count=0
    )
    memory_manager.memories["old_mem"] = old_memory

    # 添加一条新记忆
    memory_manager.add_memory("新记忆", importance=0.5)

    # 清理
    deleted_count = memory_manager.cleanup_old_memories(days_threshold=30)
    assert deleted_count == 1
    assert len(memory_manager.memories) == 1


def test_get_memory_stats(memory_manager):
    """测试获取记忆统计"""
    memory_manager.add_memory("记忆1", importance=0.5)
    memory_manager.add_memory("记忆2", importance=0.7)
    memory_manager.add_memory("记忆3", importance=0.9)

    stats = memory_manager.get_memory_stats()

    assert stats["total"] == 3
    assert stats["average_importance"] == pytest.approx(0.7)
    assert stats["total_access_count"] == 0
