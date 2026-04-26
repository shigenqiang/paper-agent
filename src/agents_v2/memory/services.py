"""
记忆服务层 - Memory Services

核心服务:
1. MemoryExtractor - 记忆提取 (LLM驱动)
2. SummaryGenerator - 摘要生成
3. RetrievalEngine - 检索引擎
4. ForgettingController - 遗忘控制器
"""
import asyncio
import time
import re
import json
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field

from .types import MemoryEntry, MemoryType, ImportanceLevel


# Mem0式的提取Prompt
EXTRACTION_PROMPT = """你是一个个人信息整理专家，专注于准确存储事实、用户记忆和偏好。

从对话中提取有价值的信息，以JSON数组格式返回。

提取类型:
1. preference - 用户偏好 (language=Python, framework=PyTorch)
2. fact - 事实信息 (user_is_developer=true, company=Google)
3. skill - 技能/能力 (skills=["Python", "Machine Learning"])
4. goal - 目标/意图 (goals=["write a paper"])
5. constraint - 约束/限制 (constraints=["deadline=2026-01"])

规则:
- 只提取明确表达的信息，不要猜测
- 使用简洁的键值对格式
- 返回JSON数组，每项包含: type, key, value, importance (0.0-1.0)

对话内容:
{messages}

返回JSON数组:"""


class MemoryOperation(str):
    """记忆操作类型"""
    ADD = "ADD"           # 添加新记忆
    UPDATE = "UPDATE"     # 更新已有记忆
    DELETE = "DELETE"     # 删除记忆
    NOOP = "NOOP"         # 不操作


@dataclass
class ExtractionResult:
    """提取结果"""
    type: str           # preference/fact/skill/goal/constraint
    key: str            # 记忆键
    value: Any          # 记忆值
    importance: float   # 重要性 (0.0-1.0)
    operation: str = MemoryOperation.ADD  # 操作类型


