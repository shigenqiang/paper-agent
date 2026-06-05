"""端到端测试：验证搜索排序 — 摘要权重 > 标题权重

运行方式（需先启动服务）:
    python -m tests.e2e.test_ranking
    # 或
    python tests/e2e/test_ranking.py

可选参数:
    --query "your query"     搜索关键词（默认: sparse functional data）
    --limit 20               搜索数量（默认: 20）
    --sources openalex,arxiv  搜索源（默认: openalex,arxiv,semantic_scholar）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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


# ── 检查逻辑 ──────────────────────────────────────────

def check_abstract_relevance(results: list[dict], query: str) -> tuple[int, int, list[str]]:
    """检查搜索结果中摘要与查询的相关性

    返回: (相关论文数, 总数, 问题列表)
    """
    query_terms = set(query.lower().split())
    issues = []

    relevant = 0
    for i, r in enumerate(results):
        title = r.get("title", "")
        abstract = r.get("abstract", "")
        score = r.get("dense_score", 0)

        # 检查摘要是否包含查询词
        abstract_lower = abstract.lower() if abstract else ""
        title_lower = title.lower()

        abstract_matches = sum(1 for t in query_terms if t in abstract_lower)
        title_matches = sum(1 for t in query_terms if t in title_lower)

        # 摘要匹配度 ≥ 50% 查询词才算相关
        if abstract_matches >= len(query_terms) * 0.5:
            relevant += 1
        else:
            if title_matches > 0 and abstract_matches == 0:
                issues.append(
                    f"  [{i+1:2d}] 标题匹配但摘要无关 [{score:.3f}]: {title[:55]}"
                )
            elif abstract_matches < len(query_terms) * 0.3:
                issues.append(
                    f"  [{i+1:2d}] 摘要相关度低 ({abstract_matches}/{len(query_terms)}) [{score:.3f}]: {title[:55]}"
                )

    return relevant, len(results), issues


def check_score_ordering(results: list[dict]) -> list[str]:
    """检查分数是否降序排列"""
    issues = []
    for i in range(len(results) - 1):
        s1 = results[i].get("dense_score", 0)
        s2 = results[i + 1].get("dense_score", 0)
        if s1 < s2:
            issues.append(f"  排序错误: [{i+1}] {s1:.3f} < [{i+2}] {s2:.3f}")
    return issues


def show_top_results(results: list[dict], n: int = 10) -> None:
    """显示前 N 个结果"""
    print(f"\n前 {min(n, len(results))} 个结果:")
    print("-" * 80)
    for i, r in enumerate(results[:n]):
        title = r.get("title", "?")[:60]
        score = r.get("dense_score", 0)
        rel = r.get("relevance_score", 0)
        qual = r.get("quality_score", 0)
        abstract = r.get("abstract", "")
        has_abs = f"{len(abstract)}字" if abstract else "无摘要"
        print(f"  {i+1:2d}. [{score:.3f}] rel={rel:.3f} qual={qual:.3f} | {title}")
        print(f"      摘要: {has_abs}")


# ── 主流程 ──────────────────────────────────────────

def run(
    query: str = "sparse functional data",
    limit: int = 20,
    sources: list[str] | None = None,
) -> bool:
    """运行排序验证测试"""
    if sources is None:
        sources = ["openalex", "arxiv", "semantic_scholar"]

    print("=" * 60)
    print("端到端测试: 搜索排序验证")
    print("=" * 60)

    if not wait_for_service():
        print("ERROR: 服务未启动，请先运行 python -m src.service")
        return False
    print(f"服务就绪: {BASE}")

    # 创建临时项目
    print(f"\n[1/4] 创建临时项目...")
    project_name = f"ranking_test_{int(time.time())}"
    result = api("POST", "/api/rw/projects", {"name": project_name})
    project_id = result["data"]["project_id"]
    print(f"  -> {project_id}")

    try:
        # 搜索
        print(f"\n[2/4] 搜索: \"{query}\"")
        print(f"  sources={sources}, limit={limit}")
        body = {"query": query, "sources": sources, "limit": limit}
        result = api("POST", f"/api/rw/projects/{project_id}/papers/search", body)
        data = result["data"]
        results = data["results"]
        print(f"  -> 找到 {len(results)} 篇")

        if not results:
            print("\nERROR: 搜索结果为空")
            return False

        # 显示结果
        show_top_results(results, 10)

        # 检查 1: 分数降序
        print(f"\n[3/4] 检查分数排序...")
        ordering_issues = check_score_ordering(results)
        if ordering_issues:
            print(f"  FAIL: 排序问题:")
            for issue in ordering_issues:
                print(f"    {issue}")
        else:
            print(f"  PASS: 分数降序正确")

        # 检查 2: 摘要相关性
        print(f"\n[4/4] 检查摘要相关性...")
        relevant, total, rel_issues = check_abstract_relevance(results, query)
        ratio = relevant / total if total else 0
        print(f"  相关论文: {relevant}/{total} ({ratio:.0%})")

        if rel_issues:
            print(f"  问题论文:")
            for issue in rel_issues[:10]:
                print(f"    {issue}")

        # 判断通过条件
        ok = len(ordering_issues) == 0 and ratio >= 0.5

        # 清理
        print(f"\n清理临时项目...")
        api("DELETE", f"/api/rw/projects/{project_id}")

        print("\n" + "=" * 60)
        print(f"测试{'通过' if ok else '失败'}!")
        print(f"  排序: {'PASS' if not ordering_issues else 'FAIL'}")
        print(f"  相关性: {relevant}/{total} ({ratio:.0%}) {'PASS' if ratio >= 0.5 else 'FAIL'}")
        print("=" * 60)
        return ok

    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        # 清理
        try:
            api("DELETE", f"/api/rw/projects/{project_id}")
        except Exception:
            pass
        return False


# ── 入口 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="端到端测试: 搜索排序验证")
    parser.add_argument("--query", default="sparse functional data", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=20, help="搜索数量")
    parser.add_argument("--sources", default="openalex,arxiv,semantic_scholar", help="搜索源")
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",")]
    ok = run(query=args.query, limit=args.limit, sources=sources)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
