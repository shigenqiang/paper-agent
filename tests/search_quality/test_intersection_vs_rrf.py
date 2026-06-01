"""双路交集 vs RRF 排名融合 对比测试

测试场景：
1. 正常情况：两路都有共同结果
2. 偏科情况：某些论文只在一路排名高
3. 无交集：两路结果完全不重叠
4. 完全重叠：两路结果完全一致
5. 不同 top_k 对交集大小的影响

输出：对比报告（结果数、排序差异、过滤效果）
"""

import random
from dataclasses import dataclass, field


@dataclass
class SimulatedPaper:
    paper_id: str
    dense_score: float  # 语义相似度（模拟 cosine similarity）
    sparse_score: float  # 关键词匹配（模拟 BM25）


@dataclass
class SearchResult:
    paper_id: str
    score: float
    method: str  # "rrf" or "intersection"
    dense_rank: int = -1
    sparse_rank: int = -1


def generate_papers(n: int = 20, seed: int = 42) -> dict[str, SimulatedPaper]:
    """生成模拟论文数据"""
    random.seed(seed)
    papers = {}
    for i in range(n):
        papers[f"paper_{i}"] = SimulatedPaper(
            paper_id=f"paper_{i}",
            dense_score=random.random(),
            sparse_score=random.random(),
        )
    return papers


def get_top_k(papers: dict[str, SimulatedPaper], key: str, top_k: int) -> list[tuple[str, float]]:
    """按指定维度取 top-K"""
    sorted_papers = sorted(papers.items(), key=lambda x: getattr(x[1], key), reverse=True)
    return [(p.paper_id, getattr(p, key)) for p_id, p in sorted_papers[:top_k]]


def rrf_fusion(
    dense_sorted: list[tuple[str, float]],
    sparse_sorted: list[tuple[str, float]],
    k: int = 60,
) -> list[SearchResult]:
    """RRF 排名融合

    公式: score(d) = Σ 1/(k + rank_i(d))
    """
    rrf_scores: dict[str, float] = {}
    dense_rank_map: dict[str, int] = {}
    sparse_rank_map: dict[str, int] = {}

    for rank, (pid, _) in enumerate(dense_sorted):
        rrf_scores[pid] = rrf_scores.get(pid, 0) + 1 / (k + rank + 1)
        dense_rank_map[pid] = rank

    for rank, (pid, _) in enumerate(sparse_sorted):
        rrf_scores[pid] = rrf_scores.get(pid, 0) + 1 / (k + rank + 1)
        sparse_rank_map[pid] = rank

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [
        SearchResult(
            paper_id=pid,
            score=score,
            method="rrf",
            dense_rank=dense_rank_map.get(pid, -1),
            sparse_rank=sparse_rank_map.get(pid, -1),
        )
        for pid, score in ranked
    ]


def intersection_fusion(
    dense_sorted: list[tuple[str, float]],
    sparse_sorted: list[tuple[str, float]],
    top_k: int,
) -> list[SearchResult]:
    """双路交集融合

    取 dense top-K 和 sparse top-K 的交集，
    交集内按两路排名之和排序（排名越小越好）。
    """
    dense_rank: dict[str, int] = {pid: rank for rank, (pid, _) in enumerate(dense_sorted)}
    sparse_rank: dict[str, int] = {pid: rank for rank, (pid, _) in enumerate(sparse_sorted)}

    inter = set(dense_rank.keys()) & set(sparse_rank.keys())

    scored = []
    for pid in inter:
        combined = dense_rank[pid] + sparse_rank[pid]
        score = 1.0 - combined / (top_k * 2)
        scored.append(SearchResult(
            paper_id=pid,
            score=score,
            method="intersection",
            dense_rank=dense_rank[pid],
            sparse_rank=sparse_rank[pid],
        ))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


def set_paper(papers: dict[str, SimulatedPaper], pid: str, dense: float, sparse: float):
    """设置特定论文的分数"""
    papers[pid].dense_score = dense
    papers[pid].sparse_score = sparse


