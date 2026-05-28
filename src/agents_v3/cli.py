"""agents_v3 命令行入口"""

from __future__ import annotations

import argparse
import json
import sys

from loguru import logger

from src.agents_v3.research_workspace import (
    EvidenceTableService,
    GraphService,
    InnovationReportGenerator,
    LiteratureReviewGenerator,
    PaperCardGenerator,
    PaperLibraryService,
    ParserService,
    ProjectService,
    ReportService,
    ScopeQAService,
)


def cmd_create_project(args: argparse.Namespace) -> None:
    ps = ProjectService()
    project = ps.create_project(args.name, description=args.description or "")
    print(json.dumps(project.model_dump(), ensure_ascii=False, indent=2))


def cmd_list_projects(args: argparse.Namespace) -> None:
    ps = ProjectService()
    projects = ps.list_projects()
    for p in projects:
        print(f"{p.project_id}\t{p.name}")


def cmd_add_paper(args: argparse.Namespace) -> None:
    pls = PaperLibraryService()
    paper = pls.add_paper_metadata(args.project_id, {"title": args.title}, source="manual")
    print(json.dumps(paper.model_dump(), ensure_ascii=False, indent=2))


def cmd_parse(args: argparse.Namespace) -> None:
    parser = ParserService()
    if args.paper_id:
        result = parser.parse_paper(args.paper_id)
    else:
        result = parser.parse_project_papers(args.project_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_build_cards(args: argparse.Namespace) -> None:
    gen = PaperCardGenerator()
    cards = gen.batch_generate(args.project_id)
    print(f"Generated {len(cards)} cards")


def cmd_build_evidence(args: argparse.Namespace) -> None:
    svc = EvidenceTableService()
    records = svc.build_for_project(args.project_id)
    print(f"Generated {len(records)} evidence records")


def cmd_build_graph(args: argparse.Namespace) -> None:
    svc = GraphService()
    graph = svc.build_project_graph(args.project_id)
    print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")


def cmd_qa(args: argparse.Namespace) -> None:
    svc = ScopeQAService()
    scope = {"type": args.scope_type or "all_project"}
    response = svc.answer(args.project_id, args.question, scope)
    print(f"Intent: {response.intent}")
    print(f"Scope: {response.scope_summary}")
    print(f"\n{response.answer}")
    if response.supporting_papers:
        print(f"\nSupporting: {', '.join(response.supporting_papers)}")


def cmd_generate_review(args: argparse.Namespace) -> None:
    gen = LiteratureReviewGenerator()
    scope = {"type": args.scope_type or "all_project"}
    report = gen.generate(args.project_id, scope)
    rs = ReportService()
    md = rs.export_markdown(report.report_id)
    print(md)


def cmd_generate_innovation(args: argparse.Namespace) -> None:
    gen = InnovationReportGenerator()
    scope = {"type": args.scope_type or "all_project"}
    report = gen.generate(args.project_id, scope)
    rs = ReportService()
    md = rs.export_markdown(report.report_id)
    print(md)


def cmd_stats(args: argparse.Namespace) -> None:
    ps = ProjectService()
    stats = ps.get_project_stats(args.project_id)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents_v3",
        description="论文知识库分析 Agent",
    )
    sub = parser.add_subparsers(dest="command")

    # create-project
    p = sub.add_parser("create-project", help="创建研究项目")
    p.add_argument("name", help="项目名称")
    p.add_argument("--description", "-d", help="项目描述")
    p.set_defaults(func=cmd_create_project)

    # list-projects
    p = sub.add_parser("list-projects", help="列出所有项目")
    p.set_defaults(func=cmd_list_projects)

    # add-paper
    p = sub.add_parser("add-paper", help="添加论文")
    p.add_argument("project_id", help="项目 ID")
    p.add_argument("title", help="论文标题")
    p.set_defaults(func=cmd_add_paper)

    # parse
    p = sub.add_parser("parse", help="解析论文")
    p.add_argument("--project-id", help="项目 ID")
    p.add_argument("--paper-id", help="论文 ID")
    p.set_defaults(func=cmd_parse)

    # build-cards
    p = sub.add_parser("build-cards", help="批量生成论文卡片")
    p.add_argument("project_id", help="项目 ID")
    p.set_defaults(func=cmd_build_cards)

    # build-evidence
    p = sub.add_parser("build-evidence", help="构建证据表")
    p.add_argument("project_id", help="项目 ID")
    p.set_defaults(func=cmd_build_evidence)

    # build-graph
    p = sub.add_parser("build-graph", help="构建知识图谱")
    p.add_argument("project_id", help="项目 ID")
    p.set_defaults(func=cmd_build_graph)

    # qa
    p = sub.add_parser("qa", help="Scope QA")
    p.add_argument("project_id", help="项目 ID")
    p.add_argument("question", help="问题")
    p.add_argument("--scope-type", default="all_project", help="范围类型")
    p.set_defaults(func=cmd_qa)

    # generate-review
    p = sub.add_parser("generate-review", help="生成文献综述")
    p.add_argument("project_id", help="项目 ID")
    p.add_argument("--scope-type", default="all_project", help="范围类型")
    p.set_defaults(func=cmd_generate_review)

    # generate-innovation
    p = sub.add_parser("generate-innovation", help="生成创新点报告")
    p.add_argument("project_id", help="项目 ID")
    p.add_argument("--scope-type", default="all_project", help="范围类型")
    p.set_defaults(func=cmd_generate_innovation)

    # stats
    p = sub.add_parser("stats", help="项目统计")
    p.add_argument("project_id", help="项目 ID")
    p.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
