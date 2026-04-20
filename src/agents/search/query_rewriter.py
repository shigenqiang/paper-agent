"""查询重写Agent"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from src.core.model import llm

logger = logging.getLogger(__name__)


class QueryRewrite(BaseModel):
    """查询重写结果"""
    original_query: str = Field(..., description="原始查询")
    rewritten_queries: List[str] = Field(default_factory=list, description="重写后的查询列表")
    rewrite_strategies: List[str] = Field(default_factory=list, description="使用的重写策略")
    improvements: List[str] = Field(default_factory=list, description="改进说明")
    best_query: Optional[str] = Field(default=None, description="最佳查询")
    best_strategy: Optional[str] = Field(default=None, description="最佳策略")


class QueryRewriterAgent:
    """查询重写Agent - 多维查询重写"""

    def __init__(
        self,
        domain: str = "general",
        max_rewrites: int = 5,
        use_llm: bool = True
    ):
        """
        Args:
            domain: 领域
            max_rewrites: 最大重写数量
            use_llm: 是否使用LLM
        """
        self.domain = domain
        self.max_rewrites = max_rewrites
        self.use_llm = use_llm

    async def rewrite(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryRewrite:
        """
        重写查询

        Args:
            query: 原始查询
            context: 上下文信息

        Returns:
            查询重写结果
        """
        # 使用多种策略重写查询
        rewrites = []

        # 策略1: 同义词替换
        synonym_rewrites = self._rewrite_with_synonyms(query)
        rewrites.extend(synonym_rewrites)

        # 策略2: 扩展查询
        expanded_rewrites = await self._rewrite_with_expansion(query)
        rewrites.extend(expanded_rewrites)

        # 策略3: 转换为学术表达
        academic_rewrites = await self._rewrite_to_academic(query)
        rewrites.extend(academic_rewrites)

        # 策略4: 添加限定词
        qualified_rewrites = await self._rewrite_with_qualifiers(query)
        rewrites.extend(qualified_rewrites)

        # 策略5: 多维度重写（LLM）
        if self.use_llm:
            llm_rewrites = await self._rewrite_with_llm(query)
            rewrites.extend(llm_rewrites)

        # 去重并限制数量
        unique_rewrites = list(set(rewrites))[:self.max_rewrites]

        # 识别使用的策略
        strategies = []
        if synonym_rewrites:
            strategies.append("synonym_replacement")
        if expanded_rewrites:
            strategies.append("query_expansion")
        if academic_rewrites:
            strategies.append("academic_translation")
        if qualified_rewrites:
            strategies.append("qualification")
        if llm_rewrites:
            strategies.append("llm_rewriting")

        # 生成改进说明
        improvements = self._generate_improvements(query, unique_rewrites)

        # 选择最佳查询
        best_query, best_strategy = await self._select_best_query(
            query,
            unique_rewrites,
            strategies
        )

        return QueryRewrite(
            original_query=query,
            rewritten_queries=unique_rewrites,
            rewrite_strategies=strategies,
            improvements=improvements,
            best_query=best_query,
            best_strategy=best_strategy
        )

    def _rewrite_with_synonyms(self, query: str) -> List[str]:
        """使用同义词替换重写查询"""
        # 预定义的同义词映射
        synonym_map = {
            "机器学习": ["人工智能", "AI技术", "ML"],
            "深度学习": ["神经网络", "深度神经网络", "DL"],
            "自然语言处理": ["NLP", "文本处理", "语言理解"],
            "计算机视觉": ["CV", "图像识别", "视觉感知"],
            "数据挖掘": ["知识发现", "数据分析", "数据科学"],
            "函数型数据": ["功能数据", "FDA", "曲线数据"],
        }

        rewrites = []

        for term, synonyms in synonym_map.items():
            if term.lower() in query.lower():
                for synonym in synonyms:
                    rewrites.append(
                        query.lower().replace(term.lower(), synonym)
                    )

        return rewrites

    async def _rewrite_with_expansion(self, query: str) -> List[str]:
        """扩展查询"""
        if not self.use_llm:
            return []

        prompt = f"""请对以下查询进行扩展，添加相关的关键词和概念，生成2-3个扩展后的查询：

原始查询: {query}