class MemoryExtractor:
    """
    记忆提取器 (LLM驱动 - Mem0风格)

    职责: 从对话中自动提取有价值的信息

    工作流程 (Mem0式):
    1. 接收原始对话 (messages)
    2. 使用LLM提取候选记忆 (Single-pass ADD-only)
    3. 与已有记忆比较，决定操作 (ADD/UPDATE/DELETE/NOOP)
    4. 存入相应记忆层

    特点:
    - Single-pass: 一次LLM调用
    - ADD-only: 记忆只添加不删除 (accumulate)
    - 智能决策: LLM决定更新策略
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Args:
            llm_client: LLM客户端 (用于智能提取)
        """
        self.llm_client = llm_client
        self._extraction_patterns = self._init_patterns()
        self._use_llm = llm_client is not None

    def _init_patterns(self) -> Dict[str, Callable]:
        """初始化提取模式 (备用)"""
        return {
            "email": lambda text: re.findall(r'[\w.-]+@[\w.-]+\.\w+', text),
            "url": lambda text: re.findall(r'https?://[^\s]+', text),
            "date": lambda text: re.findall(r'\d{4}-\d{2}-\d{2}', text),
            "number": lambda text: re.findall(r'\d+(?:\.\d+)?', text),
        }

    async def extract_with_llm(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[ExtractionResult]:
        """
        使用LLM提取记忆 (Mem0风格)

        Args:
            messages: 消息列表

        Returns:
            ExtractionResult列表
        """
        if not self._use_llm or self.llm_client is None:
            return await self.extract_candidates(messages)

        # 构建对话文本
        messages_text = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in messages[-10:]  # 最近10条
        ])

        prompt = EXTRACTION_PROMPT.format(messages=messages_text)

        try:
            # 调用LLM
            response = await self.llm_client.ainvoke(prompt)

            # 解析JSON响应
            content = response.content if hasattr(response, 'content') else str(response)

            # 尝试提取JSON数组
            json_str = self._extract_json(content)
            if json_str:
                items = json.loads(json_str)
                results = []
                for item in items:
                    results.append(ExtractionResult(
                        type=item.get("type", "fact"),
                        key=item.get("key", ""),
                        value=item.get("value"),
                        importance=item.get("importance", 0.5),
                        operation=MemoryOperation.ADD
                    ))
                return results

        except Exception as e:
            # LLM提取失败，回退到正则
            pass

        return await self.extract_candidates(messages)

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON数组"""
        # 尝试找JSON数组
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            return text[start:end]
        return None

    async def extract_candidates(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[ExtractionResult]:
        """
        从消息中提取候选记忆 (正则备用)

        Args:
            messages: 消息列表

        Returns:
            ExtractionResult列表
        """
        candidates = []

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")

            # 使用正则提取结构化信息
            for pattern_name, pattern_fn in self._extraction_patterns.items():
                matches = pattern_fn(content)
                for match in matches:
                    candidates.append(ExtractionResult(
                        type=pattern_name,
                        key=f"{pattern_name}_{match[:20]}",
                        value=match,
                        importance=0.5,
                        operation=MemoryOperation.ADD
                    ))

            # 关键事实提取
            key_facts = self._extract_key_facts(content)
            candidates.extend(key_facts)

        return candidates

    def _extract_key_facts(self, text: str) -> List[ExtractionResult]:
        """提取关键事实"""
        facts = []

        # 识别 "X是Y" 类型的陈述
        statements = re.findall(r'([A-Za-z0-9\s]+)[:是]([A-Za-z0-9\s，。,.。]+)', text)
        for subject, obj in statements:
            if len(subject) > 2 and len(obj) > 2:
                facts.append(ExtractionResult(
                    type="fact",
                    key=subject.strip().lower().replace(" ", "_"),
                    value=obj.strip(),
                    importance=0.6,
                    operation=MemoryOperation.ADD
                ))

        return facts

    async def decide_operations(
        self,
        new_memories: List[ExtractionResult],
        existing_memories: List[MemoryEntry]
    ) -> List[ExtractionResult]:
        """
        决定记忆操作 (ADD/UPDATE/DELETE/NOOP)

        Mem0风格:
        - ADD: 新记忆
        - UPDATE: 已存在但有新信息
        - NOOP: 无变化

        Args:
            new_memories: 新提取的记忆
            existing_memories: 已有记忆

        Returns:
            带有操作类型的记忆列表
        """
        # 构建已有记忆的键索引
        existing_keys = {mem.id: mem for mem in existing_memories}

        for memory in new_memories:
            key = f"{memory.type}_{memory.key}"

            if key in existing_keys:
                # 检查是否需要更新
                existing = existing_keys[key]
                if memory.value != existing.content:
                    memory.operation = MemoryOperation.UPDATE
                else:
                    memory.operation = MemoryOperation.NOOP

        return new_memories

    async def extract_and_store(
        self,
        messages: List[Dict[str, Any]],
        memory_manager: Any,
        task_id: str,
        existing_memories: Optional[List[MemoryEntry]] = None
    ) -> Dict[str, List[str]]:
        """
        提取并存储记忆

        Args:
            messages: 消息列表
            memory_manager: 记忆管理器
            task_id: 任务ID
            existing_memories: 已有记忆 (用于去重)

        Returns:
            操作统计 {added: [], updated: [],noop: []}
        """
        # 1. 提取记忆 (优先使用LLM)
        new_memories = await self.extract_with_llm(messages)

        # 2. 决定操作
        if existing_memories:
            new_memories = await self.decide_operations(new_memories, existing_memories)

        # 3. 存储记忆
        stats = {"added": [], "updated": [], "noop": []}

        for memory in new_memories:
            if memory.operation == MemoryOperation.NOOP:
                stats["noop"].append(memory.key)
                continue

            memory_key = f"extracted_{task_id}_{memory.type}_{memory.key}"

            await memory_manager.remember(
                key=memory_key,
                value={"type": memory.type, "value": memory.value},
                tags=[memory.type, "extracted"],
                persist=True,
                importance=memory.importance
            )

            if memory.operation == MemoryOperation.ADD:
                stats["added"].append(memory_key)
            elif memory.operation == MemoryOperation.UPDATE:
                stats["updated"].append(memory_key)

        return stats

    async def deduplicate(
        self,
        new_facts: List[Dict[str, Any]],
        existing_memories: List[MemoryEntry]
    ) -> List[Dict[str, Any]]:
        """
        Args:
            new_facts: 新事实
            existing_memories: 现有记忆

        Returns:
            去重后的新事实
        """
        existing_values = set()
        for memory in existing_memories:
            content = str(memory.content)
            existing_values.add(content)

        deduplicated = []
        for fact in new_facts:
            value_str = str(fact.get("value", ""))
            if value_str not in existing_values:
                deduplicated.append(fact)

        return deduplicated


class SummaryGenerator:
    """
    摘要生成器

    职责: 定期生成会话摘要

    触发条件:
    - 每N条消息
    - 每N分钟
    - 会话结束时
    """

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    async def generate_summary(
        self,
        messages: List[Dict[str, Any]],
        task_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成摘要

        Args:
            messages: 消息列表
            task_id: 任务ID
            options: 额外选项

        Returns:
            摘要字符串
        """
        if not messages:
            return ""

        options = options or {}

        # 如果有LLM客户端，使用LLM生成摘要
        if self.llm_client:
            return await self._generate_llm_summary(messages, task_id, options)

        # 否则使用简单摘要
        return self._generate_simple_summary(messages, task_id)

    async def _generate_llm_summary(
        self,
        messages: List[Dict[str, Any]],
        task_id: str,
        options: Dict[str, Any]
    ) -> str:
        """使用LLM生成摘要"""
        # 构建提示
        message_texts = [f"{m.get('role', '')}: {m.get('content', '')}" for m in messages]
        combined = "\n".join(message_texts[-20:])  # 最近20条

        prompt = f"""请为以下对话生成简洁摘要:

任务ID: {task_id}

对话:
{combined}

摘要应包含:
1. 任务进度摘要
2. 关键决策记录
3. 待处理事项
4. 用户反馈

请用中文回答，摘要长度控制在200字以内。
"""

        try:
            # 调用LLM
            response = await self.llm_client.ainvoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception:
            return self._generate_simple_summary(messages, task_id)

    def _generate_simple_summary(
        self,
        messages: List[Dict[str, Any]],
        task_id: str
    ) -> str:
        """生成简单统计摘要"""
        total = len(messages)
        agents = set(m.get("agent_id", "unknown") for m in messages if m.get("agent_id"))
        roles = set(m.get("role", "unknown") for m in messages)

        summary = f"""## 会话摘要

- 任务ID: {task_id}
- 总消息数: {total}
- 参与Agent: {', '.join(agents) if agents else 'N/A'}
- 消息类型: {', '.join(roles) if roles else 'N/A'}
- 时间范围: {messages[0].get('timestamp', 'N/A') if messages else 'N/A'} - {messages[-1].get('timestamp', 'N/A') if messages else 'N/A'}
"""
        return summary

    def should_trigger(
        self,
        message_count: int,
        time_since_last: float,
        config: Dict[str, Any]
    ) -> bool:
        """
        检查是否应该触发摘要

        Args:
            message_count: 当前消息数
            time_since_last: 距离上次摘要的时间(秒)
            config: 配置 {trigger_message_count, trigger_interval_seconds}

        Returns:
            是否触发
        """
        trigger_count = config.get("trigger_message_count", 20)
        trigger_interval = config.get("trigger_interval_seconds", 300)

        return (
            message_count >= trigger_count or
            time_since_last >= trigger_interval
        )


