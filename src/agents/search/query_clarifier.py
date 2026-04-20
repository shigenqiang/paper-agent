"""查询澄清Agent"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.core.model import llm

logger = logging.getLogger(__name__)


class QueryClarification(BaseModel):
    """查询澄清结果"""
    original_query: str = Field(..., description="原始查询")
    clarified_query: str = Field(..., description="澄清后的查询")
    identified_terms: List[str] = Field(default_factory=list, description="识别的术语")
    mapped_terms: Dict[str, str] = Field(default_factory=dict, description="术语映射")
    ambiguities: List[str] = Field(default_factory=list, description="识别的歧义")
    suggestions: List[str] = Field(default_factory=list, description="澄清建议")
    confidence: float = Field(default=0.0, description="澄清置信度")


class TermMapping(BaseModel):
    """术语映射"""
    colloquial_term: str
    academic_term: str
    domain: str
    confidence: float


class QueryClarifierAgent:
    """查询澄清Agent - 处理口语化表达和术语映射"""

    def __init__(
        self,
        domain: str = "general",
        use_llm: bool = True,
        confidence_threshold: float = 0.7
    ):
        """
        Args:
            domain: 领域
            use_llm: 是否使用LLM
            confidence_threshold: 置信度阈值
        """
        self.domain = domain
        self.use_llm = use_llm
        self.confidence_threshold = confidence_threshold

        # 加载术语映射
        self.term_mappings = self._load_term_mappings()

    def _load_term_mappings(self) -> Dict[str, List[TermMapping]]:
        """加载术语映射"""
        # 预定义的术语映射
        mappings = {
            "academic": [
                TermMapping(
                    colloquial_term="深度学习",
                    academic_term="Deep Learning",
                    domain="机器学习",
                    confidence=0.95
                ),
                TermMapping(
                    colloquial_term="机器学习",
                    academic_term="Machine Learning",
                    domain="人工智能",
                    confidence=0.95
                ),
                TermMapping(
                    colloquial_term="神经网络",
                    academic_term="Neural Networks",
                    domain="深度学习",
                    confidence=0.90
                ),
                TermMapping(
                    colloquial_term="大模型",
                    academic_term="Large Language Models",
                    domain="自然语言处理",
                    confidence=0.90
                ),
                TermMapping(
                    colloquial_term="函数型数据",
                    academic_term="Functional Data Analysis",
                    domain="统计学",
                    confidence=0.95
                ),
                TermMapping(
                    colloquial_term="时间序列",
                    academic_term="Time Series Analysis",
                    domain="统计学",
                    confidence=0.90
                ),
            ],
            "medical": [
                TermMapping(
                    colloquial_term="癌症",
                    academic_term="Cancer",
                    domain="肿瘤学",
                    confidence=0.95
                ),
                TermMapping(
                    colloquial_term="心脏病",
                    academic_term="Cardiovascular Disease",
                    domain="心脏病学",
                    confidence=0.90
                ),
            ],
            "general": []
        }

        # 添加通用映射
        mappings["general"] = [
            TermMapping(
                colloquial_term="AI",
                academic_term="Artificial Intelligence",
                domain="计算机科学",
                confidence=0.95
            ),
            TermMapping(
                colloquial_term="AI技术",
                academic_term="Artificial Intelligence Techniques",
                domain="计算机科学",
                confidence=0.90
            ),
        ]

        # 合并领域特定的映射和通用映射
        domain_mappings = mappings.get(self.domain, [])
        general_mappings = mappings.get("general", [])

        return {
            "domain": domain_mappings,
            "general": general_mappings
        }

    async def clarify(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryClarification:
        """
        澄清查询

        Args:
            query: 用户查询
            context: 上下文信息

        Returns:
            查询澄清结果
        """
        # 识别术语
        identified_terms = self._identify_terms(query)

        # 映射术语
        mapped_terms = self._map_terms(identified_terms)

        # 识别歧义
        ambiguities = await self._identify_ambiguities(query, mapped_terms)

        # 生成建议
        suggestions = await self._generate_suggestions(query, identified_terms, ambiguities)

        # 构建澄清后的查询
        clarified_query = self._build_clarified_query(query, mapped_terms)

        # 计算置信度
        confidence = self._calculate_confidence(
            identified_terms,
            mapped_terms,
            ambiguities
        )

        return QueryClarification(
            original_query=query,
            clarified_query=clarified_query,
            identified_terms=identified_terms,
            mapped_terms=mapped_terms,
            ambiguities=ambiguities,
            suggestions=suggestions,
            confidence=confidence
        )

    def _identify_terms(self, query: str) -> List[str]:
        """识别查询中的术语"""
        terms = []

        # 获取所有术语
        all_mappings = (
            self.term_mappings.get("domain", []) +
            self.term_mappings.get("general", [])
        )

        # 查找匹配的术语
        for mapping in all_mappings:
            if mapping.colloquial_term.lower() in query.lower():
                terms.append(mapping.colloquial_term)

        return list(set(terms))  # 去重

    def _map_terms(self, terms: List[str]) -> Dict[str, str]:
        """映射术语到学术表达"""
        mapped = {}

        all_mappings = (
            self.term_mappings.get("domain", []) +
            self.term_mappings.get("general", [])
        )

        for term in terms:
            for mapping in all_mappings:
                if mapping.colloquial_term.lower() == term.lower():
                    mapped[term] = mapping.academic_term
                    break

        return mapped

    async def _identify_ambiguities(
        self,
        query: str,
        mapped_terms: Dict[str, str]
    ) -> List[str]:
        """识别查询中的歧义"""
        if not self.use_llm:
            return []

        prompt = f"""请分析以下查询中可能存在的歧义或不明确的表达：