请以JSON格式返回，格式如下:
{{
  "expanded_queries": [
    "扩展查询1",
    "扩展查询2"
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
                return data.get("expanded_queries", [])

        except Exception as e:
            logger.warning(f"Failed to expand query: {e}")

        return []

    async def _rewrite_to_academic(self, query: str) -> List[str]:
        """转换为学术表达"""
        if not self.use_llm:
            return []

        prompt = f"""请将以下查询转换为更学术、更专业的表达，生成1-2个学术查询：

原始查询: {query}

请以JSON格式返回，格式如下:
{{
  "academic_queries": [
    "学术查询1",
    "学术查询2"
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
                return data.get("academic_queries", [])

        except Exception as e:
            logger.warning(f"Failed to rewrite to academic: {e}")

        return []

    async def _rewrite_with_qualifiers(self, query: str) -> List[str]:
        """添加限定词"""
        if not self.use_llm:
            return []

        prompt = f"""请为以下查询添加适当的限定词（如时间范围、领域、方法等），生成1-2个限定后的查询：

原始查询: {query}

请以JSON格式返回，格式如下:
{{
  "qualified_queries": [
    "限定查询1",
    "限定查询2"
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
                return data.get("qualified_queries", [])

        except Exception as e:
            logger.warning(f"Failed to add qualifiers: {e}")

        return []

    async def _rewrite_with_llm(self, query: str) -> List[str]:
        """使用LLM进行多维度重写"""
        if not self.use_llm:
            return []

        prompt = f"""请从多个维度重写以下查询，生成2-3个不同角度的查询：

维度建议：
1. 不同的表达方式
2. 不同的侧重点
3. 不同的技术视角

原始查询: {query}

请以JSON格式返回，格式如下:
{{
  "rewritten_queries": [
    "重写查询1",
    "重写查询2",
    "重写查询3"
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
                return data.get("rewritten_queries", [])

        except Exception as e:
            logger.warning(f"Failed to rewrite with LLM: {e}")

        return []

    def _generate_improvements(
        self,
        original: str,
        rewrites: List[str]
    ) -> List[str]:
        """生成改进说明"""
        improvements = []

        if not rewrites:
            return improvements

        # 检查是否有同义词替换
        if any(original.lower() not in r.lower() for r in rewrites):
            improvements.append("使用了同义词替换，扩大了检索范围")

        # 检查是否有查询扩展
        if any(len(r) > len(original) for r in rewrites):
            improvements.append("扩展了查询关键词，提高了召回率")

        # 检查是否有学术表达
        improvements.append("转换为学术表达，提高了专业性")

        # 检查是否有多个维度
        if len(rewrites) > 3:
            improvements.append(f"生成了{len(rewrites)}个不同角度的查询")

        return improvements

    async def _select_best_query(
        self,
        original: str,
        rewrites: List[str],
        strategies: List[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """选择最佳查询"""
        if not rewrites:
            return None, None

        if not self.use_llm:
            # 简单策略：选择最长的
            best = max(rewrites, key=len)
            best_strategy = "longest"
            return best, best_strategy

        prompt = f"""请从以下重写后的查询中选择最适合学术检索的一个：

原始查询: {original}

重写查询:
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(rewrites)])}

请返回最佳查询的序号和原因，格式如下:
{{
  "best_index": 0,
  "reason": "选择原因"
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
                best_index = data.get("best_index", 0)

                if 0 <= best_index < len(rewrites):
                    best_strategy = strategies[best_index] if best_index < len(strategies) else "llm_rewriting"
                    return rewrites[best_index], best_strategy

        except Exception as e:
            logger.warning(f"Failed to select best query: {e}")

        # 降级：选择第一个
        return rewrites[0], strategies[0] if strategies else "default"


class QueryOptimizer:
    """查询优化器 - 优化查询的质量和检索效果"""

    def __init__(self):
        self.rewrite_agent = QueryRewriterAgent()
        self.clarifier_agent = None

    def set_clarifier(self, clarifier):
        """设置查询澄清器"""
        self.clarifier_agent = clarifier

    async def optimize(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        优化查询

        Args:
            query: 原始查询
            context: 上下文信息

        Returns:
            优化结果
        """
        # 步骤1: 澄清查询
        if self.clarifier_agent:
            clarification = await self.clarifier_agent.clarify(query, context)
            clarified_query = clarification.clarified_query
        else:
            clarified_query = query

        # 步骤2: 重写查询
        rewrite_result = await self.rewrite_agent.rewrite(clarified_query, context)

        return {
            "original_query": query,
            "clarified_query": clarified_query,
            "rewritten_queries": rewrite_result.rewritten_queries,
            "best_query": rewrite_result.best_query,
            "strategies_used": rewrite_result.rewrite_strategies,
            "improvements": rewrite_result.improvements
        }

    async def batch_optimize(
        self,
        queries: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """批量优化查询"""
        results = []

        for query in queries:
            result = await self.optimize(query, context)
            results.append(result)

        return results
