"""对话历史提炼功能"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from src.memory.short_term_memory import ShortTermMemory, ConversationTurn
from src.memory.semantic_memory import SemanticMemory, MemoryType
from src.memory.episodic_memory import EpisodicMemory, EventType

logger = logging.getLogger(__name__)


class ExtractedInsight(BaseModel):
    """提炼的洞察"""
    content: str
    importance: float
    category: str
    source_turn_ids: List[int]


class ConversationSummary(BaseModel):
    """对话摘要"""
    main_topic: str
    key_points: List[str]
    user_preferences: List[str]
    action_items: List[str]
    extracted_insights: List[ExtractedInsight]
    summary_text: str
    timestamp: datetime


class ConversationSummarizer:
    """对话历史提炼器"""

    def __init__(
        self,
        semantic_memory: SemanticMemory,
        episodic_memory: EpisodicMemory
    ):
        self.semantic_memory = semantic_memory
        self.episodic_memory = episodic_memory

    async def summarize_conversation(
        self,
        short_term_memory: ShortTermMemory,
        session_id: str
    ) -> ConversationSummary:
        """
        总结对话历史
        1. 提取主要话题
        2. 提取关键点
        3. 识别用户偏好
        4. 识别待办事项
        5. 提炼洞察
        """
        history = short_term_memory.get_full_history()

        if not history:
            return ConversationSummary(
                main_topic="No conversation",
                key_points=[],
                user_preferences=[],
                action_items=[],
                extracted_insights=[],
                summary_text="No conversation history to summarize.",
                timestamp=datetime.now()
            )

        # 提取关键信息
        main_topic = self._extract_main_topic(history)
        key_points = self._extract_key_points(history)
        user_preferences = self._extract_user_preferences(history)
        action_items = self._extract_action_items(history)
        extracted_insights = await self._extract_insights(history, session_id)

        # 生成摘要文本
        summary_text = self._generate_summary_text(
            main_topic, key_points, user_preferences, action_items
        )

        summary = ConversationSummary(
            main_topic=main_topic,
            key_points=key_points,
            user_preferences=user_preferences,
            action_items=action_items,
            extracted_insights=extracted_insights,
            summary_text=summary_text,
            timestamp=datetime.now()
        )

        logger.info(f"Summarized conversation for session {session_id}")
        return summary

    def _extract_main_topic(self, history: List[ConversationTurn]) -> str:
        """提取主要话题"""
        # 获取用户的第一条消息作为主要话题
        for turn in history:
            if turn.role == "user":
                # 简化处理，实际应该使用更复杂的NLP
                return turn.content[:100] if len(turn.content) > 100 else turn.content

        return "Unknown topic"

    def _extract_key_points(self, history: List[ConversationTurn]) -> List[str]:
        """提取关键点"""
        key_points = []

        # 查找包含"首先"、"其次"、"总之"等关键词的句子
        keywords = ["首先", "其次", "总之", "关键", "重要", "结论", "结果"]

        for turn in history:
            for keyword in keywords:
                if keyword in turn.content:
                    # 提取包含关键词的句子
                    sentences = turn.content.split("。")
                    for sentence in sentences:
                        if keyword in sentence:
                            key_points.append(sentence.strip())
                            if len(key_points) >= 5:  # 限制关键点数量
                                break
                    if len(key_points) >= 5:
                        break
            if len(key_points) >= 5:
                break

        return key_points[:5]

    def _extract_user_preferences(self, history: List[ConversationTurn]) -> List[str]:
        """提取用户偏好"""
        preferences = []

        # 查找包含"我想要"、"我喜欢"、"我需要"等表达
        preference_patterns = ["我想要", "我喜欢", "我需要", "我希望", "我的偏好", "我倾向"]

        for turn in history:
            if turn.role == "user":
                for pattern in preference_patterns:
                    if pattern in turn.content:
                        # 提取偏好语句
                        sentences = turn.content.split("。")
                        for sentence in sentences:
                            if pattern in sentence:
                                preferences.append(sentence.strip())
                                if len(preferences) >= 3:
                                    break
                    if len(preferences) >= 3:
                        break
            if len(preferences) >= 3:
                break

        return preferences[:3]

    def _extract_action_items(self, history: List[ConversationTurn]) -> List[str]:
        """提取待办事项"""
        action_items = []

        # 查找包含"需要"、"应该"、"计划"等关键词的句子
        action_patterns = ["需要", "应该", "计划", "下一步", "后续", "待办"]

        for turn in history:
            for pattern in action_patterns:
                if pattern in turn.content:
                    sentences = turn.content.split("。")
                    for sentence in sentences:
                        if pattern in sentence:
                            action_items.append(sentence.strip())
                            if len(action_items) >= 5:
                                break
                    if len(action_items) >= 5:
                        break
            if len(action_items) >= 5:
                break

        return action_items[:5]

    async def _extract_insights(
        self,
        history: List[ConversationTurn],
        session_id: str
    ) -> List[ExtractedInsight]:
        """提炼洞察"""
        insights = []

        # 分析对话内容，提取有价值的洞察
        # 这里简化处理，实际应该使用LLM进行分析

        # 提取问题和答案对
        qa_pairs = []
        i = 0
        while i < len(history) - 1:
            if history[i].role == "user" and history[i + 1].role == "assistant":
                qa_pairs.append({
                    "question": history[i].content,
                    "answer": history[i + 1].content,
                    "turn_ids": [history[i].turn_id, history[i + 1].turn_id]
                })
                i += 2
            else:
                i += 1

        # 为每个QA对生成洞察
        for qa in qa_pairs:
            insight_content = f"问题: {qa['question']}\n回答: {qa['answer']}"

            # 简单的重要性评分
            importance = 0.5
            if len(qa['answer']) > 100:  # 较长的回答可能更重要
                importance = 0.7
            if "重要" in qa['answer'] or "关键" in qa['answer']:
                importance = 0.9

            insights.append(ExtractedInsight(
                content=insight_content,
                importance=importance,
                category="qa",
                source_turn_ids=qa['turn_ids']
            ))

        # 保存高重要性的洞察到语义记忆
        for insight in insights:
            if insight.importance >= 0.7:
                self.semantic_memory.add_memory(
                    content=insight.content,
                    memory_type=MemoryType.INSIGHT,
                    importance=insight.importance,
                    source=session_id,
                    metadata={"category": insight.category}
                )

        return insights

    def _generate_summary_text(
        self,
        main_topic: str,
        key_points: List[str],
        user_preferences: List[str],
        action_items: List[str]
    ) -> str:
        """生成摘要文本"""
        parts = [f"对话主题: {main_topic}"]

        if key_points:
            parts.append("\n关键点:")
            for i, point in enumerate(key_points, 1):
                parts.append(f"{i}. {point}")

        if user_preferences:
            parts.append("\n用户偏好:")
            for pref in user_preferences:
                parts.append(f"- {pref}")

        if action_items:
            parts.append("\n待办事项:")
            for item in action_items:
                parts.append(f"- {item}")

        return "\n".join(parts)

    async def save_conversation_to_memory(
        self,
        short_term_memory: ShortTermMemory,
        session_id: str
    ) -> None:
        """
        将对话保存到长期记忆
        1. 总结对话
        2. 保存关键信息到语义记忆
        3. 保存事件到情景记忆
        """
        # 确保有当前情景
        if not self.episodic_memory.current_episode_id:
            self.episodic_memory.start_episode(
                title=f"Session {session_id}",
                description=f"Conversation session {session_id}",
                session_id=session_id
            )

        # 添加对话事件
        history = short_term_memory.get_full_history()
        for turn in history:
            self.episodic_memory.add_event(
                event_type=EventType.INTERACTION,
                description=f"{turn.role}: {turn.content}",
                session_id=session_id,
                importance=0.5
            )

        # 总结对话并保存
        summary = await self.summarize_conversation(short_term_memory, session_id)

        # 保存摘要到语义记忆
        self.semantic_memory.add_memory(
            content=summary.summary_text,
            memory_type=MemoryType.EXPERIENCE,
            importance=0.7,
            source=session_id,
            tags=["conversation", "summary"]
        )

        # 保存关键点
        for point in summary.key_points:
            self.semantic_memory.add_memory(
                content=point,
                memory_type=MemoryType.INSIGHT,
                importance=0.8,
                source=session_id,
                tags=["key_point"]
            )

        # 保存用户偏好
        for pref in summary.user_preferences:
            self.semantic_memory.add_memory(
                content=pref,
                memory_type=MemoryType.FACT,
                importance=0.9,
                source=session_id,
                tags=["user_preference"]
            )

        # 保存待办事项
        for item in summary.action_items:
            self.semantic_memory.add_memory(
                content=item,
                memory_type=MemoryType.PROCEDURE,
                importance=0.8,
                source=session_id,
                tags=["action_item"]
            )

        logger.info(f"Saved conversation to memory for session {session_id}")

    async def retrieve_relevant_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        检索相关上下文
        从短期记忆、长期记忆和情景记忆中检索相关信息
        """
        context = {
            "query": query,
            "session_id": session_id,
            "short_term": [],
            "semantic_memory": [],
            "episodic_memory": []
        }

        # 从短期记忆检索（最近几轮对话）
        # 这里简化处理，实际需要传入short_term_memory实例

        # 从语义记忆检索
        semantic_results = self.semantic_memory.search_by_content(query, top_k)
        context["semantic_memory"] = [
            {
                "content": item.content,
                "type": item.memory_type.value,
                "importance": item.importance,
                "score": score
            }
            for item, score in semantic_results
        ]

        # 从情景记忆检索
        episode_results = self.episodic_memory.search_episodes(query, session_id, top_k)
        context["episodic_memory"] = [
            {
                "title": episode.title,
                "description": episode.description,
                "summary": episode.summary,
                "score": score
            }
            for episode, score in episode_results
        ]

        return context