def run_scenario(
    name: str,
    description: str,
    papers: dict[str, SimulatedPaper],
    top_k: int = 10,
    k_rrf: int = 60,
) -> dict:
    """运行一个测试场景，返回结果"""
    dense_sorted = get_top_k(papers, "dense_score", top_k)
    sparse_sorted = get_top_k(papers, "sparse_score", top_k)

    rrf_results = rrf_fusion(dense_sorted, sparse_sorted, k_rrf)
    int_results = intersection_fusion(dense_sorted, sparse_sorted, top_k)

    dense_set = {pid for pid, _ in dense_sorted}
    sparse_set = {pid for pid, _ in sparse_sorted}
    inter_set = {r.paper_id for r in int_results}
    rrf_set = {r.paper_id for r in rrf_results}

    only_dense = dense_set - sparse_set
    only_sparse = sparse_set - dense_set

    return {
        "name": name,
        "description": description,
        "top_k": top_k,
        "dense_top": [pid for pid, _ in dense_sorted],
        "sparse_top": [pid for pid, _ in sparse_sorted],
        "rrf_results": rrf_results,
        "int_results": int_results,
        "rrf_count": len(rrf_results),
        "int_count": len(int_results),
        "only_dense": sorted(only_dense),
        "only_sparse": sorted(only_sparse),
        "intersection_set": sorted(inter_set),
        "rrf_filtered_out": sorted(rrf_set - inter_set),
        "int_filtered_out": sorted(inter_set - rrf_set),
    }


def print_scenario(result: dict):
    """打印场景结果"""
    name = result["name"]
    desc = result["description"]

    print()
    print("=" * 72)
    print(f"  {name}: {desc}")
    print("=" * 72)

    print(f"\n  top_k = {result['top_k']}")
    print(f"  Dense  top-{result['top_k']}: {result['dense_top']}")
    print(f"  Sparse top-{result['top_k']}: {result['sparse_top']}")

    print(f"\n  --- RRF ({result['rrf_count']} papers) ---")
    for i, r in enumerate(result["rrf_results"]):
        tag = ""
        if r.paper_id in result["only_dense"]:
            tag = " [dense-only]"
        elif r.paper_id in result["only_sparse"]:
            tag = " [sparse-only]"
        print(f"    {i+1:2d}. {r.paper_id:12s}  rrf={r.score:.6f}  d_rank={r.dense_rank:2d}  s_rank={r.sparse_rank:2d}{tag}")

    print(f"\n  --- Intersection ({result['int_count']} papers) ---")
    for i, r in enumerate(result["int_results"]):
        print(f"    {i+1:2d}. {r.paper_id:12s}  score={r.score:.4f}  d_rank={r.dense_rank:2d}  s_rank={r.sparse_rank:2d}")

    print(f"\n  --- Diff ---")
    print(f"  Only in Dense  top-{result['top_k']}: {result['only_dense']}")
    print(f"  Only in Sparse top-{result['top_k']}: {result['only_sparse']}")
    print(f"  Intersection set:               {result['intersection_set']}")
    print(f"  RRF keeps but intersection drops: {result['rrf_filtered_out']}")
    print(f"  Intersection keeps but RRF drops: {result['int_filtered_out']}")


def print_summary(results: list[dict]):
    """打印总结对比表"""
    print()
    print("=" * 72)
    print("  SUMMARY")
    print("=" * 72)
    print()
    print(f"  {'Scenario':<35s} {'RRF':>5s} {'Int':>5s} {'RRF-only':>10s} {'Int-only':>10s}")
    print(f"  {'-'*35} {'-'*5} {'-'*5} {'-'*10} {'-'*10}")
    for r in results:
        print(f"  {r['name']:<35s} {r['rrf_count']:>5d} {r['int_count']:>5d} {len(r['rrf_filtered_out']):>10d} {len(r['int_filtered_out']):>10d}")

    print()
    print("  Conclusions:")
    print("  - RRF: inclusive, keeps papers matching in ANY dimension")
    print("  - Intersection: strict, keeps papers matching in BOTH dimensions")
    print("  - RRF has higher recall, Intersection has higher precision")
    print("  - When intersection is empty, fallback to dense-only is needed")


