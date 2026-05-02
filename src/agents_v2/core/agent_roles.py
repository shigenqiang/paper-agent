"""
Agent Role System - Agent角色系统

标准化的Agent角色和能力定义体系。
"""
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = get_logging_logger(__name__)


class ConstraintType(str, Enum):
    """约束类型"""
    TIME = "time"
    COST = "cost"
    QUALITY = "quality"
    RESOURCE = "resource"


@dataclass
class Capability:
    """能力定义"""
    name: str
    description: str
    input_types: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    quality_metrics: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


@dataclass
class Constraint:
    """约束条件"""
    type: ConstraintType
    value: Any
    soft: bool = False  # 软约束可突破，硬约束不行


@dataclass
class AgentRole:
    """Agent角色定义"""
    role_id: str
    name: str
    description: str
    capabilities: List[Capability] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    preferred_tools: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 3
    timeout_seconds: float = 300


class AgentRoleRegistry:
    """
    Agent角色注册表

    功能:
    - 注册角色
    - 分配角色给Agent
    - 根据任务需求找到最佳角色

    使用示例:
        registry = AgentRoleRegistry()

        # 注册角色
        registry.register_role(RESEARCH_ANALYST)

        # 分配角色
        registry.assign_role_to_agent("agent_1", "research_analyst")

        # 查找最佳角色
        best = registry.find_best_role({"required_capabilities": ["literature_analysis"]})
    """

    def __init__(self):
        self._roles: Dict[str, AgentRole] = {}
        self._agent_role_mapping: Dict[str, str] = {}  # agent_id -> role_id

    def register_role(self, role: AgentRole) -> None:
        """注册角色"""
        self._roles[role.role_id] = role
        logger.info(f"Registered role: {role.name}")

    def assign_role_to_agent(self, agent_id: str, role_id: str) -> None:
        """为Agent分配角色"""
        self._agent_role_mapping[agent_id] = role_id
        role = self._roles.get(role_id)
        logger.info(f"Assigned {agent_id} -> role {role.name if role else 'unknown'}")

    def get_role_for_agent(self, agent_id: str) -> Optional[AgentRole]:
        """获取Agent的角色"""
        role_id = self._agent_role_mapping.get(agent_id)
        return self._roles.get(role_id)

    def get_role(self, role_id: str) -> Optional[AgentRole]:
        """获取角色"""
        return self._roles.get(role_id)

    def find_best_role(self, task_requirements: Dict[str, Any]) -> Optional[AgentRole]:
        """
        根据任务需求找到最佳角色

        Args:
            task_requirements: 任务需求，包含:
                - required_capabilities: 必需的能力列表
                - preferred_tools: 偏好的工具
                - constraints: 约束条件

        Returns:
            Optional[AgentRole]: 最佳匹配角色
        """
        best_role = None
        best_score = 0.0

        required_caps = task_requirements.get("required_capabilities", [])
        preferred_tools = task_requirements.get("preferred_tools", [])
        constraints = task_requirements.get("constraints", {})

        for role in self._roles.values():
            # 检查约束
            if not self._satisfies_constraints(role, constraints):
                continue

            # 计算匹配分数
            score = self._calculate_role_match_score(
                role, required_caps, preferred_tools
            )

            if score > best_score:
                best_score = score
                best_role = role

        return best_role

    def _calculate_role_match_score(
        self,
        role: AgentRole,
        required_caps: List[str],
        preferred_tools: List[str]
    ) -> float:
        """计算机角色匹配分数"""
        if not required_caps:
            return 0.5  # 没有要求时给中等分数

        score = 0.0

        # 检查能力覆盖
        role_cap_names = [cap.name for cap in role.capabilities]
        caps_covered = sum(1 for cap in required_caps if cap in role_cap_names)
        cap_score = caps_covered / len(required_caps) if required_caps else 0

        # 工具偏好匹配
        tool_score = 0.0
        if preferred_tools and role.preferred_tools:
            tools_matched = sum(1 for t in preferred_tools if t in role.preferred_tools)
            tool_score = tools_matched / len(preferred_tools)

        # 综合分数
        score = cap_score * 0.7 + tool_score * 0.3

        return score

    def _satisfies_constraints(
        self,
        role: AgentRole,
        constraints: Dict[str, Any]
    ) -> bool:
        """检查是否满足约束"""
        for constraint in role.constraints:
            if constraint.type == ConstraintType.TIME:
                max_time = constraints.get("max_time")
                if max_time and constraint.value > max_time and not constraint.soft:
                    return False
            elif constraint.type == ConstraintType.COST:
                max_cost = constraints.get("max_cost")
                if max_cost and constraint.value > max_cost and not constraint.soft:
                    return False
        return True

    def list_roles(self) -> List[AgentRole]:
        """列出所有角色"""
        return list(self._roles.values())

    def list_agents_with_role(self, role_id: str) -> List[str]:
        """列出具有特定角色的所有Agent"""
        return [
            agent_id for agent_id, rid in self._agent_role_mapping.items()
            if rid == role_id
        ]


