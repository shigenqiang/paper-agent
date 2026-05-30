"""端到端测试：删除指定项目并清理关联数据

运行方式（需先启动服务）:
    python -m tests.e2e.test_delete_project --id <project_id>
    # 或
    python tests/e2e/test_delete_project.py --id <project_id>

可选参数:
    --id <project_id>       项目 ID（必填，除非使用 --name）
    --name <project_name>   按名称查找项目（需唯一匹配）
    --list                  列出所有项目后退出
    --force                 跳过确认提示
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


# ── 工具函数 ──────────────────────────────────────────

def api(method: str, path: str, body: dict | None = None) -> dict:
    """调用 API，返回 JSON 响应"""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {err_body[:200]}")
        raise


def wait_for_service(max_wait: int = 15) -> bool:
    """等待服务就绪"""
    import time
    for _ in range(max_wait):
        try:
            req = urllib.request.Request(f"{BASE}/api/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


# ── 测试步骤 ──────────────────────────────────────────

def list_projects() -> list[dict]:
    """列出所有项目"""
    print("\n项目列表:")
    result = api("GET", "/api/rw/projects")
    projects = result["data"]
    if not projects:
        print("  (无项目)")
        return []
    for p in projects:
        pid = p.get("project_id", "?")
        name = p.get("name", "?")
        created = p.get("created_at", "?")[:19]
        print(f"  {pid}  {name}  ({created})")
    return projects


def resolve_project_id(project_id: str = "", project_name: str = "") -> str:
    """解析项目 ID，支持按名称查找"""
    if project_id:
        return project_id

    projects = list_projects()
    if not projects:
        print("\nERROR: 没有可删除的项目")
        sys.exit(1)

    matches = [p for p in projects if p.get("name") == project_name]
    if len(matches) == 0:
        print(f"\nERROR: 未找到名称为 \"{project_name}\" 的项目")
        sys.exit(1)
    if len(matches) > 1:
        print(f"\nERROR: 名称 \"{project_name}\" 匹配到多个项目，请使用 --id 指定")
        for p in matches:
            print(f"  {p['project_id']}  {p['name']}")
        sys.exit(1)

    return matches[0]["project_id"]


def show_project_detail(project_id: str) -> dict:
    """显示项目详情和论文统计"""
    try:
        result = api("GET", f"/api/rw/projects/{project_id}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"\nERROR: 项目不存在: {project_id}")
            print(f"  使用 --list 查看所有项目")
            sys.exit(1)
        raise
    project = result["data"]
    name = project.get("name", "?")
    created = project.get("created_at", "?")[:19]
    print(f"\n项目详情:")
    print(f"  ID:       {project_id}")
    print(f"  名称:     {name}")
    print(f"  创建时间: {created}")

    try:
        result = api("GET", f"/api/rw/projects/{project_id}/papers")
        papers = result["data"]
        has_pdf = sum(1 for p in papers if p.get("open_access", {}).get("pdf_url"))
        has_abs = sum(1 for p in papers if p.get("abstract"))
        print(f"  论文总数: {len(papers)}")
        print(f"  有 PDF:   {has_pdf}")
        print(f"  有摘要:   {has_abs}")
    except Exception:
        print(f"  论文总数: (无法获取)")

    return project


def delete_project(project_id: str) -> bool:
    """删除项目"""
    print(f"\n删除项目: {project_id}")
    try:
        result = api("DELETE", f"/api/rw/projects/{project_id}")
        data = result.get("data", {})
        papers_cleaned = data.get("papers_cleaned", 0)
        print(f"  -> 删除成功，清理了 {papers_cleaned} 篇论文的向量数据")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  -> 项目不存在 (404)")
        else:
            print(f"  -> 删除失败: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  -> 删除失败: {e}")
        return False


def verify_deleted(project_id: str) -> bool:
    """验证项目已被删除"""
    try:
        api("GET", f"/api/rw/projects/{project_id}")
        print(f"  验证: FAIL (项目仍存在)")
        return False
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  验证: PASS (项目已删除)")
            return True
        raise


# ── 主流程 ──────────────────────────────────────────

def run(
    project_id: str = "",
    project_name: str = "",
    force: bool = False,
) -> bool:
    """运行删除流程：查找 → 确认 → 删除 → 验证"""
    print("=" * 60)
    print("端到端测试: 删除项目")
    print("=" * 60)

    if not wait_for_service():
        print("ERROR: 服务未启动，请先运行 python -m src.service")
        return False
    print(f"服务就绪: {BASE}")

    try:
        # 步骤 1: 解析项目 ID
        print("\n[1/3] 查找项目...")
        target_id = resolve_project_id(project_id, project_name)

        # 步骤 2: 显示详情并确认
        show_project_detail(target_id)

        if not force:
            confirm = input("\n确认删除? (y/N): ").strip().lower()
            if confirm not in ("y", "yes"):
                print("已取消")
                return False

        # 步骤 3: 删除并验证
        print("\n[2/3] 删除项目...")
        ok = delete_project(target_id)

        if ok:
            print("\n[3/3] 验证删除...")
            ok = verify_deleted(target_id)

        print("\n" + "=" * 60)
        print(f"测试{'通过' if ok else '失败'}!")
        print("=" * 60)
        return ok

    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


# ── 入口 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="端到端测试: 删除指定项目")
    parser.add_argument("--id", default="", help="项目 ID")
    parser.add_argument("--name", default="", help="按名称查找项目（需唯一匹配）")
    parser.add_argument("--list", action="store_true", help="列出所有项目后退出")
    parser.add_argument("--force", action="store_true", help="跳过确认提示")
    args = parser.parse_args()

    if args.list:
        wait_for_service() or sys.exit(1)
        list_projects()
        sys.exit(0)

    if not args.id and not args.name:
        print("ERROR: 请指定 --id 或 --name")
        print("用法: python -m tests.e2e.test_delete_project --id <project_id>")
        print("      python -m tests.e2e.test_delete_project --name <project_name>")
        print("      python -m tests.e2e.test_delete_project --list")
        sys.exit(1)

    ok = run(
        project_id=args.id,
        project_name=args.name,
        force=args.force,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