def main():
    papers = generate_papers(20)
    results = []

    # ── Scenario 1: Normal (some overlap) ──
    p = generate_papers(20, seed=42)
    set_paper(p, "paper_0",  dense=0.95, sparse=0.30)
    set_paper(p, "paper_3",  dense=0.20, sparse=0.92)
    set_paper(p, "paper_5",  dense=0.88, sparse=0.15)
    set_paper(p, "paper_7",  dense=0.10, sparse=0.89)
    set_paper(p, "paper_10", dense=0.75, sparse=0.70)
    r = run_scenario("Scenario 1: Normal", "Some papers rank high in one dimension only", p)
    results.append(r)
    print_scenario(r)

    # ── Scenario 2: Heavy bias (dense and sparse disagree) ──
    p = generate_papers(20, seed=99)
    # Force completely different top-K for dense vs sparse
    for i in range(20):
        if i < 10:
            p[f"paper_{i}"].dense_score = 0.9 - i * 0.05
            p[f"paper_{i}"].sparse_score = 0.1 + i * 0.01
        else:
            p[f"paper_{i}"].dense_score = 0.1 + (i - 10) * 0.01
            p[f"paper_{i}"].sparse_score = 0.9 - (i - 10) * 0.05
    r = run_scenario("Scenario 2: Heavy bias", "Dense and sparse disagree completely", p)
    results.append(r)
    print_scenario(r)

    # ── Scenario 3: No intersection ──
    p = generate_papers(20, seed=77)
    for i in range(20):
        if i < 10:
            p[f"paper_{i}"].dense_score = 0.9 - i * 0.05
            p[f"paper_{i}"].sparse_score = 0.01
        else:
            p[f"paper_{i}"].dense_score = 0.01
            p[f"paper_{i}"].sparse_score = 0.9 - (i - 10) * 0.05
    r = run_scenario("Scenario 3: No intersection", "Dense and sparse top-K have zero overlap", p, top_k=10)
    results.append(r)
    print_scenario(r)

    # ── Scenario 4: Perfect overlap ──
    p = generate_papers(20, seed=55)
    for i in range(20):
        score = 0.95 - i * 0.04
        p[f"paper_{i}"].dense_score = score
        p[f"paper_{i}"].sparse_score = score
    r = run_scenario("Scenario 4: Perfect overlap", "Dense and sparse agree completely", p)
    results.append(r)
    print_scenario(r)

    # ── Scenario 5: Different top_k values ──
    p = generate_papers(50, seed=42)
    set_paper(p, "paper_0",  dense=0.95, sparse=0.30)
    set_paper(p, "paper_3",  dense=0.20, sparse=0.92)
    set_paper(p, "paper_10", dense=0.75, sparse=0.70)

    print()
    print("=" * 72)
    print("  Scenario 5: top_k sensitivity (50 papers)")
    print("=" * 72)
    dense_sorted_full = get_top_k(p, "dense_score", 50)
    sparse_sorted_full = get_top_k(p, "sparse_score", 50)

    print(f"\n  {'top_k':>6s}  {'RRF':>5s}  {'Int':>5s}  {'Int/RRF':>8s}  {'RRF-only':>10s}")
    print(f"  {'-'*6}  {'-'*5}  {'-'*5}  {'-'*8}  {'-'*10}")
    for tk in [5, 10, 15, 20, 30, 50]:
        dense_top = dense_sorted_full[:tk]
        sparse_top = sparse_sorted_full[:tk]
        rrf = rrf_fusion(dense_top, sparse_top)
        inter = intersection_fusion(dense_top, sparse_top, tk)
        rrf_set = {r.paper_id for r in rrf}
        inter_set = {r.paper_id for r in inter}
        ratio = len(inter) / len(rrf) if rrf else 0
        rrf_only = len(rrf_set - inter_set)
        print(f"  {tk:>6d}  {len(rrf):>5d}  {len(inter):>5d}  {ratio:>7.1%}  {rrf_only:>10d}")

    # ── Final summary ──
    print_summary(results)

    print()
    print("=" * 72)
    print("  Recommendation for paper search:")
    print("=" * 72)
    print("""
  Use INTERSECTION when:
    - Paper library is large (>100 papers)
    - Precision matters more than recall
    - You want to filter out noise from single-dimension matches

  Use RRF when:
    - Paper library is small (<50 papers)
    - Recall matters more (don't want to miss relevant papers)
    - You want a single ranked list without hard cutoffs

  Current implementation:
    - Intersection with dense-only fallback (best of both worlds)
    - Strict filtering when overlap exists
    - Graceful degradation when no overlap
""")


if __name__ == "__main__":
    main()
