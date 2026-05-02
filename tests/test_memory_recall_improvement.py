"""
记忆系统改进测试

测试内容:
1. 智能触发判断（历史关键词检测）
2. 时间衰减（遗忘曲线）
3. 重要性阈值过滤
"""

import time
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents_v2.core.context_injector import IntelligentContextInjector, MemoryEntry


class MockMemoryEntry:
    """模拟记忆条目用于测试"""
    def __init__(self, content, importance, last_accessed=None):
        self.content = content
        self.importance = importance
        self.last_accessed = last_accessed or time.time()
        self.memory_type = "long_term"


def test_trigger_judgment():
    """测试1: 智能触发判断"""
    print("\n" + "="*60)
    print("测试1: 智能触发判断 (_should_recall_memories)")
    print("="*60)

    injector = IntelligentContextInjector()

    test_cases = [
        ("帮我改进之前那个登录功能", True, "包含'之前'关键词"),
        ("上次你帮我写的代码在哪里", True, "包含'上次'关键词"),
        ("还记得我们之前讨论的内容吗", True, "包含'还记得'关键词"),
        ("帮我写一篇关于深度学习的论文", False, "无历史关键词"),
        ("搜索一下最新的AI论文", False, "无历史关键词"),
    ]

    all_passed = True
    for query, expected, description in test_cases:
        result = injector._should_recall_memories(query, None)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] '{query[:30]}...' -> {result} (expected: {expected}) - {description}")
        if result != expected:
            all_passed = False

    print(f"\n测试1结果: {'通过' if all_passed else '失败'}")
    return all_passed


def test_time_decay():
    """测试2: 时间衰减（遗忘曲线）"""
    print("\n" + "="*60)
    print("测试2: 时间衰减 (_calculate_retention_score)")
    print("="*60)

    injector = IntelligentContextInjector(enable_time_decay=True)

    # 测试用例: 不同时间间隔的保留分数
    now = time.time()

    test_cases = [
        # (importance, last_accessed_ago_seconds, min_expected_retention, description)
        (0.8, 0, 0.75, "刚刚访问，高重要性"),
        (0.8, 3600, 0.5, "1小时前，高重要性"),
        (0.8, 86400, 0.3, "1天前，高重要性"),
        (0.5, 0, 0.45, "刚刚访问，中等重要性"),
        (0.5, 3600, 0.25, "1小时前，中等重要性"),
        (0.3, 0, 0.25, "刚刚访问，低重要性"),
    ]

    all_passed = True
    for importance, ago_seconds, min_expected, description in test_cases:
        mem = MockMemoryEntry("test", importance, now - ago_seconds)
        retention = injector._calculate_retention_score(mem, now)
        passed = retention >= min_expected
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] importance={importance}, ago={ago_seconds}s -> retention={retention:.3f} (min={min_expected:.3f}) - {description}")
        if not passed:
            all_passed = False

    print(f"\n测试2结果: {'通过' if all_passed else '失败'}")
    return all_passed


def test_importance_threshold():
    """测试3: 重要性阈值过滤"""
    print("\n" + "="*60)
    print("测试3: 重要性阈值过滤 (_prioritize_memories)")
    print("="*60)

    injector = IntelligentContextInjector(
        importance_threshold=0.3,
        enable_time_decay=True
    )

    # 创建测试记忆
    memories = [
        MockMemoryEntry("高重要性记忆", 0.9, time.time()),
        MockMemoryEntry("中等重要性记忆", 0.5, time.time()),
        MockMemoryEntry("低重要性记忆", 0.2, time.time()),  # 应该被过滤
        MockMemoryEntry("刚好及格", 0.3, time.time()),  # 刚好等于阈值
    ]

    result = injector._prioritize_memories(memories, [])

    # 检查低重要性记忆是否被过滤
    low_importance_filtered = len(result) < len(memories)
    has_high_priority = any(m.content == "高重要性记忆" for m in result)

    print(f"  Input: {len(memories)} memories")
    print(f"  Output: {len(result)} memories")
    print(f"  Low importance (0.2) filtered: {'YES' if low_importance_filtered else 'NO'}")
    print(f"  High importance (0.9) kept: {'YES' if has_high_priority else 'NO'}")

    all_passed = low_importance_filtered and has_high_priority
    print(f"\n测试3结果: {'通过' if all_passed else '失败'}")
    return all_passed


def test_context_builder():
    """测试4: ContextBuilder 基础功能"""
    print("\n" + "="*60)
    print("测试4: ContextBuilder 基础功能")
    print("="*60)

    from src.agents_v2.core.context_injector import ContextBuilder

    builder = ContextBuilder(max_tokens=1000)

    # 添加不同优先级的内容
    builder.add("低优先级内容", priority=1, token_count=50)
    builder.add("中优先级内容", priority=5, token_count=50)
    builder.add("高优先级内容", priority=10, token_count=50)

    result = builder.build()

    # 验证高优先级内容在前面
    high_pos = result.find("高优先级内容")
    low_pos = result.find("低优先级内容")

    passed = high_pos < low_pos and high_pos >= 0
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] High priority content appears before low priority")

    print(f"\n测试4结果: {'通过' if passed else '失败'}")
    return passed


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("记忆系统改进测试")
    print("="*60)

    results = []

    results.append(("触发判断", test_trigger_judgment()))
    results.append(("时间衰减", test_time_decay()))
    results.append(("重要性阈值", test_importance_threshold()))
    results.append(("ContextBuilder", test_context_builder()))

    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] - {name}")
        if not passed:
            all_passed = False

    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())