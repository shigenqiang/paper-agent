"""
ACML - Agent Collaboration Markup Language

用于定义多Agent协作工作流的领域特定语言。
"""
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """ACML节点类型"""
    AGENT = "agent"
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    CONDITION = "condition"
    LOOP = "loop"
    WAIT = "wait"
    MERGE = "merge"
    OUTPUT = "output"


class EdgeType(str, Enum):
    """边类型"""
    NEXT = "next"
    SUCCESS = "success"
    FAILURE = "failure"
    DATA = "data"


@dataclass
class ACMLNode:
    """ACML节点"""
    node_id: str
    node_type: NodeType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)  # 输入边
    outputs: List[str] = field(default_factory=list)  # 输出边


@dataclass
class ACMLEdge:
    """ACML边"""
    edge_id: str
    source: str  # 源节点
    target: str  # 目标节点
    edge_type: EdgeType = EdgeType.NEXT
    data_mapping: Optional[Dict[str, str]] = None  # 数据映射


@dataclass
class ACMLWorkflow:
    """ACML工作流"""
    name: str
    description: str = ""
    version: str = "1.0"
    nodes: List[ACMLNode] = field(default_factory=list)
    edges: List[ACMLEdge] = field(default_factory=list)
    entry_point: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_type": n.node_type.value,
                    "name": n.name,
                    "config": n.config,
                    "inputs": n.inputs,
                    "outputs": n.outputs
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "edge_id": e.edge_id,
                    "source": e.source,
                    "target": e.target,
                    "edge_type": e.edge_type.value,
                    "data_mapping": e.data_mapping
                }
                for e in self.edges
            ],
            "entry_point": self.entry_point
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ACMLWorkflow":
        nodes = [
            ACMLNode(
                node_id=n["node_id"],
                node_type=NodeType(n["node_type"]),
                name=n["name"],
                config=n.get("config", {}),
                inputs=n.get("inputs", []),
                outputs=n.get("outputs", [])
            )
            for n in data.get("nodes", [])
        ]

        edges = [
            ACMLEdge(
                edge_id=e["edge_id"],
                source=e["source"],
                target=e["target"],
                edge_type=EdgeType(e.get("edge_type", "next")),
                data_mapping=e.get("data_mapping")
            )
            for e in data.get("edges", [])
        ]

        return cls(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            nodes=nodes,
            edges=edges,
            entry_point=data.get("entry_point")
        )


class ACMLParser:
    """
    ACML解析器

    将ACML JSON/YAML转换为ACMLWorkflow对象

    使用示例:
        parser = ACMLParser()

        # 从JSON解析
        workflow = parser.parse_json('''
        {
            "name": "paper_writing",
            "nodes": [...],
            "edges": [...]
        }
        ''')

        # 验证工作流
        errors = parser.validate(workflow)
    """

    def parse_json(self, json_str: str) -> ACMLWorkflow:
        """从JSON解析"""
        data = json.loads(json_str)
        return ACMLWorkflow.from_dict(data)

    def parse_dict(self, data: Dict[str, Any]) -> ACMLWorkflow:
        """从字典解析"""
        return ACMLWorkflow.from_dict(data)

    def validate(self, workflow: ACMLWorkflow) -> List[str]:
        """
        验证工作流

        Returns:
            错误列表，空表示验证通过
        """
        errors = []

        # 检查是否有节点
        if not workflow.nodes:
            errors.append("Workflow has no nodes")
            return errors

        # 检查entry_point是否存在
        if workflow.entry_point:
            node_ids = {n.node_id for n in workflow.nodes}
            if workflow.entry_point not in node_ids:
                errors.append(f"Entry point '{workflow.entry_point}' not found")

        # 检查边的引用是否有效
        node_ids = {n.node_id for n in workflow.nodes}
        for edge in workflow.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge '{edge.edge_id}' references non-existent source '{edge.source}'")
            if edge.target not in node_ids:
                errors.append(f"Edge '{edge.edge_id}' references non-existent target '{edge.target}'")

        # 检查没有孤立节点（除了entry_point）
        connected_nodes: Set[str] = set()
        for edge in workflow.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)

        for node in workflow.nodes:
            if node.node_id != workflow.entry_point and node.node_id not in connected_nodes:
                errors.append(f"Node '{node.node_id}' is isolated (not connected to workflow)")

        # 检查agent节点的配置
        for node in workflow.nodes:
            if node.node_type == NodeType.AGENT:
                if "agent_id" not in node.config:
                    errors.append(f"Agent node '{node.node_id}' missing 'agent_id' in config")

        return errors


