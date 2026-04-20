"""统一记忆管理器测试"""
import pytest
import asyncio
from datetime import datetime
from src.memory.memory_manager import UnifiedMemoryManager
from src.memory.semantic_memory import MemoryType


@pytest.fixture
def memory_manager(tmp_path):
    """创建记忆管理器fixture"""
    return UnifiedMemoryManager(storage_dir=str(tmp_path / "memory"))


def test_create_session(memory_manager):
    """测试创建会话"""
    session = memory_manager.create_session("test_session")

    assert session is not None
    assert session.session_id == "test_session"
    assert len(memory_manager.short_term_memories) == 1


def test_get_or_create_session(memory_manager):
    """测试获取或创建会话"""
    session1 = memory_manager.get_or_create_session("test_session")
    session2 = memory_manager.get_or_create_session("test_session")

    assert session1 is session2
    assert len(memory_manager.short_term_memories) == 1


def test_add_message(memory_manager):
    """测试添加消息"""
    memory_manager.create_session("test_session")

    success = memory_manager.add_message(
        "test_session",
        "user",
        "Hello, this is a test message"
    )

    assert success is True

    session = memory_manager.get_session("test_session")
    assert len(session.conversation_history) == 1
    assert session.conversation_history[0].content == "Hello, this is a test message"


def test_get_recent_messages(memory_manager):
    """测试获取最近消息"""
    memory_manager.create_session("test_session")

    memory_manager.add_message("test_session", "user", "Message 1")
    memory_manager.add_message("test_session", "assistant", "Response 1")
    memory_manager.add_message("test_session", "user", "Message 2")

    recent = memory_manager.get_recent_messages("test_session", n=2)

    assert len(recent) == 2
    assert recent[0]["content"] == "Response 1"
    assert recent[1]["content"] == "Message 2"


def test_add_semantic_memory(memory_manager):
    """测试添加语义记忆"""
    memory_id = memory_manager.add_semantic_memory(
        content="Machine learning is a subset of AI",
        memory_type=MemoryType.CONCEPT,
        importance=0.9,
        tags=["AI", "ML"]
    )

    assert memory_id is not None
    assert memory_id.startswith("sem_")
    assert len(memory_manager.semantic_memory.memories) == 1


def test_add_fact(memory_manager):
    """测试添加事实"""
    memory_id = memory_manager.add_fact(
        fact="Python is a popular programming language",
        importance=0.8
    )

    assert memory_id is not None
    memory = memory_manager.semantic_memory.get_memory(memory_id)
    assert memory.memory_type == MemoryType.FACT


def test_add_preference(memory_manager):
    """测试添加偏好"""
    memory_id = memory_manager.add_preference(
        preference="User prefers detailed explanations"
    )

    assert memory_id is not None
    memory = memory_manager.semantic_memory.get_memory(memory_id)
    assert memory.memory_type == MemoryType.FACT
    assert "user_preference" in memory.tags


def test_add_insight(memory_manager):
    """测试添加洞察"""
    memory_id = memory_manager.add_insight(
        insight="Users with technical background prefer code examples"
    )

    assert memory_id is not None
    memory = memory_manager.semantic_memory.get_memory(memory_id)
    assert memory.memory_type == MemoryType.INSIGHT


@pytest.mark.asyncio
async def test_retrieve(memory_manager):
    """测试检索记忆"""
    # 添加一些记忆
    memory_manager.add_semantic_memory(
        content="Machine learning is about teaching computers to learn",
        memory_type=MemoryType.CONCEPT,
        importance=0.9,
        tags=["ML"]
    )

    memory_manager.add_semantic_memory(
        content="Deep learning is a subset of machine learning",
        memory_type=MemoryType.CONCEPT,
        importance=0.8,
        tags=["DL", "ML"]
    )

    # 检索
    results = await memory_manager.retrieve("machine learning")

    assert len(results) > 0
    assert any("machine learning" in r.content.lower() for r in results)


@pytest.mark.asyncio
async def test_retrieve_with_session(memory_manager):
    """测试从会话检索"""
    # 创建会话并添加消息
    session = memory_manager.create_session("test_session")
    session.add_turn("user", "Tell me about neural networks")
    session.add_turn("assistant", "Neural networks are computing systems...")

    # 检索
    results = await memory_manager.retrieve("neural networks", session_id="test_session")

    assert len(results) > 0
    short_term_results = [r for r in results if r.source == "short_term"]
    assert len(short_term_results) > 0


def test_close_session(memory_manager):
    """测试关闭会话"""
    memory_manager.create_session("test_session")
    memory_manager.add_message("test_session", "user", "Test message")

    success = memory_manager.close_session("test_session", save=False)

    assert success is True
    assert "test_session" not in memory_manager.short_term_memories


def test_save_all(memory_manager):
    """测试保存所有记忆"""
    # 创建会话和记忆
    memory_manager.create_session("test_session")
    memory_manager.add_message("test_session", "user", "Test message")
    memory_manager.add_fact("Test fact")

    # 保存
    success = memory_manager.save_all()

    assert success is True


def test_get_stats(memory_manager):
    """测试获取统计信息"""
    stats = memory_manager.get_stats()

    assert "sessions" in stats
    assert "semantic_memory" in stats
    assert "episodic_memory" in stats
    assert "storage" in stats


def test_backup_and_restore(memory_manager, tmp_path):
    """测试备份和恢复"""
    # 添加一些数据
    memory_manager.create_session("test_session")
    memory_manager.add_message("test_session", "user", "Test message")
    memory_manager.add_fact("Test fact")

    # 备份
    backup_success = memory_manager.backup("test_backup")

    # 清空记忆
    memory_manager.semantic_memory.memories.clear()
    memory_manager.episodic_memory.events.clear()
    memory_manager.episodic_memory.episodes.clear()

    # 恢复
    restore_success = memory_manager.restore("test_backup")

    assert backup_success
    assert restore_success
    assert len(memory_manager.semantic_memory.memories) > 0
