"""
多Agent辩论系统 - Multi-Agent Debate

多个Agent从不同角度审视问题，通过辩论得出更全面的结论。
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class DebateRole(Enum):
    """辩论角色"""
    ADVOCATE = "advocate"      # 主张方
    OPPONENT = "opponent"      # 反对方
    MODERATOR = "moderator"    # 主持人
    EXPERT = "expert"         # 专家


@dataclass
class DebateStatement:
    """辩论陈述"""
    speaker: str
    role: DebateRole
    content: str
    timestamp: float = field(default_factory=time.time)
    evidence: List[str] = field(default_factory=list)
    rebuttals: List[str] = field(default_factory=list)
    quality_score: float = 0.5


@dataclass
class DebateResult:
    """辩论结果"""
    topic: str
    rounds: int
    final_position: str
    supporting_evidence: List[str]
    opposing_arguments: List[str]
    consensus_reached: bool
    confidence: float
    debate_log: List[DebateStatement]


class MultiAgentDebate:
    """多Agent辩论系统

    支持:
    - 多角度辩论
    - 观点收敛
    - 证据整合
    """

    def __init__(self, llm: Any = None):
        """初始化

        Args:
            llm: LLM实例
        """
        self.llm = llm
        self._agents: Dict[str, DebateRole] = {}

    def register_agent(self, agent_id: str, role: DebateRole):
        """注册Agent

        Args:
            agent_id: Agent ID
            role: 辩论角色
        """
        self._agents[agent_id] = role
        logger.info(f"注册辩论Agent: {agent_id} -> {role.value}")

    async def conduct_debate(self,
                            topic: str,
                            agents: List[str],
                            max_rounds: int = 3) -> DebateResult:
        """执行辩论

        Args:
            topic: 辩题
            agents: 参与的Agent ID列表
            max_rounds: 最大轮数

        Returns:
            DebateResult: 辩论结果
        """
        statements = []
        positions = {agent: self._initial_position(topic, agent) for agent in agents}

        for round_num in range(max_rounds):
            logger.info(f"辩论第 {round_num + 1} 轮")

            # 各Agent发表观点
            for agent in agents:
                position = positions[agent]
                statement = await self._generate_statement(
                    topic, agent, position, round_num
                )
                statements.append(statement)
                positions[agent] = statement.content

            # 检查是否收敛
            if self._check_convergence(positions):
                logger.info("辩论收敛")
                break

        # 整合最终结果
        result = self._compile_result(topic, statements, positions, max_rounds)
        return result

    async def _generate_statement(self,
                                   topic: str,
                                   agent: str,
                                   current_position: str,
                                   round_num: int) -> DebateStatement:
        """生成辩论陈述

        Args:
            topic: 辩题
            agent: Agent ID
            current_position: 当前立场
            round_num: 当前轮次

        Returns:
            DebateStatement: 陈述
        """
        role = self._agents.get(agent, DebateRole.ADVOCATE)

        if self.llm:
            try:
                prompt = f"""
Topic: {topic}
Agent: {agent}
Role: {role.value}
Current Position: {current_position}
Round: {round_num + 1}

Generate a statement that:
- Presents a clear argument
- Provides evidence or reasoning
- Addresses potential counterarguments

Return your statement in 2-3 sentences.
"""
                result = await self.llm.agenerate([prompt])
                content = result.generations[0][0].text.strip()

                return DebateStatement(
                    speaker=agent,
                    role=role,
                    content=content,
                    quality_score=0.8
                )
            except Exception as e:
                logger.error(f"生成陈述失败: {e}")

        # 回退
        return DebateStatement(
            speaker=agent,
            role=role,
            content=f"[{agent}] 关于 '{topic}' 的观点 (第{round_num + 1}轮)",
            quality_score=0.5
        )

    def _initial_position(self, topic: str, agent: str) -> str:
        """获取初始立场"""
        return f"Agent {agent} 对 '{topic}' 的初始立场"

    def _check_convergence(self, positions: Dict[str, str]) -> bool:
        """检查是否收敛"""
        if len(positions) < 2:
            return True

        first_pos = list(positions.values())[0]
        return all(pos == first_pos for pos in positions.values())

    def _compile_result(self,
                        topic: str,
                        statements: List[DebateStatement],
                        positions: Dict[str, str],
                        total_rounds: int) -> DebateResult:
        """编译辩论结果"""
        # 简单的位置聚合
        all_positions = list(positions.values())

        # 选择最常出现的位置作为最终立场
        position_counts: Dict[str, int] = {}
        for pos in all_positions:
            position_counts[pos] = position_counts.get(pos, 0) + 1

        final_position = max(position_counts, key=position_counts.get) if position_counts else ""

        supporting = [s.content for s in statements if s.role == DebateRole.ADVOCATE]
        opposing = [s.content for s in statements if s.role == DebateRole.OPPONENT]

        return DebateResult(
            topic=topic,
            rounds=total_rounds,
            final_position=final_position,
            supporting_evidence=supporting,
            opposing_arguments=opposing,
            consensus_reached=self._check_convergence(positions),
            confidence=sum(s.quality_score for s in statements) / len(statements) if statements else 0.5,
            debate_log=statements
        )


class HierarchicalOrchestrator:
    """层级编排器

    动态分解任务，分配给合适的Agent，聚合结果。
    """

    def __init__(self, llm: Any = None):
        """初始化"""
        self.llm = llm
        self._subtasks: Dict[str, Any] = {}
        self._results: Dict[str, Any] = {}

    async def decompose_task(self, task: str) -> List[Dict[str, str]]:
        """分解任务

        Args:
            task: 任务描述

        Returns:
            List[Dict]: 子任务列表 [{"id": "1", "description": "...", "agent_type": "..."}]
        """
        if self.llm:
            try:
                prompt = f"""