class RetrievalEngine:
    """
    检索引擎

    职责: 统一的记忆检索接口

    检索策略:
    1. 语义检索 - 向量相似度
    2. 关键词检索 - 精确匹配
    3. 标签检索 - 精确匹配
    4. 时序检索 - 时间范围过滤
    5. 关系检索 - 图查询
    """

    def __init__(
        self,
        long_term_memory: Any,
        graph_store: Optional[Any] = None
    ):
        self.long_term_memory = long_term_memory
        self.graph_store = graph_store

    async def retrieve(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """
        统一检索接口

        Args:
            query: 查询字符串
            memory_types: 记忆类型过滤
            limit: 返回数量限制
            filters: 额外过滤条件

        Returns:
            匹配的MemoryEntry列表
        """
        filters = filters or {}
        memory_types = memory_types or [MemoryType.LONG_TERM]

        results = []

        for mem_type in memory_types:
            if mem_type == MemoryType.LONG_TERM:
                # 语义检索
                semantic_results = await self.long_term_memory.search(
                    query=query,
                    limit=limit,
                    tags=filters.get("tags")
                )
                results.extend(semantic_results)

            elif mem_type == MemoryType.SESSION:
                # 会话检索 (需要session memory实例)
                session_results = await self._search_session(query, filters, limit)
                results.extend(session_results)

        # 多策略结果融合
        fused = self._fuse_results(results, query)

        return fused[:limit]

    async def _search_session(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int
    ) -> List[MemoryEntry]:
        """搜索会话记忆"""
        # 简化实现
        return []

    def _fuse_results(
        self,
        results: List[MemoryEntry],
        query: str
    ) -> List[MemoryEntry]:
        """
        多策略结果融合

        Args:
            results: 检索结果列表
            query: 查询字符串

        Returns:
            融合排序后的结果
        """
        # 简单实现：按相关性评分排序
        scored_results = []

        for entry in results:
            # 计算与查询的相关性
            content_str = str(entry.content).lower()
            query_lower = query.lower()

            # 词匹配分数
            query_words = set(query_lower.split())
            content_words = set(content_str.split())
            overlap = len(query_words & content_words)
            word_score = overlap / max(len(query_words), 1)

            # 标签匹配分数
            tag_score = 1.0 if query_lower in entry.tags else 0.0

            # 重要性分数
            importance_score = entry.importance

            # 综合分数
            total_score = (
                word_score * 0.4 +
                tag_score * 0.3 +
                importance_score * 0.3
            )

            scored_results.append((total_score, entry))

        # 按分数排序
        scored_results.sort(key=lambda x: x[0], reverse=True)

        return [entry for _, entry in scored_results]

    async def get_context_for_agent(
        self,
        agent_id: str,
        task_id: str,
        max_tokens: int = 4096
    ) -> str:
        """
        为Agent生成上下文字符串

        Args:
            agent_id: Agent ID
            task_id: 任务ID
            max_tokens: 最大token数

        Returns:
            上下文字符串
        """
        # 检索相关记忆
        results = await self.retrieve(
            query=task_id,
            limit=10
        )

        if not results:
            return ""

        # 构建上下文
        parts = ["## 相关记忆\n"]
        current_length = 0

        for entry in results:
            content_str = str(entry.content)
            entry_length = len(content_str)

            if current_length + entry_length > max_tokens:
                break

            parts.append(f"- [{entry.memory_type.value}] {content_str[:200]}")
            current_length += entry_length

        return "\n".join(parts)


class ForgettingController:
    """
    遗忘控制器

    职责: 管理记忆的遗忘和强化

    遗忘模型 (参考MemoryBank):
    - 基于艾宾浩斯遗忘曲线
    - 重要性加权
    """

    def __init__(
        self,
        long_term_memory: Any,
        base_retention_time: float = 86400,  # 1天
        importance_scale: float = 2.0
    ):
        self.long_term_memory = long_term_memory
        self.base_retention_time = base_retention_time
        self.importance_scale = importance_scale

    def calculate_retention_score(
        self,
        last_accessed: float,
        importance: float,
        importance_level: ImportanceLevel
    ) -> float:
        """
        计算保留分数

        公式: importance * e^(-t/S)

        Args:
            last_accessed: 上次访问时间戳
            importance: 重要性 (0.0-1.0)
            importance_level: 重要性等级

        Returns:
            保留分数 (0.0-1.0)
        """
        t = time.time() - last_accessed

        # 根据重要性等级设置记忆强度
        S_map = {
            ImportanceLevel.CRITICAL: float('inf'),
            ImportanceLevel.HIGH: self.base_retention_time * 7,
            ImportanceLevel.MEDIUM: self.base_retention_time,
            ImportanceLevel.LOW: self.base_retention_time / 24,
        }
        S = S_map.get(importance_level, self.base_retention_time)

        # 计算保留率
        if S == float('inf'):
            retention = importance
        else:
            retention = importance * (1.0 if S == float('inf') else __import__('math').exp(-t / S))

        return min(1.0, max(0.0, retention))

    async def cleanup(
        self,
        threshold: float = 0.1,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        清理低保留分数的记忆

        Args:
            threshold: 保留分数阈值
            batch_size: 批处理大小

        Returns:
            清理统计
        """
        deleted_count = 0
        kept_count = 0

        all_keys = await self.long_term_memory.list_all()

        for key in all_keys[:batch_size]:
            # 获取记忆内容来计算保留分数
            # 简化实现：直接从搜索结果获取
            results = await self.long_term_memory.search(key, limit=1)
            if not results:
                continue

            metadata = results[0].metadata if hasattr(results[0], 'metadata') else {}

            last_accessed = metadata.get("last_accessed", time.time())
            importance = metadata.get("importance", 0.5)

            # 获取重要性等级
            importance_level_str = metadata.get("importance_level", "MEDIUM")
            try:
                importance_level = ImportanceLevel[importance_level_str]
            except KeyError:
                importance_level = ImportanceLevel.MEDIUM

            retention = self.calculate_retention_score(
                last_accessed, importance, importance_level
            )

            if retention < threshold:
                await self.long_term_memory.delete(key)
                deleted_count += 1
            else:
                kept_count += 1

        return {
            "deleted": deleted_count,
            "kept": kept_count,
            "threshold": threshold
        }

    async def reinforce(
        self,
        memory_key: str,
        boost: float = 0.1
    ) -> None:
        """
        强化记忆

        Args:
            memory_key: 记忆键
            boost: 强化量
        """
        results = await self.long_term_memory.search(memory_key, limit=1)
        if results:
            entry = results[0]
            entry.importance = min(1.0, entry.importance + boost)
            entry.access_count += 1
            # 实际应该更新存储中的值


class MemoryCache:
    """
    记忆缓存层 (LRU)

    特点:
    - OrderedDict实现
    - 可配置大小
    - 自动淘汰最久未使用的
    """

    def __init__(self, max_size: int = 1000):
        self._cache = {}
        self._access_order: List[str] = []
        self._max_size = max_size

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any]
    ) -> Any:
        """
        获取或创建缓存

        Args:
            key: 缓存键
            factory: 工厂函数 (当key不存在时调用)

        Returns:
            缓存值
        """
        if key in self._cache:
            # 移到最前
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.insert(0, key)
            return self._cache[key]

        # 创建新值
        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()

        # 添加到缓存
        self._cache[key] = value
        self._access_order.insert(0, key)

        # 淘汰
        if len(self._cache) > self._max_size:
            oldest_key = self._access_order.pop()
            del self._cache[oldest_key]

        return value

    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        return self._cache.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        if key in self._cache:
            if key in self._access_order:
                self._access_order.remove(key)
        else:
            if len(self._cache) >= self._max_size:
                oldest_key = self._access_order.pop()
                del self._cache[oldest_key]

        self._cache[key] = value
        self._access_order.insert(0, key)

    def invalidate(self, key: str) -> None:
        """使缓存失效"""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._access_order.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "utilization": len(self._cache) / self._max_size if self._max_size > 0 else 0
        }


class BatchMemoryOperations:
    """
    批量记忆操作

    职责:
    - 批量存储
    - 批量搜索
    - 并发控制
    """

    def __init__(self, memory_manager: Any):
        self.memory_manager = memory_manager
        self._semaphore = asyncio.Semaphore(5)  # 最多5个并发

    async def batch_remember(
        self,
        entries: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        批量存储记忆

        Args:
            entries: 记忆条目列表
            batch_size: 批大小

        Returns:
            {success_count, failed_count, errors}
        """
        success_count = 0
        failed_count = 0
        errors = []

        for i in range(0, len(entries), batch_size):
            batch = entries[i:i + batch_size]

            for entry in batch:
                try:
                    await self.memory_manager.remember(
                        key=entry.get("key", ""),
                        value=entry.get("value"),
                        memory_type=entry.get("memory_type"),
                        tags=entry.get("tags"),
                        persist=entry.get("persist", True),
                        importance=entry.get("importance", 0.5)
                    )
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append({"key": entry.get("key"), "error": str(e)})

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(entries),
            "errors": errors[:10]  # 最多返回10个错误
        }

    async def batch_search(
        self,
        queries: List[str],
        memory_types: Optional[List[Any]] = None,
        limit: int = 10
    ) -> List[List[Any]]:
        """
        批量搜索

        Args:
            queries: 查询列表
            memory_types: 记忆类型列表
            limit: 每个查询的返回数量

        Returns:
            结果列表
        """
        mem_types = memory_types or [MemoryType.LONG_TERM]

        async def search_with_semaphore(query: str) -> List[Any]:
            async with self._semaphore:
                return await self.memory_manager.search(
                    query=query,
                    memory_types=mem_types,
                    limit=limit
                )

        results = await asyncio.gather(
            *[search_with_semaphore(q) for q in queries],
            return_exceptions=True
        )

        # 过滤异常
        filtered_results = []
        for result in results:
            if isinstance(result, Exception):
                filtered_results.append([])
            else:
                filtered_results.append(result)

        return filtered_results

    async def concurrent_search(
        self,
        queries: List[str],
        max_concurrency: int = 5,
        memory_types: Optional[List[Any]] = None,
        limit: int = 10
    ) -> List[List[Any]]:
        """
        并发搜索 (限制并发数)

        Args:
            queries: 查询列表
            max_concurrency: 最大并发数
            memory_types: 记忆类型列表
            limit: 返回数量

        Returns:
            结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        mem_types = memory_types or [MemoryType.LONG_TERM]

        async def search_with_limit(query: str) -> List[Any]:
            async with semaphore:
                try:
                    return await self.memory_manager.search(
                        query=query,
                        memory_types=mem_types,
                        limit=limit
                    )
                except Exception:
                    return []

        return await asyncio.gather(
            *[search_with_limit(q) for q in queries],
            return_exceptions=True
        )


class AdaptiveCache:
    """
    自适应缓存

    特点:
    - 基于访问统计自动调整缓存策略
    - 记录命中率
    - 智能预取
    """

    def __init__(self, base_cache: Optional[MemoryCache] = None):
        self._base_cache = base_cache or MemoryCache(max_size=1000)
        self._access_stats: Dict[str, int] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._lock = asyncio.Lock()

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / total if total > 0 else 0.0

    @property
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "hit_rate": self.hit_rate,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cached_keys": len(self._access_stats),
            "base_cache_stats": self._base_cache.get_stats()
        }

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any]
    ) -> Any:
        """获取或创建缓存(带统计)"""
        # 检查访问统计
        async with self._lock:
            access_count = self._access_stats.get(key, 0)
            self._access_stats[key] = access_count + 1

        # 检查是否应该缓存
        if access_count >= 2 or self.should_cache_by_frequency(key):
            self._cache_hits += 1
            return await self._base_cache.get_or_set(key, factory)
        else:
            self._cache_misses += 1
            # 直接调用factory
            if asyncio.iscoroutinefunction(factory):
                return await factory()
            return factory()

    def should_cache_by_frequency(self, key: str) -> bool:
        """基于访问频率判断是否缓存"""
        return self._access_stats.get(key, 0) >= 2

    async def prefetch(self, keys: List[str], factory_map: Dict[str, Callable]) -> None:
        """
        预取多个键

        Args:
            keys: 要预取的键列表
            factory_map: 键到工厂函数的映射
        """
        for key in keys:
            if key not in self._access_stats:
                continue

            factory = factory_map.get(key)
            if factory:
                await self._base_cache.set(key, await factory() if asyncio.iscoroutinefunction(factory) else factory())

    def invalidate(self, key: str) -> None:
        """使缓存失效"""
        self._base_cache.invalidate(key)
        if key in self._access_stats:
            del self._access_stats[key]

    def reset_stats(self) -> None:
        """重置统计"""
        self._cache_hits = 0
        self._cache_misses = 0


class PrefetchStrategy:
    """
    预取策略

    基于访问模式预测并预取
    """

    def __init__(self, cache: AdaptiveCache):
        self.cache = cache
        self._access_history: List[str] = []
        self._pattern_window = 10

    def analyze_pattern(self) -> Dict[str, Any]:
        """
        分析访问模式

        Returns:
            {pattern_type, frequent_keys, next_predict}
        """
        if len(self._access_history) < self._pattern_window:
            return {
                "pattern_type": "insufficient_data",
                "frequent_keys": [],
                "next_predict": []
            }

        # 统计最近访问
        recent = self._access_history[-self._pattern_window:]
        key_counts = {}
        for key in recent:
            key_counts[key] = key_counts.get(key, 0) + 1

        # 频繁访问的键
        frequent_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)
        frequent_keys = [k for k, _ in frequent_keys[:5]]

        # 简单预测：下次可能访问最频繁的几个键
        next_predict = frequent_keys[:3]

        return {
            "pattern_type": "temporal",
            "frequent_keys": frequent_keys,
            "next_predict": next_predict
        }

    def record_access(self, key: str) -> None:
        """记录访问"""
        self._access_history.append(key)
        if len(self._access_history) > 100:
            self._access_history = self._access_history[-100:]

    async def execute_prefetch(self, factory_map: Dict[str, Callable]) -> None:
        """执行预取"""
        pattern = self.analyze_pattern()
        keys_to_prefetch = pattern.get("next_predict", [])

        await self.cache.prefetch(keys_to_prefetch, factory_map)


class QueryCache:
    """
    查询结果缓存

    特点:
    - TTL过期机制
    - 查询结果缓存
    - 自动去重
    """

    def __init__(self, ttl_seconds: float = 60.0, max_size: int = 1000):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = asyncio.Lock()

    def _is_expired(self, timestamp: float) -> bool:
        """检查是否过期"""
        return (time.time() - timestamp) > self._ttl

    async def get_or_query(
        self,
        query: str,
        query_func: Callable[[], Any]
    ) -> Any:
        """
        获取缓存或执行查询

        Args:
            query: 查询字符串
            query_func: 查询函数

        Returns:
            查询结果
        """
        async with self._lock:
            # 检查缓存
            if query in self._cache:
                result, timestamp = self._cache[query]
                if not self._is_expired(timestamp):
                    return result
                del self._cache[query]

        # 执行查询
        result = await query_func() if asyncio.iscoroutinefunction(query_func) else query_func()

        # 更新缓存
        async with self._lock:
            if len(self._cache) >= self._max_size:
                # 删除最老的
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]

            self._cache[query] = (result, time.time())

        return result

    async def get(self, query: str) -> Optional[Any]:
        """获取缓存结果"""
        async with self._lock:
            if query in self._cache:
                result, timestamp = self._cache[query]
                if not self._is_expired(timestamp):
                    return result
                del self._cache[query]
        return None

    async def invalidate(self, query: str) -> None:
        """使缓存失效"""
        async with self._lock:
            if query in self._cache:
                del self._cache[query]

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "cached_queries": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl
        }


class ConcurrentQueryOptimizer:
    """
    并发查询优化器

    特点:
    - 查询去重
    - 并发限制
    - 结果复用
    """

    def __init__(self, max_concurrency: int = 10):
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._pending_queries: Dict[str, asyncio.Future] = {}

    async def batch_query_with_dedup(
        self,
        queries: List[str],
        executor: Callable[[str], Any]
    ) -> Dict[str, Any]:
        """
        带去重的批量查询

        Args:
            queries: 查询列表
            executor: 执行函数

        Returns:
            {query: result} 字典
        """
        # 去重
        unique_queries = list(dict.fromkeys(queries))

        # 创建任务
        tasks = [
            self._execute_with_dedup(query, executor)
            for query in unique_queries
        ]

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 构建结果字典
        result_map = {}
        for query, result in zip(unique_queries, results):
            if isinstance(result, Exception):
                result_map[query] = []
            else:
                result_map[query] = result

        return result_map

    async def _execute_with_dedup(
        self,
        query: str,
        executor: Callable[[str], Any]
    ) -> Any:
        """
        带去重的单查询

        Args:
            query: 查询字符串
            executor: 执行函数

        Returns:
            查询结果
        """
        # 检查是否有正在执行的相同查询
        if query in self._pending_queries:
            return await self._pending_queries[query]

        # 创建Future
        future = asyncio.Future()
        self._pending_queries[query] = future

        try:
            async with self._semaphore:
                result = await executor(query) if asyncio.iscoroutinefunction(executor) else executor(query)
                future.set_result(result)
                return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            del self._pending_queries[query]
