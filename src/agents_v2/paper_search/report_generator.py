"""报告生成Agent - 基于论文生成专业报告"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_qa_agent import BaseQAAgent
from .paper_search import Paper
from src.agents_v2.logging_config import get_logging_logger

logger = get_logging_logger(__name__)


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str
    citations: List[str] = field(default_factory=list)


@dataclass
class PaperReport:
    """论文报告"""
    summary: str = ""
    papers: List[Dict[str, Any]] = field(default_factory=list)
    comparisons: str = ""
    references: List[str] = field(default_factory=list)
    methodology_analysis: str = ""
    trends: str = ""
    limitations: str = ""
    future_directions: str = ""


class ReportGenerator(BaseQAAgent):
    """
    报告生成Agent

    输出格式：
    {
        "summary": "综合摘要",
        "papers": [
            {
                "title": "论文标题",
                "authors": "作者",
                "year": 年份,
                "key_contributions": ["贡献1", "贡献2"],
                "method": "方法概述",
                "results": "主要结果"
            }
        ],
        "comparisons": "对比分析",
        "references": ["参考文献列表"]
    }

    职责：
    1. 摘要提取 - 提炼每篇论文核心贡献
    2. 对比分析 - 比较不同论文的方法和结论
    3. 专业报告 - 生成结构化报告，含参考文献
    """

    def __init__(self):
        super().__init__(
            name="ReportGenerator",
            description="报告生成Agent - 基于论文生成专业报告"
        )
        self.system_prompt = """你是一个专业的学术报告生成助手。给你的任务是：
1. 分析论文的核心贡献和方法
2. 进行横向对比
3. 生成结构化的专业报告

请确保：
- 引用准确，使用标准学术引用格式
- 方法描述专业且准确
- 对比分析客观全面
"""

    async def execute(
        self,
        papers: List[Dict],
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成报告

        Args:
            papers: 论文列表（字典格式）
            question: 用户问题
            context: 上下文

        Returns:
            报告字典
        """
        self.logger.info(f"生成报告，共 {len(papers)} 篇论文")

        if not papers:
            return {
                "success": False,
                "error": "没有论文可供分析",
                "report": None
            }

        try:
            # 构建报告生成prompt
            prompt = self._build_report_prompt(papers, question)

            # 调用LLM生成报告
            report_content = await self._llm_call(prompt, self.system_prompt)

            # 解析报告
            report = self._parse_report(report_content, papers)

            self.logger.info("报告生成成功")

            return {
                "success": True,
                "report": report,
                "papers_count": len(papers),
                "references_count": len(report.get("references", []))
            }

        except Exception as e:
            self.logger.error(f"报告生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "report": None
            }

    def _build_report_prompt(self, papers: List[Dict], question: str) -> str:
        """构建报告生成prompt"""
        # 构建论文信息摘要
        papers_summary = []
        for i, paper in enumerate(papers):
            title = paper.get("title", "Unknown")
            authors = ", ".join(paper.get("authors", [])[:3])
            year = paper.get("year", "Unknown")
            abstract = paper.get("abstract", "")[:500]  # 限制长度
            methodology = paper.get("methodology", "")
            contributions = paper.get("key_contributions", [])

            papers_summary.append(f"""
论文 {i+1}: {title}
作者: {authors}
年份: {year}
摘要: {abstract}
方法: {methodology}
贡献: {contributions}
""")

        prompt = f"""请基于以下论文信息，针对问题「{question}」生成一份专业的学术报告。

## 用户问题
{question}

## 论文列表
{chr(10).join(papers_summary)}

## 报告要求

请生成结构化的报告，包含以下部分：

### 1. 综合摘要（200字以内）
概括这些论文的核心发现和回答

### 2. 论文详解
对每篇论文，说明：
- 核心贡献
- 使用的方法
- 主要结论

### 3. 方法对比
比较这些论文使用的方法有何异同

### 4. 研究趋势
从这些论文看出该领域的发展趋势

### 5. 局限性与未来方向
指出这些研究的局限性和值得探索的方向

### 6. 参考文献
列出所有论文的标准引用格式

请以JSON格式输出：
{{
    "summary": "综合摘要",
    "paper_details": [
        {{
            "title": "论文标题",
            "core_contribution": "核心贡献",
            "method": "方法",
            "conclusion": "结论"
        }}
    ],
    "comparisons": "方法对比分析",
    "trends": "研究趋势",
    "limitations": "局限性",
    "future_directions": "未来方向",
    "references": ["引用1", "引用2"]
}}
"""
        return prompt

    def _parse_report(self, llm_output: str, papers: List[Dict]) -> Dict[str, Any]:
        """解析LLM输出的报告"""
        import json

        try:
            # 尝试解析JSON
            report = json.loads(llm_output)
            return report

        except json.JSONError:
            # 降级处理：手动构建报告
            self.logger.warning("JSON解析失败，使用降级处理")
            return {
                "summary": llm_output[:500],
                "paper_details": [
                    {"title": p.get("title", ""), "core_contribution": "", "method": p.get("methodology", ""), "conclusion": ""}
                    for p in papers
                ],
                "comparisons": "见上述内容",
                "trends": "",
                "limitations": "",
                "future_directions": "",
                "references": self._generate_references(papers)
            }

    def _generate_references(self, papers: List[Dict]) -> List[str]:
        """生成参考文献列表"""
        refs = []
        for paper in papers:
            authors = paper.get("authors", [])
            author_str = authors[0] if authors else "Unknown"
            if len(authors) > 1:
                author_str += " et al."
            year = paper.get("year", "n.d.")
            title = paper.get("title", "Unknown")
            source = paper.get("source", "").upper()

            if source == "ARXIV":
                ref = f"{author_str} ({year}). {title}. arXiv preprint."
            elif source == "PUBMED":
                ref = f"{author_str} ({year}). {title}. PubMed."
            else:
                ref = f"{author_str} ({year}). {title}."

            refs.append(ref)

        return refs

    async def generate_from_paper_objects(
        self,
        papers: List[Paper],
        question: str
    ) -> Dict[str, Any]:
        """从Paper对象生成报告"""
        paper_dicts = [p.to_dict() for p in papers]
        return await self.execute(paper_dicts, question)

    def generate_batch_reports(
        self,
        paper_groups: Dict[str, List[Dict]],
        questions: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量生成报告

        适用于每日推送等场景，对不同主题分别生成报告
        """
        results = {}
        for topic, papers in paper_groups.items():
            question = questions.get(topic, topic)
            results[topic] = asyncio.run(self.execute(papers, question))

        return results