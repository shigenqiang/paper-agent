"""迁移脚本：平铺 JSON → 项目目录隔离 / proj_* → 项目名称目录

两种迁移模式：
1. 平铺 JSON → 项目目录（旧版兼容）
2. proj_* 目录 → 项目名称目录（当前版本）

用法:
    python -m scripts.migrate_storage               # 迁移
    python -m scripts.migrate_storage --dry-run      # 仅预览
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

DEFAULT_DATA_DIR = Path("data/research_workspace")

# 需要按 project_id 分组迁移的集合（旧版平铺迁移用）
PROJECT_SCOPED = [
    "papers", "paper_cards", "evidence_records", "reports", "report_versions",
    "graphs", "chunks", "paper_chunks", "parse_results", "qa_history",
    "search_sessions",
]


def load_json(path: Path) -> list | dict | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sanitize_dirname(name: str) -> str:
    """与 storage.sanitize_dirname 相同逻辑"""
    import re
    s = name.strip()
    s = re.sub(r"[^\w.\-]", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    if len(s) > 64:
        s = s[:64].rstrip("_")
    return s if s else "untitled"


def unique_dirname(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    i = 2
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"


# ── 迁移模式 2: proj_* → 项目名称目录 ──


def migrate_project_dirs(data_dir: Path, dry_run: bool = False) -> None:
    """将 proj_* 目录重命名为项目名称目录，并写入 project.json"""
    projects_dir = data_dir / "projects"
    if not projects_dir.exists():
        print(f"[SKIP] 项目目录不存在: {projects_dir}")
        return

    # 加载旧的 projects.json 索引（如果存在）
    projects_index = {}
    projects_json = data_dir / "projects.json"
    if projects_json.exists():
        items = load_json(projects_json)
        if isinstance(items, list):
            for p in items:
                projects_index[p.get("project_id", "")] = p

    # 收集已有的非 proj_* 目录名
    existing_dirs = set()
    for d in projects_dir.iterdir():
        if d.is_dir() and not d.name.startswith("proj_"):
            existing_dirs.add(d.name)

    migrated = 0
    for d in sorted(projects_dir.iterdir()):
        if not d.is_dir() or not d.name.startswith("proj_"):
            continue

        project_id = d.name  # e.g. proj_a1b2c3d4

        # 尝试获取项目名称
        # 优先从目录内 project.json 获取
        meta = load_json(d / "project.json")
        if not meta:
            # 从全局 projects.json 获取
            meta = projects_index.get(project_id)

        if not meta:
            print(f"[WARN] {project_id}: 无元数据，跳过")
            continue

        name = meta.get("name", project_id)
        base_dir = sanitize_dirname(name)
        new_dir_name = unique_dirname(base_dir, existing_dirs)
        existing_dirs.add(new_dir_name)

        new_path = projects_dir / new_dir_name
        print(f"[MIGRATE] {project_id} -> {new_dir_name}/")

        if not dry_run:
            # 重命名目录
            if new_path.exists():
                print(f"  [WARN] 目标目录已存在: {new_dir_name}，跳过")
                continue
            d.rename(new_path)

            # 写入 project.json（补充 dir_name 字段）
            meta["dir_name"] = new_dir_name
            if "project_id" not in meta:
                meta["project_id"] = project_id
            save_json(new_path / "project.json", meta)

        migrated += 1

    # 备份旧的 projects.json
    if not dry_run and projects_json.exists():
        backup = projects_json.with_suffix(".json.bak")
        shutil.move(str(projects_json), str(backup))
        print(f"[BACKUP] projects.json -> {backup.name}")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}迁移完成: {migrated} 个项目目录已重命名")


# ── 迁移模式 1: 平铺 JSON → 项目目录（旧版兼容） ──


def migrate_flat_json(data_dir: Path, dry_run: bool = False) -> None:
    """将旧版平铺 JSON 文件按 project_id 分组到项目目录"""
    if not data_dir.exists():
        print(f"[SKIP] 数据目录不存在: {data_dir}")
        return

    projects_dir = data_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    # 读取已有的项目列表
    projects_data = load_json(data_dir / "projects.json")
    if isinstance(projects_data, list):
        for proj in projects_data:
            pid = proj.get("project_id")
            if pid:
                proj_dir = projects_dir / pid
                if not proj_dir.exists():
                    print(f"[MKDIR] {proj_dir}")
                    if not dry_run:
                        proj_dir.mkdir(parents=True, exist_ok=True)

    total_moved = 0

    for name in PROJECT_SCOPED:
        flat_file = data_dir / f"{name}.json"
        if not flat_file.exists():
            continue

        items = load_json(flat_file)
        if not isinstance(items, list) or not items:
            continue

        grouped: dict[str, list] = {}
        for item in items:
            pid = item.get("project_id")
            if pid:
                grouped.setdefault(pid, []).append(item)

        if not grouped:
            continue

        print(f"\n[FILE] {flat_file.name}: {len(items)} 条记录")
        for pid, pid_items in grouped.items():
            proj_dir = projects_dir / pid
            target = proj_dir / f"{name}.json"
            print(f"  -> {pid}: {len(pid_items)} 条 -> {target}")

            if not dry_run:
                existing = load_json(target) or []
                if isinstance(existing, list):
                    save_json(target, existing + pid_items)
                else:
                    save_json(target, pid_items)

            total_moved += len(pid_items)

        if not dry_run:
            backup = flat_file.with_suffix(".json.bak")
            shutil.move(str(flat_file), str(backup))

    print(f"\n{'[DRY RUN] ' if dry_run else ''}迁移完成，共处理 {total_moved} 条记录")


def main():
    parser = argparse.ArgumentParser(description="存储迁移脚本")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际写入")
    parser.add_argument("--mode", choices=["dirs", "flat", "auto"], default="auto",
                        help="dirs: proj_*→名称目录; flat: 平铺JSON→项目目录; auto: 自动检测")
    args = parser.parse_args()

    if args.mode == "auto":
        # 检测需要哪种迁移
        projects_dir = args.data_dir / "projects"
        has_proj_dirs = any(
            d.is_dir() and d.name.startswith("proj_")
            for d in (projects_dir.iterdir() if projects_dir.exists() else [])
        )
        has_flat = any(
            (args.data_dir / f"{n}.json").exists()
            for n in ["papers", "paper_cards", "evidence_records"]
        )

        if has_proj_dirs:
            print("=== 检测到 proj_* 目录，执行目录重命名迁移 ===\n")
            migrate_project_dirs(args.data_dir, dry_run=args.dry_run)
        elif has_flat:
            print("=== 检测到平铺 JSON，执行分组迁移 ===\n")
            migrate_flat_json(args.data_dir, dry_run=args.dry_run)
        else:
            print("无需迁移")
    elif args.mode == "dirs":
        migrate_project_dirs(args.data_dir, dry_run=args.dry_run)
    else:
        migrate_flat_json(args.data_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