# 预定义角色

RESEARCH_ANALYST = AgentRole(
    role_id="research_analyst",
    name="研究分析师",
    description="深入分析研究主题，识别研究空白和机会",
    capabilities=[
        Capability(
            name="literature_analysis",
            description="文献分析与综合",
            input_types=["topic", "papers"],
            output_types=["analysis_report", "research_gaps"]
        ),
        Capability(
            name="trend_identification",
            description="研究趋势识别",
            input_types=["field", "papers"],
            output_types=["trends", "forecasts"]
        )
    ],
    constraints=[
        Constraint(ConstraintType.QUALITY, 0.8, soft=True),
        Constraint(ConstraintType.TIME, 120, soft=True)
    ],
    preferred_tools=["arxiv_searcher", "pubmed_searcher"],
    max_concurrent_tasks=2
)

WRITING_SPECIALIST = AgentRole(
    role_id="writing_specialist",
    name="写作专家",
    description="专业学术写作，结构清晰论证严密",
    capabilities=[
        Capability(
            name="academic_writing",
            description="学术论文写作",
            input_types=["outline", "content"],
            output_types=["paper_draft", "sections"]
        ),
        Capability(
            name="revision",
            description="论文修订润色",
            input_types=["draft", "feedback"],
            output_types=["revised_draft"]
        )
    ],
    constraints=[
        Constraint(ConstraintType.QUALITY, 0.85, soft=False),
        Constraint(ConstraintType.TIME, 180, soft=True)
    ],
    preferred_tools=["draft_generator", "language_polisher"],
    max_concurrent_tasks=1
)

LITERATURE_EXPERT = AgentRole(
    role_id="literature_expert",
    name="文献专家",
    description="高效搜索和筛选学术文献",
    capabilities=[
        Capability(
            name="literature_search",
            description="文献搜索",
            input_types=["topic", "keywords"],
            output_types=["papers", "metadata"]
        ),
        Capability(
            name="literature_review",
            description="文献综述",
            input_types=["papers"],
            output_types=["summary", "synthesis"]
        )
    ],
    constraints=[
        Constraint(ConstraintType.QUALITY, 0.75, soft=True),
        Constraint(ConstraintType.TIME, 60, soft=True)
    ],
    preferred_tools=["arxiv_searcher", "semantic_scholar"],
    max_concurrent_tasks=3
)

DIAGNOSTIC_EXPERT = AgentRole(
    role_id="diagnostic_expert",
    name="诊断专家",
    description="诊断论文问题并提供改进建议",
    capabilities=[
        Capability(
            name="problem_diagnosis",
            description="问题诊断",
            input_types=["paper"],
            output_types=["problems", "suggestions"]
        ),
        Capability(
            name="quality_assessment",
            description="质量评估",
            input_types=["paper"],
            output_types=["score", "feedback"]
        )
    ],
    constraints=[
        Constraint(ConstraintType.QUALITY, 0.8, soft=False),
        Constraint(ConstraintType.TIME, 30, soft=True)
    ],
    preferred_tools=["plagiarism_checker", "language_polisher"],
    max_concurrent_tasks=2
)


def create_role_registry() -> AgentRoleRegistry:
    """创建角色注册表并注册预定义角色"""
    registry = AgentRoleRegistry()
    registry.register_role(RESEARCH_ANALYST)
    registry.register_role(WRITING_SPECIALIST)
    registry.register_role(LITERATURE_EXPERT)
    registry.register_role(DIAGNOSTIC_EXPERT)
    return registry
