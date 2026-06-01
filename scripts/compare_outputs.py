"""对比 pymupdf4llm vs Docling 的输出质量"""
import pymupdf4llm
import time

COMPARE_PDFS = [
    ("bert.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/test_pdfs/bert.pdf"),
    ("paper_85306019.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/files/test_search_to_pdf/paper_85306019.pdf"),
    ("paper_cc3f2153.pdf", "D:/pycharmprojects/pythonProject1/data/research_workspace/files/proj_673ac013/paper_cc3f2153.pdf"),
]

def main():
    for name, path in COMPARE_PDFS:
        print(f"\n{'='*80}")
        print(f"PDF: {name}")
        print(f"{'='*80}")

        # pymupdf4llm 全文
        t0 = time.time()
        md = pymupdf4llm.to_markdown(path)
        t1 = time.time()
        print(f"\n[pymupdf4llm] {len(md)} chars, {t1-t0:.2f}s")
        print(f"--- 前 3000 字符 ---")
        print(md[:3000])
        print(f"\n--- 后 1500 字符 ---")
        print(md[-1500:])

if __name__ == "__main__":
    main()
