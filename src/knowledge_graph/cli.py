"""
知识图谱构建工具
Command-line interface for building academic knowledge graphs
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge_graph import AcademicGraphBuilder
from src.knowledge_graph.config import KGConfig


def build_from_pdf(
    pdf_path: str,
    output_path: Optional[str] = None,
    verbose: bool = False
):
    """从PDF文件构建知识图谱"""
    config = KGConfig()
    builder = AcademicGraphBuilder(config)

    if verbose:
        print(f"正在解析PDF: {pdf_path}")

    result = builder.build_from_documents([pdf_path])

    if verbose:
        print(f"构建完成!")
        print(f"  - 实体数量: {result.statistics.get('total_entities', 0)}")
        print(f"  - 关系数量: {result.statistics.get('total_relations', 0)}")

    if output_path:
        builder.save(output_path)
        if verbose:
            print(f"已保存到: {output_path}")

    return result


def build_from_directory(
    dir_path: str,
    output_path: Optional[str] = None,
    file_pattern: str = "*.pdf",
    verbose: bool = False
):
    """从目录批量构建知识图谱"""
    config = KGConfig()
    builder = AcademicGraphBuilder(config)

    if verbose:
        print(f"正在扫描目录: {dir_path}")

    result = builder.build_from_directory(dir_path, file_pattern)

    if verbose:
        print(f"批量构建完成!")
        print(f"  - 处理文件数: {result.statistics.get('processed_files', 0)}")
        print(f"  - 实体数量: {result.statistics.get('total_entities', 0)}")
        print(f"  - 关系数量: {result.statistics.get('total_relations', 0)}")

    if output_path:
        builder.save(output_path)
        if verbose:
            print(f"已保存到: {output_path}")

    return result


def visualize(
    graph_path: str,
    output_path: str,
    layout: str = "force",
    max_nodes: int = 100
):
    """生成知识图谱可视化"""
    from src.knowledge_graph.storage.neo4j_client import Neo4jClient
    from src.knowledge_graph.visualization import KnowledgeGraphVisualizer
    from src.knowledge_graph.visualization import VisualizationConfig

    # 连接图数据库
    client = Neo4jClient()

    # 查询子图
    subgraph = client.query_subgraph(center_id="", depth=2)

    # 可视化
    config = VisualizationConfig(
        layout=layout,
        max_nodes=max_nodes
    )
    visualizer = KnowledgeGraphVisualizer(config)

    vis_data = visualizer.visualize(subgraph)

    # 导出HTML
    visualizer.export_to_html(subgraph, output_path)

    print(f"可视化已导出到: {output_path}")


def query(
    query_text: str,
    top_k: int = 5,
    verbose: bool = False
):
    """查询知识图谱"""
    from src.knowledge_graph.graphrag import SubgraphRetriever, KGReasoner

    config = KGConfig()
    retriever = SubgraphRetriever(config)

    if verbose:
        print(f"正在检索: {query_text}")

    results = retriever.retrieve(query_text, top_k=top_k)

    print(f"\n检索结果:")
    for i, result in enumerate(results, 1):
        print(f"\n--- 结果 {i} ---")
        print(f"社区: {result.get('community_id', 'N/A')}")
        print(f"摘要: {result.get('description', 'N/A')}")

    return results


def stats():
    """显示知识图谱统计信息"""
    from src.knowledge_graph.storage.neo4j_client import Neo4jClient

    client = Neo4jClient()
    stats = client.get_statistics()

    print("\n知识图谱统计:")
    print(f"  - 实体总数: {stats.get('total_entities', 0)}")
    print(f"  - 关系总数: {stats.get('total_relations', 0)}")

    entity_types = stats.get('entity_types', {})
    if entity_types:
        print("\n  实体类型分布:")
        for etype, count in entity_types.items():
            print(f"    - {etype}: {count}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="学术论文知识图谱构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # build命令 - 从PDF构建
    build_parser = subparsers.add_parser("build", help="从PDF构建知识图谱")
    build_parser.add_argument("input", help="输入PDF文件路径或目录路径")
    build_parser.add_argument("-o", "--output", help="输出文件路径")
    build_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    build_parser.add_argument("-d", "--directory", action="store_true", help="批量处理目录")
    build_parser.add_argument("-p", "--pattern", default="*.pdf", help="文件匹配模式(批量模式)")

    # visualize命令 - 生成可视化
    viz_parser = subparsers.add_parser("visualize", help="生成知识图谱可视化")
    viz_parser.add_argument("graph", help="图数据路径")
    viz_parser.add_argument("-o", "--output", default="kg_visualization.html", help="输出HTML路径")
    viz_parser.add_argument("-l", "--layout", default="force", choices=["force", "circular", "hierarchical"], help="布局类型")
    viz_parser.add_argument("-m", "--max-nodes", type=int, default=100, help="最大节点数")

    # query命令 - 查询
    query_parser = subparsers.add_parser("query", help="查询知识图谱")
    query_parser.add_argument("text", help="查询文本")
    query_parser.add_argument("-k", "--top-k", type=int, default=5, help="返回结果数量")
    query_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    # stats命令 - 显示统计
    subparsers.add_parser("stats", help="显示知识图谱统计信息")

    # 解析参数
    args = parser.parse_args()

    if args.command == "build":
        if args.directory:
            build_from_directory(args.input, args.output, args.pattern, args.verbose)
        else:
            build_from_pdf(args.input, args.output, args.verbose)

    elif args.command == "visualize":
        visualize(args.graph, args.output, args.layout, args.max_nodes)

    elif args.command == "query":
        query(args.text, args.top_k, args.verbose)

    elif args.command == "stats":
        stats()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()