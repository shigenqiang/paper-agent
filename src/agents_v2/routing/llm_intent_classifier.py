"""
LLM意图分类器 - LLM Intent Classifier

功能:
1. 基于LLM的意图分类
2. 多意图检测
3. 置信度计算
4. 意图建议生成

设计原则:
- LLM驱动的智能分类
- 多意图支持
- 可配置的分类策略
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class Intent(str, Enum):
    """意图类型"""
    LITERATURE_SEARCH = "literature_search"
    LITERATURE_REVIEW = "literature_review"
    TOPIC_SELECT = "topic_select"
    THESIS_FORMULATE = "thesis_formulate"
    OUTLINE_GENERATE = "outline_generate"
    DRAFT_WRITE = "draft_write"
    FULL_PAPER = "full_paper"
    DIAGNOSTIC = "diagnostic"
    QUESTION = "question"
    COMPARISON = "comparison"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """意图分类结果"""
    primary_intent: Intent
    confidence: float
    all_intents: List[Tuple[Intent, float]] = field(default_factory=list)
    suggested_agents: List[str] = field(default_factory=list)
    reasoning: str = ""


class LLMIntentClassifier:
    """LLM意图分类器"""

    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        model_name: str = "gpt-4",
        fallback_keyword_matching: bool = True
    ):
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.fallback_keyword_matching = fallback_keyword_matching

        # 意图关键词映射
        self._intent_keywords = {
            Intent.LITERATURE_SEARCH: [
                "搜索", "搜索论文", "找论文", "search", "find paper",
                "查找文献", "搜索文献", "找相关文章"
            ],
            Intent.LITERATURE_REVIEW: [
                "综述", "文献综述", "研究现状", "review", "survey",
                "总结", "概览", "overview"
            ],
            Intent.TOPIC_SELECT: [
                "选题", "选题目", "研究方向", "topic", "研究主题",
                "写什么", "研究方向", "课题"
            ],
            Intent.THESIS_FORMULATE: [
                "thesis", "论点", "凝练", "核心观点", "研究目标",
                "研究目的", "thesis statement"
            ],
            Intent.OUTLINE_GENERATE: [
                "大纲", "目录", "结构", "outline", "章节安排",
                "提纲", "文章结构"
            ],
            Intent.DRAFT_WRITE: [
                "写", "撰写", "draft", "write", "初稿", "草稿",
                "生成文章", "生成论文"
            ],
            Intent.FULL_PAPER: [
                "完整论文", "整篇论文", "完整文章", "full paper",
                "从头到尾", "一整篇"
            ],
            Intent.DIAGNOSTIC: [
                "诊断", "问题诊断", "diagnostic", "分析问题",
                "哪里有问题", "诊断问题"
            ],
            Intent.QUESTION: [
                "什么是", "为什么", "如何", "解释", "question",
                "what is", "why", "how", "什么意思"
            ],
            Intent.COMPARISON: [
                "对比", "比较", "区别", "差异", "compare",
                "对比分析", "比较分析", "vs", "versus"
            ]
        }

        # 意图到Agent映射
        self._intent_agent_map = {
            Intent.LITERATURE_SEARCH: ["LiteratureAgent", "PaperSearchAgent"],
            Intent.LITERATURE_REVIEW: ["LiteratureAgent"],
            Intent.TOPIC_SELECT: ["TopicAgent"],
            Intent.THESIS_FORMULATE: ["ThesisAgent"],
            Intent.OUTLINE_GENERATE: ["OutlineAgent"],
            Intent.DRAFT_WRITE: ["DraftWriterAgent"],
            Intent.FULL_PAPER: ["TopicAgent", "LiteratureAgent", "OutlineAgent", "DraftWriterAgent"],
            Intent.DIAGNOSTIC: ["DiagnosticAgent"],
            Intent.QUESTION: ["QAAgent"],
            Intent.COMPARISON: ["LiteratureAgent", "ComparisonAgent"]
        }

    async def classify(self, query: str) -> IntentResult:
        """分类用户查询的意图

        Args:
            query: 用户查询

        Returns:
            IntentResult: 意图分类结果
        """
        # 先用关键词匹配
        keyword_result = self._keyword_match(query)

        # 如果有LLM provider，使用LLM分类
        if self.llm_provider:
            try:
                llm_result = await self._llm_classify(query)
                # 融合结果
                return self._merge_results(keyword_result, llm_result)
            except Exception:
                return keyword_result

        return keyword_result

    def _keyword_match(self, query: str) -> IntentResult:
        """关键词匹配"""
        query_lower = query.lower()
        intent_scores: Dict[Intent, float] = {}

        for intent, keywords in self._intent_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 1

            if score > 0:
                # 归一化分数
                intent_scores[intent] = min(score / len(keywords), 1.0)

        if not intent_scores:
            return IntentResult(
                primary_intent=Intent.UNKNOWN,
                confidence=0.5,
                reasoning="No keywords matched"
            )

        # 排序并选择最高分
        sorted_intents = sorted(
            intent_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        primary, confidence = sorted_intents[0]
        all_intents = sorted_intents[:3]  # 取前3个

        return IntentResult(
            primary_intent=primary,
            confidence=confidence,
            all_intents=all_intents,
            suggested_agents=self._intent_agent_map.get(primary, []),
            reasoning=f"Keyword matched: {primary.value}"
        )

    async def _llm_classify(self, query: str) -> IntentResult:
        """LLM分类"""
        prompt = f"""分析以下用户查询的意图:

查询: "{query}"

意图类型:
- literature_search: 搜索论文
- literature_review: 文献综述
- topic_select: 选题
- thesis_formulate: Thesis凝练
- outline_generate: 大纲生成
- draft_write: 初稿撰写
- full_paper: 完整论文流程
- diagnostic: 诊断
- question: 问答
- comparison: 对比

请返回JSON格式:
{{"intent": "主要意图", "confidence": 0.0-1.0, "reasoning": "理由"}}
"""

        response = await self.llm_provider(prompt)

        try:
            import json
            data = json.loads(response)

            intent_str = data.get("intent", "unknown")
            confidence = float(data.get("confidence", 0.5))

            # 转换字符串到Intent枚举
            intent = Intent(intent_str) if intent_str in [e.value for e in Intent] else Intent.UNKNOWN

            return IntentResult(
                primary_intent=intent,
                confidence=confidence,
                all_intents=[(intent, confidence)],
                suggested_agents=self._intent_agent_map.get(intent, []),
                reasoning=data.get("reasoning", "")
            )
        except Exception:
            return IntentResult(
                primary_intent=Intent.UNKNOWN,
                confidence=0.5,
                reasoning="LLM parsing failed"
            )

    def _merge_results(
        self,
        keyword_result: IntentResult,
        llm_result: IntentResult
    ) -> IntentResult:
        """融合关键词和LLM结果"""
        # 如果LLM置信度高，使用LLM结果
        if llm_result.confidence > 0.8:
            return llm_result

        # 如果关键词置信度高，使用关键词结果
        if keyword_result.confidence > 0.7:
            return keyword_result

        # 融合：取置信度的加权平均
        keyword_weight = 0.3
        llm_weight = 0.7

        merged_confidence = (
            keyword_result.confidence * keyword_weight +
            llm_result.confidence * llm_weight
        )

        # 如果意图不同，选择置信度高的
        if keyword_result.primary_intent != llm_result.primary_intent:
            if keyword_result.confidence > llm_result.confidence:
                return keyword_result
            else:
                return llm_result

        return IntentResult(
            primary_intent=llm_result.primary_intent,
            confidence=merged_confidence,
            all_intents=llm_result.all_intents,
            suggested_agents=llm_result.suggested_agents,
            reasoning=f"Keyword: {keyword_result.reasoning}, LLM: {llm_result.reasoning}"
        )

    def detect_multi_intent(self, query: str) -> List[IntentResult]:
        """检测多意图

        Args:
            query: 用户查询

        Returns:
            List[IntentResult]: 多个意图结果
        """
        # 分解查询为句子
        sentences = query.replace("。", "|").replace("?", "|").replace("！", "|").split("|")

        results = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                result = self._keyword_match(sentence)
                results.append(result)

        return results

    def get_suggested_agents(self, intent: Intent) -> List[str]:
        """获取建议的Agent列表"""
        return self._intent_agent_map.get(intent, [])


# 便捷函数
async def classify_intent(query: str) -> IntentResult:
    """便捷意图分类函数"""
    classifier = LLMIntentClassifier()
    return await classifier.classify(query)
