"""
IntentRouter - 意图路由Agent

根据用户请求自动识别意图，并路由到最合适的Agent或Agent组合

设计原则（来自Agent开发最佳实践）：
1. 简单性优先 - 不使用复杂框架，直接简单路由
2. 清晰的能力定义 - 每个路由目标都有明确的职责
3. 可组合性 - 支持多Agent协作处理复杂请求
"""
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import logging
import json

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """意图类型枚举"""
    # 文献相关
    LITERATURE_SEARCH = "literature_search"      # 搜索论文
    LITERATURE_REVIEW = "literature_review"      # 文献综述
    LITERATURE_TRACKING = "literature_tracking"  # 文献追踪
    LITERATURE_SUMMARY = "literature_summary"     # 论文总结对比

    # 论文写作相关
    TOPIC_SELECT = "topic_select"                # 选题
    THESIS_FORMULATE = "thesis_formulate"        # Thesis凝练
    OUTLINE_GENERATE = "outline_generate"       # 大纲生成
    DRAFT_WRITE = "draft_write"                 # 初稿撰写
    REPORT_REFINE = "report_refine"              # 报告精炼
    PAPER_REVISION = "paper_revision"            # 智能改稿

    # 开题相关
    PROPOSAL_GENERATE = "proposal_generate"       # 开题报告

    # 完善相关
    LANGUAGE_POLISH = "language_polish"           # 语言润色
    REFERENCE_FORMAT = "reference_format"        # 参考文献处理

    # Pipeline
    FULL_PAPER = "full_paper"                    # 完整论文流程
    DIAGNOSTIC = "diagnostic"                    # 诊断

    # 未知
    UNKNOWN = "unknown"


class IntentConfidence(str, Enum):
    """意图置信度等级"""
    HIGH = "high"      # >= 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # < 0.5


@dataclass
class IntentResult:
    """意图识别结果（含置信度和多意图支持）"""
    primary_intent: IntentType
    confidence: float
    confidence_level: IntentConfidence
    is_multi_intent: bool = False
    secondary_intents: List[IntentType] = field(default_factory=list)
    intent_conflicts: List[str] = field(default_factory=list)
    reasoning: str = ""
    keywords_matched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_intent": self.primary_intent.value,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "is_multi_intent": self.is_multi_intent,
            "secondary_intents": [i.value for i in self.secondary_intents],
            "intent_conflicts": self.intent_conflicts,
            "reasoning": self.reasoning,
            "keywords_matched": self.keywords_matched
        }


# 意图关键词映射
INTENT_KEYWORDS = {
    IntentType.LITERATURE_SEARCH: [
        "搜索论文", "找论文", "查文献", "搜索文献", "找相关文章",
        "search paper", "find papers", "search literature"
    ],
    IntentType.LITERATURE_REVIEW: [
        "文献综述", "综述", "literature review", "survey",
        "总结文献", "整理文献"
    ],
    IntentType.LITERATURE_TRACKING: [
        "追踪", "最新论文", "近期论文", "新发表", "最新进展",
        "track", "latest papers", "recent work"
    ],
    IntentType.LITERATURE_SUMMARY: [
        "对比", "比较", "优缺点", "总结", "compare", "pros cons",
        "分析", "各论文"
    ],
    IntentType.TOPIC_SELECT: [
        "选题", "选主题", "研究方向", "topic selection",
        "研究主题", "确定题目"
    ],
    IntentType.THESIS_FORMULATE: [
        "研究凝练", "thesis", "研究陈述", "研究观点",
        "研究动机", "研究目标"
    ],
    IntentType.OUTLINE_GENERATE: [
        "大纲", "结构设计", "章节规划", "outline",
        "生成大纲", "写大纲"
    ],
    IntentType.DRAFT_WRITE: [
        "撰写", "写作", "初稿", "write", "draft",
        "生成初稿", "撰写内容"
    ],
    IntentType.REPORT_REFINE: [
        "精炼", "优化", "改进", "refine", "improve",
        "完善", "修改稿"
    ],
    IntentType.PAPER_REVISION: [
        "改稿", "修改", "revision", "导师意见", "reviewer comments",
        "审稿意见", "revision"
    ],
    IntentType.PROPOSAL_GENERATE: [
        "开题报告", "任务书", "proposal",
        "开题", "课题申报"
    ],
    IntentType.LANGUAGE_POLISH: [
        "润色", "语言优化", "语法检查", "polish",
        "语言润色", "表达优化"
    ],
    IntentType.REFERENCE_FORMAT: [
        "引用", "参考文献", "citation", "reference",
        "格式化引用", "引用格式"
    ],
    IntentType.FULL_PAPER: [
        "完整论文", "写论文", "全流程", "full paper",
        "生成论文", "论文写作"
    ],
    IntentType.DIAGNOSTIC: [
        "诊断", "问题诊断", "diagnostic",
        "检查问题", "分析问题"
    ]
}