class ACMLExecutor:
    """
    ACML执行器

    执行ACML工作流

    使用示例:
        executor = ACMLExecutor()

        # 注册Agent
        executor.register_agent("researcher", researcher_agent)
        executor.register_agent("writer", writer_agent)

        # 执行工作流
        result = await executor.execute(workflow, initial_input)
    """

    def __init__(self):
        self._agents: Dict[str, Any] = {}

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """注册Agent"""
        self._agents[agent_id] = agent

    async def execute(
        self,
        workflow: ACMLWorkflow,
        initial_input: Any = None
    ) -> Dict[str, Any]:
        """
        执行工作流

        Args:
            workflow: ACML工作流
            initial_input: 初始输入

        Returns:
            执行结果
        """
        parser = ACMLParser()
        errors = parser.validate(workflow)

        if errors:
            return {"success": False, "errors": errors}

        # 构建节点图
        node_map = {n.node_id: n for n in workflow.nodes}
        adjacency = self._build_adjacency(workflow)

        # 从entry_point开始执行
        entry = workflow.entry_point or (workflow.nodes[0].node_id if workflow.nodes else None)
        if not entry:
            return {"success": False, "error": "No entry point"}

        # 执行
        context = {"input": initial_input, "results": {}}
        current = entry

        while current:
            node = node_map.get(current)
            if not node:
                break

            try:
                result = await self._execute_node(node, context)
                context["results"][current] = result

                # 获取下一个节点
                current = self._get_next_node(current, adjacency, result)

            except Exception as e:
                logger.error(f"Node {current} execution failed: {e}")
                return {"success": False, "error": str(e), "failed_node": current}

        return {
            "success": True,
            "results": context["results"]
        }

    async def _execute_node(self, node: ACMLNode, context: Dict[str, Any]) -> Any:
        """执行单个节点"""
        if node.node_type == NodeType.AGENT:
            agent_id = node.config.get("agent_id")
            agent = self._agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent not found: {agent_id}")

            # 调用Agent
            if hasattr(agent, 'execute'):
                return await agent.execute(node.config.get("input", context.get("input")))
            elif hasattr(agent, '__call__'):
                return await agent(node.config.get("input", context.get("input")))
            else:
                return None

        elif node.node_type == NodeType.SEQUENCE:
            return {"type": "sequence", "status": "completed"}

        elif node.node_type == NodeType.PARALLEL:
            return {"type": "parallel", "status": "completed"}

        elif node.node_type == NodeType.OUTPUT:
            return node.config.get("value", context.get("input"))

        return None

    def _build_adjacency(self, workflow: ACMLWorkflow) -> Dict[str, List[str]]:
        """构建邻接表"""
        adjacency: Dict[str, List[str]] = {n.node_id: [] for n in workflow.nodes}

        for edge in workflow.edges:
            if edge.edge_type == EdgeType.NEXT:
                adjacency[edge.source].append(edge.target)

        return adjacency

    def _get_next_node(
        self,
        current: str,
        adjacency: Dict[str, List[str]],
        result: Any
    ) -> Optional[str]:
        """获取下一个节点"""
        next_nodes = adjacency.get(current, [])
        return next_nodes[0] if next_nodes else None


# 预定义工作流模板

PAPER_WRITING_WORKFLOW = ACMLWorkflow(
    name="paper_writing",
    description="完整论文写作流程",
    nodes=[
        ACMLNode(
            node_id="topic_select",
            node_type=NodeType.AGENT,
            name="选题",
            config={"agent_id": "topic_agent", "input": "user_topic"}
        ),
        ACMLNode(
            node_id="literature_search",
            node_type=NodeType.AGENT,
            name="文献搜索",
            config={"agent_id": "literature_agent", "input": "topic"}
        ),
        ACMLNode(
            node_id="outline_gen",
            node_type=NodeType.AGENT,
            name="大纲生成",
            config={"agent_id": "outline_agent", "input": "topic+literature"}
        ),
        ACMLNode(
            node_id="draft_write",
            node_type=NodeType.AGENT,
            name="初稿撰写",
            config={"agent_id": "draft_agent", "input": "outline+literature"}
        ),
        ACMLNode(
            node_id="revision",
            node_type=NodeType.AGENT,
            name="修订",
            config={"agent_id": "revision_agent", "input": "draft"}
        ),
        ACMLNode(
            node_id="polish",
            node_type=NodeType.AGENT,
            name="润色",
            config={"agent_id": "polish_agent", "input": "revised_draft"}
        ),
    ],
    edges=[
        ACMLEdge(edge_id="e1", source="topic_select", target="literature_search"),
        ACMLEdge(edge_id="e2", source="literature_search", target="outline_gen"),
        ACMLEdge(edge_id="e3", source="outline_gen", target="draft_write"),
        ACMLEdge(edge_id="e4", source="draft_write", target="revision"),
        ACMLEdge(edge_id="e5", source="revision", target="polish"),
    ],
    entry_point="topic_select"
)


def create_acml_parser() -> ACMLParser:
    """创建ACML解析器"""
    return ACMLParser()


def create_acml_executor() -> ACMLExecutor:
    """创建ACML执行器"""
    return ACMLExecutor()
