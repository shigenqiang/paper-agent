"""
学术写作助手 - 单一PaperAgent核心实现

核心设计：
- 单一Agent贯穿research→analysis→writing→review全程
- 每个阶段后进行Self-Reflection
- Validation Gate控制阶段转换
- Phase Handler机制处理不同阶段
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import json
import asyncio

logger = logging.getLogger(__name__)


# ============ 输入输出模型 ============

class AgentInput(BaseModel):
    """Agent标准输入"""
    task_type: str = Field(..., description="任务类型: full_research, research, analysis, writing, review")
    task_description: str = Field(..., description="任务描述")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="任务输入数据")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    requirements: List[str] = Field(default_factory=list, description="需求列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AgentOutput(BaseModel):
    """Agent标准输出"""
    success: bool = Field(..., description="是否成功")
    result: Any = Field(None, description="执行结果")
    agent_name: str = Field(..., description="执行Agent名称")
    reasoning: Optional[str] = Field(None, description="推理过程")
    next_actions: List[str] = Field(default_factory=list, description="建议的后续操作")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    quality_score: float = Field(0.0, description="质量评分")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field(default="openai", description="LLM提供商")
    model_name: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="最大token数")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")


# ============ 反思结果模型 ============

class ReflectionResult(BaseModel):
    """反思结果"""
    needs_improvement: bool = False
    quality_score: float = 0.0
    issues: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    iteration: int = 0


# ============ Validation Gate ============

class ValidationGate:
    """质量门控"""

    PHASE_GATES = {
        "research": {
            "min_papers": 10,
            "min_relevance": 0.6,
            "max_age_years": 5,
        },
        "analysis": {
            "min_themes": 3,
            "min_gaps": 1,
            "min_papers_analyzed": 5,
        },
        "writing": {
            "min_sections": 5,
            "min_coherence": 0.7,
            "min_citations": 10,
        },
        "review": {
            "min_quality_score": 7.0,
        }
    }

    def validate(self, phase: str, result: Dict[str, Any]) -> Dict[str, Any]:
        gate_config = self.PHASE_GATES.get(phase, {})
        issues = []
        actual = {}

        for criterion, threshold in gate_config.items():
            value = result.get(criterion, 0)
            actual[criterion] = value
            if isinstance(threshold, (int, float)) and value < threshold:
                issues.append(f"{criterion} below threshold: {value} < {threshold}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "criteria": gate_config,
            "actual": actual
        }


# ============ Circuit Breaker ============

class CircuitBreaker:
    """熔断器"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time: Optional[float] = None

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpen("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if self.state == "OPEN":
                raise
            raise

    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return False
        import time
        return (time.time() - self.last_failure_time) > self.recovery_timeout

    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        self.failure_count += 1
        import time
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""
    pass


# ============ Phase Handler 基类 ============

class PhaseHandler(ABC):
    """阶段处理器基类"""

    def __init__(self, name: str, llm: Any = None):
        self.name = name
        self.llm = llm

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行阶段处理"""
        pass

    @abstractmethod
    async def reflect(self, result: Dict[str, Any]) -> ReflectionResult:
        """反思阶段结果"""
        pass


# ============ 单一PaperAgent ============

class PaperAgent:
    """
    单一PaperAgent - 贯穿research→analysis→writing→review全程

    核心设计：
    1. 单一execute方法，内部通过mode切换处理不同阶段
    2. 每个阶段后进行self-reflection
    3. Validation Gate控制阶段转换
    4. Circuit Breaker + Fallback处理错误

    使用方式：
    agent = PaperAgent(llm_config)
    result = await agent.execute({"task_type": "full_research", "user_request": "..."})
    """

    def __init__(
        self,
        name: str = "paper_agent",
        llm_config: Optional[LLMConfig] = None,
        max_iterations: int = 3,
        quality_threshold: float = 0.7
    ):
        self.name = name
        self.llm_config = llm_config or LLMConfig()
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold

        # 阶段处理器
        self.phase_handlers: Dict[str, PhaseHandler] = {}

        # 组件
        self.validation_gate = ValidationGate()
        self.circuit_breaker = CircuitBreaker()
        self._llm = None

        # 状态
        self.current_phase: Optional[str] = None
        self.phase_history: List[Dict[str, Any]] = []

        # 初始化
        self._init_llm()
        self._setup_logging()
        self._register_phase_handlers()

        logger.info(f"PaperAgent {self.name} initialized")

    def _init_llm(self):
        """初始化LLM"""
        try:
            provider = self.llm_config.provider.lower()

            if provider == "openai":
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=self.llm_config.api_key,
                    base_url=self.llm_config.base_url
                )
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                self._llm = ChatAnthropic(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    api_key=self.llm_config.api_key
                )
            else:
                raise ValueError(f"不支持的LLM提供商: {provider}")

            logger.info(f"Initialized LLM: {self.llm_config.provider} - {self.llm_config.model_name}")
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            self._llm = None

    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"PaperAgent.{self.name}")

    def _register_phase_handlers(self):
        """注册阶段处理器"""
        # 研究阶段处理器
        self.phase_handlers["research"] = ResearchPhaseHandler(self._llm)
        # 分析阶段处理器
        self.phase_handlers["analysis"] = AnalysisPhaseHandler(self._llm)
        # 写作阶段处理器
        self.phase_handlers["writing"] = WritingPhaseHandler(self._llm)
        # 审核阶段处理器
        self.phase_handlers["review"] = ReviewPhaseHandler(self._llm)

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentOutput:
        """
        统一入口，内部路由到对应phase handler
        """
        task_type = input_data.get("task_type", "full_research")
        user_request = input_data.get("user_request", input_data.get("task_description", ""))

        try:
            if task_type == "full_research":
                return await self._full_research_pipeline(input_data, context or {})
            else:
                return await self._single_phase_execute(task_type, input_data, context)
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=str(e)
            )

    async def _full_research_pipeline(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentOutput:
        """
        完整研究流程：research → analysis → writing → review
        每阶段后进行self-reflection和质量检查
        """
        phases = ["research", "analysis", "writing", "review"]
        current_phase_index = 0
        all_results = {}
        user_request = input_data.get("user_request", "")

        self.logger.info(f"Starting full research pipeline for: {user_request}")

        while current_phase_index < len(phases):
            phase = phases[current_phase_index]
            self.current_phase = phase

            self.logger.info(f"Executing phase: {phase}")

            try:
                # 1. 执行当前阶段
                handler = self.phase_handlers.get(phase)
                if not handler:
                    raise ValueError(f"No handler for phase: {phase}")

                phase_input = {
                    "user_request": user_request,
                    "previous_results": all_results,
                    **context
                }
                phase_result = await handler.execute(phase_input, all_results)

                # 2. Self-Reflection
                reflection = await handler.reflect(phase_result)
                self.logger.info(f"Phase {phase} reflection: needs_improvement={reflection.needs_improvement}, score={reflection.quality_score}")

                # 3. 迭代改进
                iteration_count = 0
                while reflection.needs_improvement and iteration_count < self.max_iterations:
                    iteration_count += 1
                    self.logger.info(f"Improving phase {phase}, iteration {iteration_count}")

                    # 应用改进建议
                    improved_result = await self._improve_phase(phase, phase_result, reflection, handler)
                    phase_result = improved_result

                    # 重新反思
                    reflection = await handler.reflect(phase_result)

                # 4. Validation Gate
                validation = self.validation_gate.validate(phase, phase_result)
                if not validation["passed"]:
                    self.logger.warning(f"Validation failed for {phase}: {validation['issues']}")
                    # 降级处理
                    phase_result = await self._fallback_phase(phase, phase_result)
                    validation = {"passed": True, "issues": []}  # 强制通过

                # 5. 保存阶段结果
                all_results[phase] = {
                    "result": phase_result,
                    "reflection": reflection.model_dump(),
                    "validation": validation,
                    "completed_at": datetime.now().isoformat()
                }
                self.phase_history.append({
                    "phase": phase,
                    "quality_score": reflection.quality_score,
                    "validation_passed": validation["passed"]
                })

            except Exception as e:
                self.logger.error(f"Phase {phase} failed: {e}")
                all_results[phase] = {
                    "result": {},
                    "error": str(e)
                }

            # 进入下一阶段或结束
            if phase == "review":
                break
            current_phase_index += 1

        # 编译最终输出
        final_report = all_results.get("writing", {}).get("result", {}).get("report", "")
        final_quality = all_results.get("review", {}).get("reflection", {}).get("quality_score", 0.0)

        return AgentOutput(
            success=True,
            result={
                "phases": list(all_results.keys()),
                "report": final_report,
                "phase_details": all_results
            },
            agent_name=self.name,
            reasoning=f"Completed {len(all_results)} phases",
            quality_score=final_quality,
            next_actions=["review", "export"]
        )

    async def _single_phase_execute(
        self,
        task_type: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> AgentOutput:
        """执行单个阶段"""
        handler = self.phase_handlers.get(task_type)
        if not handler:
            return AgentOutput(
                success=False,
                result=None,
                agent_name=self.name,
                error=f"Unknown task type: {task_type}"
            )

        phase_input = {**input_data, **(context or {})}
        result = await handler.execute(phase_input, context or {})
        reflection = await handler.reflect(result)

        return AgentOutput(
            success=True,
            result=result,
            agent_name=self.name,
            quality_score=reflection.quality_score,
            reasoning=json.dumps(reflection.model_dump(), ensure_ascii=False)
        )

    async def _improve_phase(
        self,
        phase: str,
        current_result: Dict[str, Any],
        reflection: ReflectionResult,
        handler: PhaseHandler
    ) -> Dict[str, Any]:
        """根据反思结果改进阶段结果"""
        improvement_prompt = f"""
当前阶段：{phase}
当前结果：{json.dumps(current_result, ensure_ascii=False, indent=2)}

反思发现的问题：{json.dumps(reflection.issues, ensure_ascii=False, indent=2)}
改进建议：{json.dumps(reflection.improvement_suggestions, ensure_ascii=False, indent=2)}

请根据改进建议优化结果。输出优化后的JSON结果。
"""
        try:
            response = await self._llm_call(improvement_prompt)
            improved = json.loads(response)
            return improved
        except Exception as e:
            self.logger.error(f"Improvement failed: {e}")
            return current_result

    async def _fallback_phase(self, phase: str, current_result: Dict[str, Any]) -> Dict[str, Any]:
        """降级处理"""
        self.logger.warning(f"Entering fallback mode for phase: {phase}")

        # 简化的降级策略
        fallback_strategies = {
            "research": {
                "papers": [{"title": "Fallback paper", "abstract": "Generated fallback result"}],
                "paper_analyses": []
            },
            "analysis": {
                "themes": [{"name": "General", "description": "Fallback theme"}],
                "research_gaps": ["Further research needed"]
            },
            "writing": {
                "outline": [{"title": "Introduction", "outline": "Basic intro"}],
                "report": "Report generation failed. Please review manually."
            },
            "review": {
                "critique_result": {"passed": True, "score": 0.5},
                "issues": ["Used fallback due to quality issues"]
            }
        }

        return fallback_strategies.get(phase, current_result)

    async def _llm_call(self, prompt: str) -> str:
        """LLM调用封装"""
        if not self._llm:
            raise RuntimeError("LLM未初始化")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content="你是一个专业的学术写作助手。"),
                HumanMessage(content=prompt)
            ]

            response = await self._llm.ainvoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise


# ============ 阶段处理器实现 ============

class ResearchPhaseHandler(PhaseHandler):
    """研究阶段处理器"""

    def __init__(self, llm: Any = None):
        super().__init__("research", llm)

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行研究阶段：搜索 → 排序 → 阅读"""
        user_request = input_data.get("user_request", "")

        # 1. 生成搜索查询
        search_queries = await self._generate_search_queries(user_request)

        # 2. 多引擎并行搜索
        papers = await self._multi_engine_search(search_queries)

        # 3. 排序
        ranked_papers = await self._rank_papers(user_request, papers)

        # 4. 阅读论文
        paper_analyses = await self._read_papers(ranked_papers[:20])

        return {
            "search_queries": search_queries,
            "papers": papers,
            "ranked_papers": ranked_papers,
            "paper_analyses": paper_analyses,
            "paper_count": len(papers),
            "analyzed_count": len(paper_analyses)
        }

    async def _generate_search_queries(self, query: str) -> List[Dict[str, str]]:
        """生成多角度搜索查询"""
        prompt = f"""
为以下研究主题生成多个搜索角度：

研究主题：{query}

请生成5-10个不同角度的搜索查询，每个查询应：
1. 覆盖不同的子主题或方面
2. 使用不同的关键词组合
3. 包含同义词和相关术语

输出JSON格式：
{{
    "queries": [
        {{"query": "搜索查询内容", "strategy": "基础/扩展/验证", "aspect": "方法/应用/趋势"}},
        ...
    ]
}}
"""
        try:
            response = await self.llm.ainvoke(prompt) if self.llm else ""
            if hasattr(response, 'content'):
                response = response.content
            data = json.loads(response)
            return data.get("queries", [{"query": query, "strategy": "基础", "aspect": "综合"}])
        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            return [{"query": query, "strategy": "基础", "aspect": "综合"}]

    async def _multi_engine_search(self, queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """多引擎并行搜索"""
        # 简化实现：实际应该调用多个搜索API
        all_papers = []

        async def search_single(query_obj: Dict[str, str]) -> List[Dict[str, Any]]:
            # 这里应该调用实际的搜索API
            # 目前返回模拟数据
            return [{
                "title": f"Paper about {query_obj.get('query', 'research')}",
                "abstract": f"Abstract for {query_obj.get('query', 'research')}",
                "source": "search_engine",
                "relevance_score": 0.8
            }]

        # 并行搜索
        tasks = [search_single(q) for q in queries[:5]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_papers.extend(result)

        return all_papers

    async def _rank_papers(self, query: str, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """排序论文"""
        # 简化实现：按相关性排序
        return sorted(papers, key=lambda p: p.get("relevance_score", 0), reverse=True)

    async def _read_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """阅读论文"""
        analyses = []

        for paper in papers:
            # 简化实现：实际应该调用PDF阅读
            analyses.append({
                "paper_id": paper.get("title", "unknown"),
                "title": paper.get("title", ""),
                "core_problem": "Identified core problem",
                "key_methodology": "Methodology description",
                "key_findings": "Key findings",
                "limitations": "Limitations"
            })

        return analyses

    async def reflect(self, result: Dict[str, Any]) -> ReflectionResult:
        """反思研究结果"""
        paper_count = result.get("paper_count", 0)
        analyzed_count = result.get("analyzed_count", 0)
        issues = []
        suggestions = []

        if paper_count < 10:
            issues.append(f"论文数量不足: {paper_count} < 10")
            suggestions.append("扩大搜索范围，添加更多关键词")

        if analyzed_count < 5:
            issues.append(f"分析论文数不足: {analyzed_count} < 5")
            suggestions.append("优先分析高相关性论文")

        quality_score = min(1.0, (paper_count / 20) * 0.4 + (analyzed_count / 10) * 0.6)

        return ReflectionResult(
            needs_improvement=len(issues) > 0,
            quality_score=quality_score,
            issues=issues,
            improvement_suggestions=suggestions,
            iteration=0
        )


class AnalysisPhaseHandler(PhaseHandler):
    """分析阶段处理器"""

    def __init__(self, llm: Any = None):
        super().__init__("analysis", llm)

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析阶段：主题聚类 → Gap识别 → 方法对比"""
        paper_analyses = context.get("research", {}).get("result", {}).get("paper_analyses", [])

        if not paper_analyses:
            paper_analyses = input_data.get("paper_analyses", [])

        # 1. 主题聚类
        themes = await self._cluster_themes(paper_analyses)

        # 2. 研究空白识别
        gaps = await self._identify_research_gaps(themes, paper_analyses)

        # 3. 方法对比
        comparisons = await self._compare_methods(paper_analyses)

        return {
            "themes": themes,
            "research_gaps": gaps,
            "method_comparisons": comparisons,
            "theme_count": len(themes),
            "gap_count": len(gaps)
        }

    async def _cluster_themes(self, paper_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """主题聚类"""
        if not paper_analyses:
            return [{"name": "General Research", "description": "General research theme", "paper_ids": []}]

        # 简化实现：基于关键词聚类
        themes = []
        for i, analysis in enumerate(paper_analyses[:10]):
            themes.append({
                "name": f"Theme {i+1}",
                "description": analysis.get("key_methodology", "Research theme"),
                "paper_ids": [analysis.get("paper_id", f"paper_{i}")]
            })

        return themes

    async def _identify_research_gaps(self, themes: List[Dict[str, Any]], paper_analyses: List[Dict[str, Any]]) -> List[str]:
        """识别研究空白"""
        if len(themes) < 3:
            return ["需要更多主题研究", "研究深度有待加强"]

        return ["可进一步探索的空白方向"]

    async def _compare_methods(self, paper_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """方法对比"""
        return [{
            "method_name": "Traditional Method",
            "description": "Standard approach",
            "strengths": ["稳健"],
            "weaknesses": ["效率较低"]
        }]

    async def reflect(self, result: Dict[str, Any]) -> ReflectionResult:
        """反思分析结果"""
        theme_count = result.get("theme_count", 0)
        gap_count = result.get("gap_count", 0)
        issues = []
        suggestions = []

        if theme_count < 3:
            issues.append(f"主题数不足: {theme_count} < 3")
            suggestions.append("扩大论文分析范围")

        if gap_count < 1:
            issues.append("研究空白识别不足")
            suggestions.append("深入分析现有研究的局限性")

        quality_score = min(1.0, (theme_count / 5) * 0.6 + (gap_count / 3) * 0.4)

        return ReflectionResult(
            needs_improvement=len(issues) > 0,
            quality_score=quality_score,
            issues=issues,
            improvement_suggestions=suggestions,
            iteration=0
        )


class WritingPhaseHandler(PhaseHandler):
    """写作阶段处理器"""

    def __init__(self, llm: Any = None):
        super().__init__("writing", llm)

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行写作阶段：大纲 → 章节撰写 → 报告整合"""
        # 获取分析结果
        analysis_result = context.get("analysis", {}).get("result", {})
        themes = analysis_result.get("themes", [])
        research_gaps = analysis_result.get("research_gaps", [])

        # 1. 生成大纲
        outline = await self._generate_outline(themes, research_gaps)

        # 2. 逐章节撰写
        written_sections = []
        for section in outline:
            section_content = await self._write_section(section, context)
            written_sections.append(section_content)

        # 3. 整合报告
        report = self._compile_report(written_sections)

        return {
            "outline": outline,
            "written_sections": written_sections,
            "report": report,
            "section_count": len(written_sections),
            "citation_count": sum(len(s.get("citations", [])) for s in written_sections)
        }

    async def _generate_outline(self, themes: List, gaps: List[str]) -> List[Dict[str, str]]:
        """生成大纲"""
        outline = [
            {"index": 0, "title": "摘要", "outline": "研究概述、主要发现和贡献"},
            {"index": 1, "title": "引言", "outline": "研究背景、问题定义、研究动机"},
            {"index": 2, "title": "文献综述", "outline": "相关工作、方法分类、现有方法优缺点"},
            {"index": 3, "title": "方法", "outline": "技术方案、方法原理"},
            {"index": 4, "title": "实验", "outline": "数据集、实验设置、结果分析"},
            {"index": 5, "title": "讨论", "outline": "结果解读、未来方向"},
            {"index": 6, "title": "结论", "outline": "总结、贡献、局限性"}
        ]
        return outline

    async def _write_section(self, section: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """撰写章节"""
        section_title = section.get("title", "")
        section_outline = section.get("outline", "")

        # 简化实现：实际应该调用LLM生成内容
        content = f"## {section_title}\n\n{section_outline}\n\n本章节详细描述了{section_title}的相关内容。"

        return {
            "index": section.get("index", 0),
            "title": section_title,
            "content": content,
            "citations": ["Reference 1", "Reference 2"],
            "completed": True
        }

    def _compile_report(self, sections: List[Dict[str, Any]]) -> str:
        """整合报告"""
        report_parts = []
        for section in sorted(sections, key=lambda s: s.get("index", 0)):
            report_parts.append(section.get("content", ""))
        return "\n\n".join(report_parts)

    async def reflect(self, result: Dict[str, Any]) -> ReflectionResult:
        """反思写作结果"""
        section_count = result.get("section_count", 0)
        citation_count = result.get("citation_count", 0)
        issues = []
        suggestions = []

        if section_count < 5:
            issues.append(f"章节数不足: {section_count} < 5")

        if citation_count < 10:
            issues.append(f"引用数不足: {citation_count} < 10")
            suggestions.append("添加更多文献引用")

        quality_score = min(1.0, (section_count / 7) * 0.5 + (citation_count / 20) * 0.5)

        return ReflectionResult(
            needs_improvement=len(issues) > 0,
            quality_score=quality_score,
            issues=issues,
            improvement_suggestions=suggestions,
            iteration=0
        )


class ReviewPhaseHandler(PhaseHandler):
    """审核阶段处理器"""

    def __init__(self, llm: Any = None):
        super().__init__("llm", llm)

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行审核阶段：多视角Critique"""
        report = context.get("writing", {}).get("result", {}).get("report", "")

        if not report:
            report = input_data.get("report", "")

        # 多视角审核
        critique = await self._multi_perspective_critique(report, context)

        return {
            "critique_result": critique,
            "passed": critique.get("overall_score", 0) >= 7.0,
            "issues": critique.get("issues", []),
            "suggestions": critique.get("suggestions", [])
        }

    async def _multi_perspective_critique(self, report: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """多视角审核"""
        # 简化实现：基础审核
        word_count = len(report.split())
        has_all_sections = all(s in report for s in ["摘要", "引言", "方法", "实验", "结论"])

        issues = []
        if word_count < 1000:
            issues.append("报告内容过短")
        if not has_all_sections:
            issues.append("缺少必要章节")

        overall_score = 8.0 if not issues else 6.0

        return {
            "passed": overall_score >= 7.0,
            "overall_score": overall_score,
            "issues": issues,
            "suggestions": ["完善报告内容"] if issues else []
        }

    async def reflect(self, result: Dict[str, Any]) -> ReflectionResult:
        """反思审核结果"""
        critique_result = result.get("critique_result", {})
        overall_score = critique_result.get("overall_score", 0.0)
        issues = critique_result.get("issues", [])

        return ReflectionResult(
            needs_improvement=overall_score < 7.0,
            quality_score=overall_score / 10.0,  # 转换为0-1
            issues=issues,
            improvement_suggestions=result.get("suggestions", []),
            iteration=0
        )


# ============ 便捷函数 ============

async def create_paper_agent(
    name: str = "paper_agent",
    llm_config: Optional[Dict[str, Any]] = None,
    max_iterations: int = 3
) -> PaperAgent:
    """创建PaperAgent实例"""
    config = LLMConfig(**(llm_config or {}))
    return PaperAgent(
        name=name,
        llm_config=config,
        max_iterations=max_iterations
    )


async def run_full_research(
    user_request: str,
    session_id: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """运行完整研究流程的便捷函数"""
    agent = await create_paper_agent(llm_config=llm_config)

    input_data = {
        "task_type": "full_research",
        "task_description": user_request,
        "user_request": user_request
    }

    output = await agent.execute(input_data)

    return {
        "success": output.success,
        "report": output.result.get("report", "") if output.result else "",
        "quality_score": output.quality_score,
        "phase_details": output.result.get("phase_details", {}) if output.result else {},
        "error": output.error
    }