查询: {query}

已识别的术语映射: {mapped_terms}

请列出查询中可能存在的歧义，例如：
1. 范围不明确（时间、领域等）
2. 术语的多义性
3. 缺乏上下文的信息

请以JSON格式返回，格式如下:
{{
  "ambiguities": [
    "歧义描述1",
    "歧义描述2"
  ]
}}
"""

        try:
            response = await llm.ainvoke({"messages": prompt})
            content = response["messages"][-1].content

            import re
            import json
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("ambiguities", [])

        except Exception as e:
            logger.warning(f"Failed to identify ambiguities: {e}")

        return []

    async def _generate_suggestions(
        self,
        query: str,
        identified_terms: List[str],
        ambiguities: List[str]
    ) -> List[str]:
        """生成澄清建议"""
        suggestions = []

        # 基于术语映射的建议
        for term in identified_terms:
            if term not in self._map_terms(identified_terms):
                suggestions.append(f"请澄清术语 '{term}' 的具体含义")

        # 基于歧义的建议
        suggestions.extend([
            f"请明确: {ambiguity}"
            for ambiguity in ambiguities
        ])

        return suggestions

    def _build_clarified_query(
        self,
        query: str,
        mapped_terms: Dict[str, str]
    ) -> str:
        """构建澄清后的查询"""
        clarified = query

        # 替换术语
        for colloquial, academic in mapped_terms.items():
            clarified = clarified.replace(colloquial, academic)

        return clarified

    def _calculate_confidence(
        self,
        identified_terms: List[str],
        mapped_terms: Dict[str, str],
        ambiguities: List[str]
    ) -> float:
        """计算澄清置信度"""
        if not identified_terms:
            return 0.5

        # 术语映射率
        mapping_rate = len(mapped_terms) / len(identified_terms)

        # 歧义惩罚
        ambiguity_penalty = len(ambiguities) * 0.1

        # 计算置信度
        confidence = mapping_rate - ambiguity_penalty

        return max(0.0, min(1.0, confidence))

    def add_term_mapping(
        self,
        colloquial_term: str,
        academic_term: str,
        domain: str,
        confidence: float = 0.8
    ):
        """添加术语映射"""
        mapping = TermMapping(
            colloquial_term=colloquial_term,
            academic_term=academic_term,
            domain=domain,
            confidence=confidence
        )

        if domain == self.domain:
            self.term_mappings["domain"].append(mapping)
        else:
            self.term_mappings["general"].append(mapping)

        logger.info(f"Added term mapping: {colloquial_term} -> {academic_term}")

    def get_term_mappings(self) -> List[Dict[str, Any]]:
        """获取所有术语映射"""
        mappings = []

        for category in ["domain", "general"]:
            for mapping in self.term_mappings.get(category, []):
                mappings.append({
                    "colloquial_term": mapping.colloquial_term,
                    "academic_term": mapping.academic_term,
                    "domain": mapping.domain,
                    "confidence": mapping.confidence
                })

        return mappings


class QueryDisambiguator:
    """查询消歧器 - 处理多义词和模糊查询"""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm

    async def disambiguate(
        self,
        query: str,
        candidates: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        消歧查询

        Args:
            query: 模糊查询
            candidates: 候选解释列表

        Returns:
            消歧结果
        """
        if candidates is None:
            candidates = await self._generate_candidates(query)

        # 评估每个候选
        evaluated = []
        for candidate in candidates:
            score = await self._evaluate_candidate(query, candidate)
            evaluated.append({
                "candidate": candidate,
                "score": score,
                "explanation": await self._explain_choice(query, candidate)
            })

        # 按分数排序
        evaluated.sort(key=lambda x: x["score"], reverse=True)

        return {
            "original_query": query,
            "candidates": evaluated,
            "best_match": evaluated[0] if evaluated else None
        }

    async def _generate_candidates(self, query: str) -> List[str]:
        """生成候选解释"""
        if not self.use_llm:
            return []

        prompt = f"""对于以下模糊查询，请生成3-5个可能的解释候选：

查询: {query}

请以JSON格式返回，格式如下:
{{
  "candidates": [
    "候选解释1",
    "候选解释2"
  ]
}}
"""

        try:
            response = await llm.ainvoke({"messages": prompt})
            content = response["messages"][-1].content

            import re
            import json
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("candidates", [])

        except Exception as e:
            logger.warning(f"Failed to generate candidates: {e}")

        return []

    async def _evaluate_candidate(
        self,
        query: str,
        candidate: str
    ) -> float:
        """评估候选解释的合适度"""
        if not self.use_llm:
            return 0.5

        prompt = f"""请评估候选解释与查询的匹配程度，给出0-1之间的分数：

查询: {query}
候选解释: {candidate}

请直接返回数字分数（0-1之间），不要其他内容。
"""

        try:
            response = await llm.ainvoke({"messages": prompt})
            content = response["messages"][-1].content.strip()

            import re
            score_match = re.search(r'0\.\d+|1\.0|0|1', content)
            if score_match:
                return float(score_match.group())

        except Exception as e:
            logger.warning(f"Failed to evaluate candidate: {e}")

        return 0.5

    async def _explain_choice(
        self,
        query: str,
        candidate: str
    ) -> str:
        """解释选择原因"""
        if not self.use_llm:
            return ""

        prompt = f"""请简要解释为什么这个候选解释适合该查询：

查询: {query}
候选解释: {candidate}

请用1-2句话解释。
"""

        try:
            response = await llm.ainvoke({"messages": prompt})
            return response["messages"][-1].content.strip()

        except Exception as e:
            logger.warning(f"Failed to explain choice: {e}")

            return ""