Task: {task}

Decompose this task into 3-5 subtasks that can be executed in parallel.
Each subtask should be independent and have a clear output.

Return a JSON list of subtasks with fields: id, description, agent_type
"""
                result = await self.llm.agenerate([prompt])
                response = result.generations[0][0].text.strip()

                import json
                import re

                # 尝试提取JSON
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    return json.loads(match.group())

            except Exception as e:
                logger.error(f"任务分解失败: {e}")

        # 回退：简单分解
        return [
            {"id": "1", "description": f"执行任务: {task}", "agent_type": "default"}
        ]

    async def execute_subtask(self,
                              subtask: Dict[str, str],
                              executor: Callable) -> Any:
        """执行子任务

        Args:
            subtask: 子任务
            executor: 执行器函数

        Returns:
            Any: 执行结果
        """
        subtask_id = subtask.get("id", "")
        self._subtasks[subtask_id] = subtask

        logger.info(f"执行子任务: {subtask_id}")

        try:
            result = await executor(subtask)
            self._results[subtask_id] = result
            return result
        except Exception as e:
            logger.error(f"子任务执行失败 {subtask_id}: {e}")
            return None

    async def aggregate_results(self, subtask_ids: List[str]) -> Dict[str, Any]:
        """聚合结果

        Args:
            subtask_ids: 子任务ID列表

        Returns:
            Dict: 聚合后的结果
        """
        results = [self._results.get(sid) for sid in subtask_ids if sid in self._results]

        if self.llm and results:
            try:
                prompt = f"""
Aggregate the following results into a coherent summary:

{results}

Provide a structured summary with key findings.
"""
                result = await self.llm.agenerate([prompt])
                return {
                    "summary": result.generations[0][0].text.strip(),
                    "subtask_results": results
                }
            except Exception as e:
                logger.error(f"结果聚合失败: {e}")

        return {
            "summary": "结果聚合完成",
            "subtask_results": results
        }

    def get_task_graph(self) -> Dict[str, Any]:
        """获取任务图

        Returns:
            Dict: 任务依赖图
        """
        return {
            "subtasks": self._subtasks,
            "results": self._results,
            "subtask_count": len(self._subtasks),
            "completed_count": len(self._results)
        }


class AgentSkillLibrary:
    """Agent技能库

    管理Agent可用的技能，支持技能注册、发现和执行。
    """

    def __init__(self):
        """初始化"""
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._skill_history: List[Dict] = []

    def register_skill(self,
                       skill_name: str,
                       description: str,
                       execute_fn: Callable,
                       metadata: Dict = None):
        """注册技能

        Args:
            skill_name: 技能名称
            description: 技能描述
            execute_fn: 执行函数
            metadata: 元数据
        """
        self._skills[skill_name] = {
            "description": description,
            "execute_fn": execute_fn,
            "metadata": metadata or {},
            "usage_count": 0,
            "success_rate": 0.0
        }
        logger.info(f"注册技能: {skill_name}")

    def discover_skills(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """发现技能

        Args:
            query: 查询
            top_k: 返回数量

        Returns:
            List[Dict]: 匹配的技能列表
        """
        query_lower = query.lower()
        matched = []

        for name, skill in self._skills.items():
            desc = skill["description"].lower()
            if query_lower in desc or any(kw in desc for kw in query_lower.split()):
                matched.append({
                    "name": name,
                    "description": skill["description"],
                    "metadata": skill["metadata"]
                })

        return matched[:top_k]

    async def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """执行技能

        Args:
            skill_name: 技能名称
            **kwargs: 技能参数

        Returns:
            Any: 执行结果
        """
        if skill_name not in self._skills:
            raise ValueError(f"技能不存在: {skill_name}")

        skill = self._skills[skill_name]
        skill["usage_count"] += 1

        try:
            result = await skill["execute_fn"](**kwargs)
            self._skill_history.append({
                "skill": skill_name,
                "success": True,
                "timestamp": time.time()
            })
            return result
        except Exception as e:
            logger.error(f"技能执行失败 {skill_name}: {e}")
            self._skill_history.append({
                "skill": skill_name,
                "success": False,
                "timestamp": time.time(),
                "error": str(e)
            })
            raise

    def get_skill_stats(self) -> Dict[str, Any]:
        """获取技能统计

        Returns:
            Dict: 统计信息
        """
        total_usages = sum(s["usage_count"] for s in self._skills.values())
        return {
            "total_skills": len(self._skills),
            "total_usages": total_usages,
            "skills": {
                name: {
                    "usage_count": s["usage_count"],
                    "description": s["description"]
                }
                for name, s in self._skills.items()
            }
        }


# 便捷函数
async def run_debate(topic: str,
                     agents: List[str],
                     llm: Any = None,
                     max_rounds: int = 3) -> DebateResult:
    """运行辩论的便捷函数"""
    debate = MultiAgentDebate(llm=llm)
    for agent in agents:
        debate.register_agent(agent, DebateRole.ADVOCATE if agents.index(agent) % 2 == 0 else DebateRole.OPPONENT)
    return await debate.conduct_debate(topic, agents, max_rounds)