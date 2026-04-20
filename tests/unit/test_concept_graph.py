"""概念图谱测试"""
import pytest
from src.knowledge.concept_graph.concept_graph import ConceptGraph, ConceptNode, ConceptEdge


def test_concept_graph_creation():
    """测试概念图谱创建"""
    graph = ConceptGraph()
    assert graph.nodes == {}
    assert graph.edges == []
    assert graph.root_concepts == []


def test_add_node():
    """测试添加节点"""
    graph = ConceptGraph()
    node = ConceptNode(
        id="c1",
        name="机器学习",
        definition="一种人工智能的方法"
    )

    graph.add_node(node)

    assert len(graph.nodes) == 1
    assert "c1" in graph.nodes
    assert graph.nodes["c1"].name == "机器学习"
    assert "c1" in graph.root_concepts


def test_add_node_with_parent():
    """测试添加带父节点的概念"""
    graph = ConceptGraph()

    parent = ConceptNode(
        id="c1",
        name="机器学习",
        definition="一种人工智能的方法"
    )
    graph.add_node(parent)

    child = ConceptNode(
        id="c2",
        name="深度学习",
        definition="机器学习的一个分支",
        parent_id="c1"
    )
    graph.add_node(child)

    assert len(graph.nodes) == 2
    assert "c2" not in graph.root_concepts


def test_add_edge():
    """测试添加边"""
    graph = ConceptGraph()

    node1 = ConceptNode(id="c1", name="概念1", definition="定义1")
    node2 = ConceptNode(id="c2", name="概念2", definition="定义2")

    graph.add_node(node1)
    graph.add_node(node2)

    edge = ConceptEdge(
        source_id="c1",
        target_id="c2",
        relation_type="包含"
    )

    graph.add_edge(edge)

    assert len(graph.edges) == 1
    assert graph.edges[0].relation_type == "包含"


def test_get_children():
    """测试获取子概念"""
    graph = ConceptGraph()

    parent = ConceptNode(id="c1", name="父概念", definition="父定义")
    child1 = ConceptNode(id="c2", name="子概念1", definition="子定义1", parent_id="c1")
    child2 = ConceptNode(id="c3", name="子概念2", definition="子定义2", parent_id="c1")

    graph.add_node(parent)
    graph.add_node(child1)
    graph.add_node(child2)

    children = graph.get_children("c1")
    assert len(children) == 2
    assert children[0].name in ["子概念1", "子概念2"]
    assert children[1].name in ["子概念1", "子概念2"]


def test_find_concepts_by_name():
    """测试根据名称查找概念"""
    graph = ConceptGraph()

    node1 = ConceptNode(id="c1", name="机器学习", definition="定义1")
    node2 = ConceptNode(id="c2", name="深度学习", definition="定义2")

    graph.add_node(node1)
    graph.add_node(node2)

    results = graph.find_concepts_by_name("学习")
    assert len(results) == 2

    results = graph.find_concepts_by_name("深度")
    assert len(results) == 1
    assert results[0].name == "深度学习"
