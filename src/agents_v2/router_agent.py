"""RouterAgent - 智能路由器"""
import logging
from typing import List, Dict, Any, Optional
import json

from .base_agent import BaseAgent, AgentInput, AgentOutput, AgentCapability

logger = logging.getLogger(__name__)


class RouterAgent(BaseAgent):
    """
    路由Agent - 智能分配任务给最合适的Agent

    功能:
    - 分析任务类型和描述
    - 评估各个Agent的能力匹配度
    - 选择最合适的Agent执行任务
    - 支持多Agent协作调度
    """

    def __init__(self, agents: List[BaseAgent], llm_config=None):
        self.available_agents = agents
        super().__init__(
            name="RouterAgent",
            llm_config=llm_config,
            description="智能路由器，负责将任务分配给最合适的Agent",
            system_prompt="""你是RouterAgent，一个智能任务路由器。

你的职责:
1. 分析任务类型和需求
2. 评估可用Agent的能力
3. 选择最合适的Agent执行任务
4. 如果需要，规划多Agent协作

决策原则:
- 优先选择能力完全匹配的Agent
- 考虑Agent的专业性和历史表现
- 复杂任务可分解为多个子任务
- 保证任务执行的准确性和效率
"""
        )

    def _get_capabilities(self) -> AgentCapability:
        return AgentCapability(
            task_types=["*"],  # 路由器处理所有任务类型
            description="智能路由，任务分配，多Agent协调"
        )

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        """
        执行路由逻辑

        流程:
        1. 分析任务需求
        2. 评估候选Agent
        3. 选择最佳Agent
        4. 返回路由决策
        """
        try:
            # 1. 分析任务
            task_analysis = await self._analyze_task(input_data)

            # 2. 评估候选Agent
            candidates = await self._evaluate_candidates(task_analysis)

            # 3. 选择最佳Agent
            selected_agent = await self._select_best_agent(candidates)

            if not selected_agent:
                # 如果没有找到合适的Agent，返回错误
                return AgentOutput(
                    success=False,
                    agent_name=self.name,
                    error=f"没有找到能处理任务类型 {input_data.task_type} 的Agent"
                )

            logger.info(f"路由决策: 将任务分配给 {selected_agent.name}")

            # 4. 返回路由结果（包含Agent引用）
            return AgentOutput(
                success=True,
                result={
                    "selected_agent": selected_agent,
                    "task_analysis": task_analysis,
                    "routing_reasoning": candidates.get(selected_agent.name, {}).get("reasoning", ""),
                    "all_candidates": list(candidates.keys())
                },
                agent_name=self.name,
                reasoning=f"为任务 '{input_data.task_description}' 选择Agent: {selected_agent.name}"
            )

        except Exception as e:
            logger.error(f"路由失败: {e}")
            return AgentOutput(
                success=False,
                agent_name=self.name,
                error=str(e)
            )

    async def _analyze_task(self, input_data: AgentInput) -> Dict[str, Any]:
        """使用LLM分析任务"""
        prompt = f"""
请分析以下任务:

任务类型: {input_data.task_type}
任务描述: {input_data.task_description}
输入数据: {json.dumps(input_data.input_data, ensure_ascii=False)[:500]}
用户需求: {', '.join(input_data.requirements)}

请分析:
1. 任务的复杂度 (简单/中等/复杂)
2. 所需的关键能力
3. 是否需要分解为子任务
4. 优先级 (低/中/高)

以JSON格式返回:
{{
  "complexity": "simple|medium|complex",
  "required_capabilities": ["能力1", "能力2"],
  "needs_decomposition": true/false,
  "subtasks": ["子任务1", "子任务2"],
  "priority": "low|medium|high"
}}
"""

        try:
            response = await self._llm_call(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"任务分析失败: {e}")
            return {
                "complexity": "medium",
                "required_capabilities": [],
                "needs_decomposition": False,
                "subtasks": [],
                "priority": "medium"
            }

    async def _evaluate_candidates(self, task_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """评估候选Agent的能力匹配度"""
        candidates = {}

        # 为每个Agent评分
        for agent in self.available_agents:
            score, reasoning = await self._score_agent(agent, task_analysis)
            candidates[agent.name] = {
                "agent": agent,
                "score": score,
                "reasoning": reasoning
            }

        # 记录评估结果
        logger.info(f"Agent评估结果: {[(k, v['score']) for k, v in candidates.items()]}")

        return candidates

    async def _score_agent(self, agent: BaseAgent, task_analysis: Dict[str, Any]) -> tuple[float, str]:
        """
        为Agent打分

        评分因素:
        - 能力匹配度 (0-40分)
        - 专业性 (0-30分)
        - 历史表现 (0-30分)
        """
        score = 0.0
        reasons = []

        # 1. 能力匹配度 (40分)
        if agent.can_handle(task_analysis.get("complexity", "medium")):
            score += 40
            reasons.append("能力完全匹配")
        else:
            # 检查部分匹配
            capability_match = len([
                cap for cap in task_analysis.get("required_capabilities", [])
                if cap in agent.description.lower()
            ])
            score += capability_match * 10
            reasons.append(f"能力部分匹配 {capability_match}/{len(task_analysis.get('required_capabilities', []))}")

        # 2. 专业性 (30分)
        # 根据Agent的专业描述评分
        keywords = task_analysis.get("required_capabilities", [])
        keyword_count = sum(1 for kw in keywords if kw.lower() in agent.description.lower())
        score += min(30, keyword_count * 10)
        if keyword_count > 0:
            reasons.append(f"专业关键词匹配 {keyword_count}个")

        # 3. 工具数量 (加分项)
        tool_bonus = min(10, len(agent.tools) * 2)
        score += tool_bonus
        if tool_bonus > 0:
            reasons.append(f"工具丰富度加分 +{tool_bonus}")

        reasoning = "; ".join(reasons) if reasons else "无明显优势"

        return score, reasoning

    async def _select_best_agent(self, candidates: Dict[str, Any]) -> Optional[BaseAgent]:
        """选择评分最高的Agent"""
        if not candidates:
            return None

        # 按评分排序
        sorted_candidates = sorted(
            candidates.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        # 返回评分最高的Agent
        best_name = sorted_candidates[0][0]
        return candidates[best_name]["agent"]

    async def plan_multi_agent_workflow(
        self,
        input_data: AgentInput,
        agents: List[BaseAgent]
    ) -> Dict[str, Any]:
        """
        规划多Agent协作工作流

        用于复杂任务，需要多个Agent协作
        """
        prompt = f"""
复杂任务规划:

任务: {input_data.task_description}
输入数据: {json.dumps(input_data.input_data, ensure_ascii=False)[:300]}

可用Agent:
{self._format_agents_for_planning(agents)}

请规划一个多Agent协作的工作流:

1. 将任务分解为步骤
2. 为每个步骤选择合适的Agent
3. 定义步骤之间的依赖关系
4. 说明数据流转

以JSON格式返回:
{{
  "steps": [
    {{
      "step_id": 1,
      "description": "步骤描述",
      "agent": "Agent名称",
      "input": "步骤输入",
      "output": "期望输出"
    }}
  ],
  "dependencies": {{
    "step_2": ["step_1"],
    "step_3": ["step_1", "step_2"]
  }}
}}
"""

        try:
            response = await self._llm_call(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"多Agent工作流规划失败: {e}")
            return {}

    def _format_agents_for_planning(self, agents: List[BaseAgent]) -> str:
        """格式化Agent信息用于规划"""
        lines = []
        for agent in agents:
            lines.append(f"- {agent.name}:")
            lines.append(f"  描述: {agent.description}")
            lines.append(f"  能力: {', '.join(agent.capabilities.task_types)}")
        return "\n".join(lines)

    def get_agent_info(self) -> Dict[str, Any]:
        """获取所有可用Agent的信息"""
        return {
            agent.name: agent.to_dict()
            for agent in self.available_agents
        }


class CapabilityRouter(RouterAgent):
    """
    基于能力的路由器

    特点:
    - 快速路由，不使用LLM
    - 适用于简单任务
    - 可以作为缓存层
    """

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        """基于能力快速路由"""
        # 直接查找能处理该任务类型的Agent
        for agent in self.available_agents:
            if agent.can_handle(input_data.task_type):
                return AgentOutput(
                    success=True,
                    result={
                        "selected_agent": agent,
                        "routing_method": "capability_match"
                    },
                    agent_name=self.name
                )

        # 如果没有找到，返回错误
        return AgentOutput(
            success=False,
            agent_name=self.name,
            error=f"没有找到能处理任务类型 {input_data.task_type} 的Agent"
        )
