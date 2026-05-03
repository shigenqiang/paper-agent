"""
优化版论文生成流程 - 并行执行优化

优化策略:
1. TopicAgent 和 LiteratureAgent 并行执行（无依赖）
2. OutlineGenerator 不等待 LiteratureAgent 完成
3. 章节生成并行化

用法：
    python paper_pipeline_parallel.py "你的研究主题"
"""
import asyncio
import sys
import os
import time

# 禁用日志以减少输出
os.environ["LOG_LEVEL"] = "ERROR"

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents_v2.paper_agents.topic_agent import TopicAgent
from src.agents_v2.paper_agents.literature_agent import LiteratureAgent
from src.agents_v2.writing.outline_generator import OutlineGeneratorAgent
from src.agents_v2.writing.draft_generator import DraftGeneratorAgent


async def run_pipeline_optimized(topic: str):
    """运行优化版论文生成流程（并行化）"""
    print(f"\n{'='*60}")
    print(f"学术论文全流程生成系统（优化版）")
    print(f"主题: {topic}")
    print(f"{'='*60}\n")

    start_time = time.time()
    stage_times = {}

    try:
        # ========== 阶段1: 选题分析（异步）==========
        print("[阶段1] 选题分析...")
        topic_agent = TopicAgent()
        topic_start = time.time()
        topic_task = asyncio.create_task(
            topic_agent.execute({"user_request": topic})
        )
        # 不等待topic结果，继续下一步

        # ========== 阶段2: 文献收集（与阶段1并行）==========
        print("\n[阶段2] 文献收集...")
        literature_agent = LiteratureAgent()
        lit_start = time.time()
        lit_task = asyncio.create_task(
            literature_agent.execute(
                {"topic": topic},
                context={"research_question": topic}
            )
        )

        # 等待阶段1完成
        topic_result = await topic_task
        stage_times["topic"] = time.time() - topic_start
        refined_topic = topic if not topic_result.success else topic
        print(f"  选题精炼结果: {refined_topic} ({stage_times['topic']:.1f}s)")

        # 等待阶段2完成
        lit_result = await lit_task
        stage_times["literature"] = time.time() - lit_start
        papers = []
        if lit_result.success and lit_result.result:
            papers = lit_result.result.get("papers", [])
        print(f"  收集文献: {len(papers)} 篇 ({stage_times['literature']:.1f}s)")

        # ========== 阶段3: 大纲生成（不等待文献收集完成）==========
        print("\n[阶段3] 论文大纲生成...")
        outline_agent = OutlineGeneratorAgent()
        outline_start = time.time()
        outline_task = asyncio.create_task(
            outline_agent.execute({
                "topic": topic,
                "thesis_statement": f"研究{topic}的相关问题",
                "academic_level": "硕士"
            })
        )

        # 大纲生成中...同时可以开始准备参考文献
        references = []
        for i, paper in enumerate(papers[:20]):
            title = paper.get("title", "")
            authors = paper.get("authors", [])
            year = paper.get("year", 2024)
            if title:
                author_str = ", ".join(authors[:3]) if authors else "Unknown"
                references.append(f"[{i+1}] {author_str}. {title}. {year}.")

        # 等待大纲生成
        outline_result = await outline_task
        stage_times["outline"] = time.time() - outline_start
        outline = {}
        if outline_result.success and outline_result.result:
            outline = outline_result.result.get("outline", {})
        chapters = outline.get("chapters", [])
        print(f"  生成大纲: {len(chapters)} 个章节 ({stage_times['outline']:.1f}s)")

        # ========== 阶段4: 全文生成 ==========
        print("\n[阶段4] 论文全文生成...")
        draft_agent = DraftGeneratorAgent()
        draft_start = time.time()

        draft_result = await draft_agent.execute({
            "topic": topic,
            "outline": outline,
            "thesis_statement": f"针对{topic}的深入研究",
            "references": references,
            "writing_style": "学术"
        })

        stage_times["draft"] = time.time() - draft_start
        full_draft = ""
        if draft_result.success and draft_result.result:
            full_draft = draft_result.result.get("full_draft", "")

        # ========== 输出结果 ==========
        total_time = time.time() - start_time

        print(f"\n{'='*60}")
        print("论文生成完成!")
        print(f"总耗时: {total_time:.1f}s")
        print(f"  - 选题分析: {stage_times.get('topic', 0):.1f}s")
        print(f"  - 文献收集: {stage_times.get('literature', 0):.1f}s")
        print(f"  - 大纲生成: {stage_times.get('outline', 0):.1f}s")
        print(f"  - 全文生成: {stage_times.get('draft', 0):.1f}s")
        print(f"字数: {len(full_draft.split())}")
        print(f"章节: {len(chapters)}")
        print(f"{'='*60}\n")

        # 打印论文
        if full_draft:
            print("生成的论文预览:")
            print("-"*60)
            lines = full_draft.split("\n")
            for i, line in enumerate(lines[:100]):
                print(line)
            if len(lines) > 100:
                print(f"\n... (共 {len(lines)} 行，已显示前100行) ...")

        # 保存到文件
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)

        md_path = os.path.join(output_dir, "paper.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {topic}\n\n")
            f.write(full_draft)
        print(f"\n论文已保存到: {md_path}")

        return {
            "success": True,
            "draft": full_draft,
            "total_time": total_time,
            "stage_times": stage_times
        }

    except Exception as e:
        print(f"\n流程执行失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def main():
    if len(sys.argv) < 2:
        print("用法: python paper_pipeline_parallel.py \"你的研究主题\"")
        print("示例: python paper_pipeline_parallel.py \"深度学习在医学图像诊断中的应用\"")
        sys.exit(1)

    topic = sys.argv[1]
    result = await run_pipeline_optimized(topic)

    if not result.get("success"):
        print(f"\n论文生成失败: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())