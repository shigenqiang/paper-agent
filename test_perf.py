"""测试论文生成各阶段耗时"""
import time
import asyncio
import os

os.environ["LOG_LEVEL"] = "ERROR"

from src.agents_v2.paper_agents.topic_agent import TopicAgent
from src.agents_v2.paper_agents.literature_agent import LiteratureAgent
from src.agents_v2.writing.outline_generator import OutlineGeneratorAgent
from src.agents_v2.writing.draft_generator import DraftGeneratorAgent

async def test_topic():
    """测试TopicAgent"""
    agent = TopicAgent()
    start = time.time()
    result = await agent.execute({"user_request": "deep learning medical image diagnosis"})
    elapsed = time.time() - start
    print(f"[1] TopicAgent: {elapsed:.1f}s, success={result.success}")
    return elapsed

async def test_literature(topic="deep learning medical image diagnosis"):
    """测试LiteratureAgent"""
    agent = LiteratureAgent()
    start = time.time()
    result = await agent.execute(
        {"topic": topic},
        context={"research_question": topic}
    )
    elapsed = time.time() - start
    papers = result.result.get("papers", []) if result.success else []
    print(f"[2] LiteratureAgent: {elapsed:.1f}s, success={result.success}, papers={len(papers)}")
    return elapsed, papers

async def test_outline(topic="deep learning medical image diagnosis"):
    """测试OutlineGeneratorAgent"""
    agent = OutlineGeneratorAgent()
    start = time.time()
    result = await agent.execute({
        "topic": topic,
        "thesis_statement": f"Research on {topic}",
        "academic_level": "硕士"
    })
    elapsed = time.time() - start
    outline = result.result.get("outline", {}) if result.success else {}
    chapters = outline.get("chapters", [])
    print(f"[3] OutlineGeneratorAgent: {elapsed:.1f}s, success={result.success}, chapters={len(chapters)}")
    return elapsed, outline

async def test_draft(topic="deep learning medical image diagnosis", outline=None, papers=None):
    """测试DraftGeneratorAgent"""
    agent = DraftGeneratorAgent()
    references = []
    if papers:
        for i, paper in enumerate(papers[:20]):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", 2024)
            if title:
                author_str = ", ".join(authors[:3]) if authors else "Unknown"
                references.append(f"[{i+1}] {author_str}. {title}. {year}.")

    start = time.time()
    result = await agent.execute({
        "topic": topic,
        "outline": outline or {},
        "thesis_statement": f"Research on {topic}",
        "references": references,
        "writing_style": "学术"
    })
    elapsed = time.time() - start
    full_draft = result.result.get("full_draft", "") if result.success else ""
    print(f"[4] DraftGeneratorAgent: {elapsed:.1f}s, success={result.success}, words={len(full_draft.split())}")
    return elapsed

async def main():
    print("=" * 60)
    print("论文生成流程性能测试")
    print("=" * 60)

    times = {}

    # 测试各阶段
    times["topic"] = await test_topic()
    times["literature"], papers = await test_literature()
    times["outline"], outline = await test_outline()
    times["draft"] = await test_draft(outline=outline, papers=papers)

    print("\n" + "=" * 60)
    print("性能汇总:")
    total = sum(times.values())
    for stage, t in times.items():
        pct = t / total * 100
        print(f"  {stage}: {t:.1f}s ({pct:.1f}%)")
    print(f"  总计: {total:.1f}s")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())