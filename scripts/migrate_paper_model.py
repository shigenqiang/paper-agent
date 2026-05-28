"""迁移 papers.json 从旧扁平格式到新子模型格式

Usage:
    python -m scripts.migrate_paper_model --dry-run   # 预览
    python -m scripts.migrate_paper_model              # 执行
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

# 旧字段 → (子模型名, 子模型字段)
FIELD_MAPPING = {
    "doi": ("identifiers", "doi"),
    "arxiv_id": ("identifiers", "arxiv_id"),
    "pubmed_id": ("identifiers", "pubmed_id"),
    "openalex_id": ("identifiers", "openalex_id"),
    "semantic_scholar_id": ("identifiers", "semantic_scholar_id"),
    "year": ("dates", "year"),
    "venue": ("source", "venue"),
    "pdf_url": ("open_access", "pdf_url"),
    "concepts": ("classification", "concepts"),
    "keywords": ("classification", "keywords"),
    "citations": ("citation", "citation_count"),
}

# 旧字段中需要删除的顶层字段
FIELDS_TO_REMOVE = set(FIELD_MAPPING.keys()) | {"source"}


def is_old_format(paper: dict) -> bool:
    """判断是否为旧扁平格式"""
    return "year" in paper or "doi" in paper or "venue" in paper


def migrate_paper(paper: dict) -> dict:
    """将单篇论文从旧格式迁移到新格式"""
    if not is_old_format(paper):
        return paper  # 已经是新格式

    new_paper = dict(paper)

    # 构建子模型
    for old_field, (sub_model, sub_field) in FIELD_MAPPING.items():
        if old_field not in new_paper:
            continue
        value = new_paper.pop(old_field)
        if sub_model not in new_paper:
            new_paper[sub_model] = {}
        new_paper[sub_model][sub_field] = value

    # source → source_platform
    if "source" in new_paper:
        new_paper["source_platform"] = new_paper.pop("source")

    # authors: list[str] → list[dict]
    if "authors" in new_paper:
        authors = new_paper["authors"]
        if authors and isinstance(authors[0], str):
            new_paper["authors"] = [{"name": a} for a in authors]

    return new_paper


def migrate_papers_file(papers_path: Path, dry_run: bool = False) -> int:
    """迁移单个 papers.json 文件"""
    if not papers_path.exists():
        return 0

    with open(papers_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        return 0

    count = 0
    migrated = {}
    for paper_id, paper_data in data.items():
        if is_old_format(paper_data):
            migrated[paper_id] = migrate_paper(paper_data)
            count += 1
        else:
            migrated[paper_id] = paper_data

    if count > 0 and not dry_run:
        # 备份
        backup = papers_path.with_suffix(".json.bak")
        shutil.copy2(papers_path, backup)
        # 写入新格式
        with open(papers_path, "w", encoding="utf-8") as f:
            json.dump(migrated, f, ensure_ascii=False, indent=2)

    return count


def main():
    parser = argparse.ArgumentParser(description="迁移 papers.json 到新子模型格式")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入")
    parser.add_argument("--data-dir", default="data/research_workspace", help="数据目录")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    projects_dir = data_dir / "projects"

    if not projects_dir.exists():
        print(f"项目目录不存在: {projects_dir}")
        return

    total = 0
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        papers_path = project_dir / "papers.json"
        count = migrate_papers_file(papers_path, dry_run=args.dry_run)
        if count > 0:
            action = "Would migrate" if args.dry_run else "Migrated"
            print(f"  {action} {count} papers in {project_dir.name}/papers.json")
            total += count

    if total == 0:
        print("无需迁移（所有 papers.json 已是新格式或为空）")
    else:
        action = "would be" if args.dry_run else ""
        print(f"\n总计 {action}迁移 {total} 篇论文")


if __name__ == "__main__":
    main()
