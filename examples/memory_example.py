"""记忆系统使用示例"""
import asyncio
from src.memory import (
    UnifiedMemoryManager,
    MemoryType
)


async def main():
    """主函数"""
    print("="*50)
    print("记忆系统使用示例")
    print("="*50)

    # 初始化记忆管理器
    memory_manager = UnifiedMemoryManager()

    # 创建会话
    session_id = "example_session_001"
    print(f"\n1. 创建会话: {session_id}")
    memory_manager.create_session(session_id)

    # 添加对话消息
    print("\n2. 添加对话消息")
    messages = [
        ("user", "我对机器学习很感兴趣，特别是深度学习"),
        ("assistant", "深度学习是机器学习的一个分支，使用神经网络进行学习"),
        ("user", "能否推荐一些入门资源？"),
        ("assistant", "推荐Andrew Ng的深度学习课程和《深度学习》这本书"),
        ("user", "好的，我会学习的。还有，我更喜欢实践而不是理论"),
    ]

    for role, content in messages:
        memory_manager.add_message(session_id, role, content)
        print(f"   {role}: {content[:50]}...")

    # 添加语义记忆
    print("\n3. 添加语义记忆")
    memory_manager.add_fact(
        "深度学习使用多层神经网络进行特征学习",
        importance=0.9,
        source=session_id
    )
    print("   已添加事实: 深度学习使用多层神经网络进行特征学习")

    memory_manager.add_insight(
        "初学者应该从实践项目开始，而不是纯理论学习",
        importance=0.8,
        source=session_id
    )
    print("   已添加洞察: 初学者应该从实践项目开始...")

    memory_manager.add_preference(
        "用户更喜欢实践而不是理论学习",
        source=session_id
    )
    print("   已添加偏好: 用户更喜欢实践而不是理论学习")

    # 检索相关记忆
    print("\n4. 检索相关记忆")
    query = "深度学习入门"
    results = await memory_manager.retrieve(query, session_id=session_id, top_k=5)

    print(f"   查询: {query}")
    print(f"   找到 {len(results)} 条相关记忆:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. [{result.source}] (分数: {result.score:.2f})")
        print(f"      {result.content[:80]}...")

    # 获取统计信息
    print("\n5. 获取统计信息")
    stats = memory_manager.get_stats()
    print(f"   活跃会话数: {stats['sessions']['active']}")
    print(f"   语义记忆数: {stats['semantic_memory']['total']}")
    print(f"   情景记忆事件数: {stats['episodic_memory']['total_events']}")

    # 保存所有记忆
    print("\n6. 保存所有记忆")
    memory_manager.save_all()
    print("   记忆已保存")

    # 关闭会话
    print("\n7. 关闭会话")
    memory_manager.close_session(session_id, save=True)
    print(f"   会话 {session_id} 已关闭")

    print("\n" + "="*50)
    print("示例完成!")
    print("="*50)


async def test_retrieval_with_new_session():
    """测试使用新会话检索之前的记忆"""
    print("\n\n" + "="*50)
    print("测试检索之前的记忆")
    print("="*50)

    # 创建新的记忆管理器（模拟重新启动）
    memory_manager = UnifiedMemoryManager()

    # 创建新会话
    session_id = "new_session_002"
    print(f"\n1. 创建新会话: {session_id}")
    memory_manager.create_session(session_id)

    # 添加新消息
    print("\n2. 添加新消息")
    memory_manager.add_message(
        session_id,
        "user",
        "我想学习深度学习，但不知道从哪里开始"
    )

    # 检索相关记忆（应该能找到之前保存的偏好）
    print("\n3. 检索相关记忆")
    query = "深度学习学习方式"
    results = await memory_manager.retrieve(query, session_id=session_id, top_k=3)

    print(f"   查询: {query}")
    print(f"   找到 {len(results)} 条相关记忆:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. [{result.source}] (分数: {result.score:.2f})")
        print(f"      {result.content[:80]}...")

    print("\n" + "="*50)


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(test_retrieval_with_new_session())