class IntentRouter:
    """
    IntentRouter - 意图路由

    根据用户请求的语义识别意图，并返回：
    1. 识别的意图类型
    2. 建议的Agent名称
    3. 处理模式（单个/协作/Pipeline）
    4. 输入数据格式化建议
    """

    def __init__(self, llm_config: Optional[Any] = None):
        self.llm_config = llm_config
        self._llm = None
        self._init_llm()

        # 意图到Agent的映射 (使用MasterSupervisor中的注册键名)
        self.intent_agent_map = {
            IntentType.LITERATURE_SEARCH: "literature",
            IntentType.LITERATURE_REVIEW: "literature_review",
            IntentType.LITERATURE_TRACKING: "literature_review",
            IntentType.LITERATURE_SUMMARY: "literature_review",
            IntentType.TOPIC_SELECT: "topic",
            IntentType.THESIS_FORMULATE: "thesis",
            IntentType.OUTLINE_GENERATE: "outline_generator",
            IntentType.DRAFT_WRITE: "draft_generator",
            IntentType.REPORT_REFINE: "report_refiner",
            IntentType.PAPER_REVISION: "smart_reviser",
            IntentType.PROPOSAL_GENERATE: "proposal_generator",
            IntentType.LANGUAGE_POLISH: "language_polisher_writing",
            IntentType.REFERENCE_FORMAT: "reference_processor",
            IntentType.FULL_PAPER: "full_pipeline",
            IntentType.DIAGNOSTIC: "diagnostic_phase"
        }

        # 复杂意图需要的多Agent协作 (使用MasterSupervisor中的注册键名)
        self.intent_collaboration_map = {
            IntentType.FULL_PAPER: ["topic", "literature", "thesis", "outline_generator", "draft_generator"],
            IntentType.DIAGNOSTIC: ["topic_refiner", "literature_mapper", "methodology_advisor"]
        }

        logger.info("IntentRouter initialized")

    def _calibrate_confidence(
        self,
        base_confidence: float,
        keyword_match: bool,
        llm_match: bool
    ) -> float:
        """置信度校准

        根据多种信号对置信度进行校准：
        - 关键词匹配：+0.1
        - LLM匹配：+0.0（无调整）
        - 两者都匹配：+0.15
        - 两者都不匹配：-0.2
        """
        calibrated = base_confidence

        if keyword_match and llm_match:
            calibrated += 0.15
        elif keyword_match:
            calibrated += 0.1
        elif not keyword_match and not llm_match:
            calibrated -= 0.2

        return max(0.0, min(1.0, calibrated))

    def _get_confidence_level(self, confidence: float) -> IntentConfidence:
        """获取置信度等级"""
        if confidence >= 0.8:
            return IntentConfidence.HIGH
        elif confidence >= 0.5:
            return IntentConfidence.MEDIUM
        else:
            return IntentConfidence.LOW

    def _detect_intent_conflicts(
        self,
        primary: IntentType,
        secondary: List[IntentType]
    ) -> List[str]:
        """检测意图冲突

        检测同时出现的意图之间是否有冲突：
        - literature_search + topic_select: 可能有冲突（搜索 vs 选题）
        - draft_write + literature_review: 可能有冲突（写作 vs 综述）
        """
        conflicts = []

        conflict_pairs = [
            (IntentType.LITERATURE_SEARCH, IntentType.TOPIC_SELECT),
            (IntentType.LITERATURE_SEARCH, IntentType.OUTLINE_GENERATE),
            (IntentType.DRAFT_WRITE, IntentType.LANGUAGE_POLISH),
        ]

        for sec in secondary:
            for cp in conflict_pairs:
                if (primary == cp[0] and sec == cp[1]) or \
                   (primary == cp[1] and sec == cp[0]):
                    conflicts.append(f"{primary.value} <-> {sec.value}")

        return conflicts

    def _init_llm(self):
        """初始化LLM"""
        try:
            from langchain_openai import ChatOpenAI

            model_name = "gpt-4"
            temperature = 0.3

            if self.llm_config:
                model_name = getattr(self.llm_config, 'model_name', model_name)
                temperature = getattr(self.llm_config, 'temperature', temperature)

            self._llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=2048
            )
            logger.info(f"IntentRouter LLM initialized: {model_name}")
        except Exception as e:
            logger.warning(f"IntentRouter LLM init failed: {e}")

    async def route(self, user_request: str) -> Dict[str, Any]:
        """
        路由用户请求（增强版：支持多意图检测和置信度校准）

        Args:
            user_request: 用户请求文本

        Returns:
            路由结果，包含：
            - intent: 识别的意图类型
            - confidence: 置信度
            - confidence_level: 置信度等级
            - is_multi_intent: 是否多意图
            - secondary_intents: 次要意图列表
            - intent_conflicts: 意图冲突列表
            - suggested_agents: 建议的Agent列表
            - mode: 处理模式 (single/collaboration/pipeline)
            - input_format: 建议的输入格式化
            - reasoning: 路由推理过程
        """
        # 1. 关键词匹配（快速路径）+ 记录匹配词
        keyword_matches = self._match_keywords_with_detail(user_request)

        # 2. LLM辅助识别（复杂情况）+ 多意图检测
        llm_result = await self._llm_multi_intent_route(user_request)

        # 3. 合并结果，确定主意图和次要意图
        all_intents = set()

        # 关键词匹配的意图
        if keyword_matches:
            all_intents.add(keyword_matches[0]["intent"])

        # LLM识别出的意图
        if llm_result["intents"]:
            for intent_data in llm_result["intents"]:
                try:
                    all_intents.add(IntentType(intent_data["intent"]))
                except ValueError:
                    pass

        # 按优先级排序（FULL_PAPER > DIAGNOSTIC > 其他）
        intent_priority = {
            IntentType.FULL_PAPER: 100,
            IntentType.DIAGNOSTIC: 90,
            IntentType.DRAFT_WRITE: 80,
            IntentType.PROPOSAL_GENERATE: 70,
            IntentType.LITERATURE_SEARCH: 60,
            IntentType.LITERATURE_REVIEW: 60,
            IntentType.TOPIC_SELECT: 50,
            IntentType.OUTLINE_GENERATE: 40,
            IntentType.LANGUAGE_POLISH: 30,
        }

        sorted_intents = sorted(
            all_intents,
            key=lambda x: intent_priority.get(x, 0),
            reverse=True
        )

        if not sorted_intents:
            primary = IntentType.UNKNOWN
            secondaries = []
        else:
            primary = sorted_intents[0]
            secondaries = sorted_intents[1:6]  # 最多5个次要意图

        # 4. 置信度校准
        keyword_match = len(keyword_matches) > 0
        llm_match = len(llm_result["intents"]) > 0

        base_conf = llm_result.get("confidence", 0.5)
        calibrated_conf = self._calibrate_confidence(base_conf, keyword_match, llm_match)

        # 5. 意图冲突检测
        conflicts = self._detect_intent_conflicts(primary, secondaries)

        # 6. 构建IntentResult
        intent_result = IntentResult(
            primary_intent=primary,
            confidence=calibrated_conf,
            confidence_level=self._get_confidence_level(calibrated_conf),
            is_multi_intent=len(sorted_intents) > 1,
            secondary_intents=secondaries,
            intent_conflicts=conflicts,
            reasoning=llm_result.get("reasoning", ""),
            keywords_matched=[m["keyword"] for m in keyword_matches]
        )

        # 7. 获取Agent建议
        agents = self._get_agents_for_intent(primary, secondaries)
        mode = self._determine_mode_enhanced(primary, secondaries)
        input_format = self._suggest_input_format_enhanced(primary, user_request, secondaries)

        return {
            **intent_result.to_dict(),
            "suggested_agents": agents,
            "mode": mode,
            "input_format": input_format,
            "requires_collaboration": len(secondaries) > 1 or primary in self.intent_collaboration_map
        }

    def _match_keywords_with_detail(self, text: str) -> List[Dict[str, Any]]:
        """关键词匹配，返回匹配详情"""
        text_lower = text.lower()
        matches = []

        for intent_type, keywords in INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matches.append({
                        "intent": intent_type,
                        "keyword": keyword,
                        "position": text_lower.find(keyword.lower())
                    })
                    break  # 每个意图只取第一个匹配

        return matches

    async def _llm_multi_intent_route(self, user_request: str) -> Dict[str, Any]:
        """LLM多意图识别"""
        if not self._llm:
            return {"intents": [], "confidence": 0.5, "reasoning": "LLM not available"}

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            prompt = f"""
分析以下用户请求，识别所有可能的意图（可能是多个）：

用户请求：{user_request}

可选意图类型（每个都可能是一个意图）：
- literature_search: 搜索论文/文献
- literature_review: 文献综述
- literature_tracking: 文献追踪（最新论文）
- literature_summary: 论文对比总结
- topic_select: 选题
- thesis_formulate: Thesis凝练
- outline_generate: 大纲生成
- draft_write: 初稿撰写
- report_refine: 报告精炼
- paper_revision: 智能改稿（根据导师意见）
- proposal_generate: 开题报告
- language_polish: 语言润色
- reference_format: 参考文献处理
- full_paper: 完整论文流程
- diagnostic: 诊断

请输出JSON格式（注意：intents是一个数组）：
{{"intents": [
    {{"intent": "意图类型1", "confidence": 0.0-1.0}},
    {{"intent": "意图类型2", "confidence": 0.0-1.0}}
], "reasoning": "综合识别理由"}}
"""
            messages = [
                SystemMessage(content="你是一个意图识别专家，擅长识别多个并存的意图。"),
                HumanMessage(content=prompt)
            ]

            response = await self._llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            data = json.loads(content)
            return {
                "intents": data.get("intents", []),
                "confidence": data.get("confidence", 0.5),
                "reasoning": data.get("reasoning", "")
            }

        except Exception as e:
            logger.error(f"LLM multi-intent routing failed: {e}")
            return {"intents": [], "confidence": 0.5, "reasoning": ""}

    def _get_agents_for_intent(
        self,
        primary: IntentType,
        secondaries: List[IntentType]
    ) -> List[str]:
        """获取处理意图所需的Agent列表"""
        agents = []

        # 主意图的Agent
        primary_agent = self.intent_agent_map.get(primary)
        if primary_agent:
            if isinstance(primary_agent, list):
                agents.extend(primary_agent)
            else:
                agents.append(primary_agent)

        # 检查是否需要协作
        if primary in self.intent_collaboration_map:
            for col_agent in self.intent_collaboration_map[primary]:
                if col_agent not in agents:
                    agents.append(col_agent)

        # 次要意图也需要对应的Agent
        for sec in secondaries:
            sec_agent = self.intent_agent_map.get(sec)
            if sec_agent and sec_agent not in agents:
                if isinstance(sec_agent, list):
                    agents.extend(sec_agent)
                else:
                    agents.append(sec_agent)

        return list(dict.fromkeys(agents))  # 去重保持顺序

    def _determine_mode_enhanced(
        self,
        primary: IntentType,
        secondaries: List[IntentType]
    ) -> str:
        """增强的模式确定（考虑多意图）"""
        # 多意图需要协作模式
        if len(secondaries) > 1:
            return "collaboration"

        # 主意图本身需要协作
        if primary in self.intent_collaboration_map:
            return "collaboration"

        # 全流程需要Pipeline模式
        if primary == IntentType.FULL_PAPER:
            return "pipeline"

        return "single"

    def _suggest_input_format_enhanced(
        self,
        primary: IntentType,
        user_request: str,
        secondaries: List[IntentType]
    ) -> Dict[str, Any]:
        """建议输入格式化（考虑多意图）"""
        base_format = {
            "user_request": user_request,
            "task_type": primary.value,
            "is_multi_intent": len(secondaries) > 0,
            "secondary_intents": [s.value for s in secondaries]
        }

        # 根据不同意图添加特定字段建议
        if primary == IntentType.LITERATURE_TRACKING:
            base_format["mode"] = "tracking"
            base_format["time_range"] = "6months"
        elif primary == IntentType.LITERATURE_SUMMARY:
            base_format["mode"] = "summary"
        elif primary == IntentType.PAPER_REVISION:
            base_format["highlight_changes"] = True

        # 多意图时的特殊处理
        if len(secondaries) > 1:
            base_format["parallel_processing"] = True
            base_format["result_aggregation"] = "merge"

        return base_format

    def _match_keywords(self, text: str) -> IntentType:
        """关键词匹配"""
        text_lower = text.lower()

        for intent_type, keywords in INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return intent_type

        return IntentType.UNKNOWN

    async def _llm_assisted_route(self, user_request: str) -> IntentType:
        """LLM辅助意图识别"""
        if not self._llm:
            return IntentType.UNKNOWN

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            prompt = f"""
分析以下用户请求，识别其核心意图：

用户请求：{user_request}

可选意图类型：
- literature_search: 搜索论文/文献
- literature_review: 文献综述
- literature_tracking: 文献追踪（最新论文）
- literature_summary: 论文对比总结
- topic_select: 选题
- thesis_formulate: Thesis凝练
- outline_generate: 大纲生成
- draft_write: 初稿撰写
- report_refine: 报告精炼
- paper_revision: 智能改稿（根据导师意见）
- proposal_generate: 开题报告
- language_polish: 语言润色
- reference_format: 参考文献处理
- full_paper: 完整论文流程
- diagnostic: 诊断
- unknown: 无法识别

请输出JSON格式：
{{"intent": "意图类型", "confidence": 0.0-1.0, "reasoning": "识别理由"}}
"""
            messages = [
                SystemMessage(content="你是一个意图识别专家。"),
                HumanMessage(content=prompt)
            ]

            response = await self._llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            data = json.loads(content)
            intent_str = data.get("intent", "unknown")

            # 验证意图类型有效性
            try:
                return IntentType(intent_str)
            except ValueError:
                return IntentType.UNKNOWN

        except Exception as e:
            logger.error(f"LLM-assisted routing failed: {e}")
            return IntentType.UNKNOWN

    def _determine_mode(self, intent: IntentType) -> str:
        """确定处理模式"""
        if intent in self.intent_collaboration_map:
            return "collaboration"
        elif intent == IntentType.FULL_PAPER:
            return "pipeline"
        else:
            return "single"

    def _suggest_input_format(self, intent: IntentType, user_request: str) -> Dict[str, Any]:
        """建议输入格式化"""
        base_format = {
            "user_request": user_request,
            "task_type": intent.value
        }

        # 根据不同意图添加特定字段建议
        if intent == IntentType.LITERATURE_TRACKING:
            base_format["mode"] = "tracking"
            base_format["time_range"] = "6months"
        elif intent == IntentType.LITERATURE_SUMMARY:
            base_format["mode"] = "summary"
        elif intent == IntentType.PAPER_REVISION:
            base_format["highlight_changes"] = True

        return base_format

    def _get_intent_source(self, keyword_intent: IntentType, llm_intent: IntentType) -> str:
        """获取意图识别来源"""
        if keyword_intent != IntentType.UNKNOWN and llm_intent != IntentType.UNKNOWN:
            return "keyword + LLM"
        elif keyword_intent != IntentType.UNKNOWN:
            return "keyword matching"
        elif llm_intent != IntentType.UNKNOWN:
            return "LLM inference"
        else:
            return "unknown"

    def get_intent_keywords(self) -> Dict[str, List[str]]:
        """获取所有意图类型及其关键词"""
        return {intent.value: keywords for intent, keywords in INTENT_KEYWORDS.items()}
