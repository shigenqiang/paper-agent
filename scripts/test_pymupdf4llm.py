"""pymupdf4llm 解析器测试 — 与 Docling 对比"""
import time
import json
from pathlib import Path

import pymupdf4llm


PDFS = [
    ("sample_paper.pdf", "D:/pycharmprojects/pythonProject1/tests/agents_v3/research_workspace/fixtures/sample_paper.pdf"),
    ("attention_is_all_you_need.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/test_pdfs/attention_is_all_you_need.pdf"),
    ("bert.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/test_pdfs/bert.pdf"),
    ("sparse_functional_data.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/test_pdfs/sparse_functional_data.pdf"),
    ("paper_8164fcee.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/files/test_search_to_pdf/paper_8164fcee.pdf"),
    ("paper_85306019.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/files/test_search_to_pdf/paper_85306019.pdf"),
    ("paper_17ae8232.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/files/proj_673ac013/paper_17ae8232.pdf"),
    ("paper_2afd8414.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/files/proj_673ac013/paper_2afd8414.pdf"),
    ("paper_6c775e70.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/files/proj_673ac013/paper_6c775e70.pdf"),
    ("paper_cc3f2153.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/files/proj_673ac013/paper_cc3f2153.pdf"),
]


def test_single(name: str, path: str) -> dict:
    result = {"name": name, "path": path, "status": "success"}
    try:
        t0 = time.time()
        md_text = pymupdf4llm.to_markdown(path)
        elapsed = time.time() - t0

        # 统计
        char_count = len(md_text)
        word_count = len(md_text.split())
        # 粗略检测章节：以 # 开头的行
        lines = md_text.split("\n")
        sections = [l.strip() for l in lines if l.strip().startswith("#")]

        result["char_count"] = char_count
        result["word_count"] = word_count
        result["section_count"] = len(sections)
        result["elapsed_s"] = round(elapsed, 2)
        result["sections"] = sections[:20]
        result["preview"] = md_text[:500]

        # 内容特征检测
        lower = md_text.lower()
        result["has_abstract"] = "abstract" in lower
        result["has_references"] = "references" in lower or "bibliography" in lower
        result["has_table"] = "|" in md_text and "---" in md_text

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)

    return result


def main():
    results = []
    total_chars = 0
    total_sections = 0
    total_time = 0
    success = 0
    failed = 0

    for name, path in PDFS:
        print(f"Testing {name}...")
        r = test_single(name, path)
        results.append(r)
        if r["status"] == "success":
            success += 1
            total_chars += r["char_count"]
            total_sections += r["section_count"]
            total_time += r["elapsed_s"]
            print(f"  OK  {r['char_count']} chars, {r['section_count']} sections, {r['elapsed_s']}s")
        else:
            failed += 1
            print(f"  FAIL: {r.get('error', 'unknown')}")

    # 汇总
    summary = {
        "total_pdfs": len(PDFS),
        "success": success,
        "failed": failed,
        "total_chars": total_chars,
        "total_sections": total_sections,
        "total_time_s": round(total_time, 2),
        "avg_chars": round(total_chars / max(success, 1)),
        "avg_sections": round(total_sections / max(success, 1), 1),
        "avg_time_s": round(total_time / max(success, 1), 2),
    }

    output = {"summary": summary, "results": results}

    out_path = Path("D:/pycharmprojects/pythonProject1/docs/test_results/04-PDF解析与分块/pymupdf4llm-test-report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n=== Summary ===")
    print(f"Success: {success}/{len(PDFS)}")
    print(f"Total chars: {total_chars}")
    print(f"Avg chars/PDF: {summary['avg_chars']}")
    print(f"Avg sections/PDF: {summary['avg_sections']}")
    print(f"Avg time/PDF: {summary['avg_time_s']}s")
    print(f"Total time: {summary['total_time_s']}s")
    print(f"\nSaved to: {out_path}")


if __name__ == "__main__":
    main()
