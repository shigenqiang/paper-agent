"""隔离子Agent - 每篇论文独立处理"""
import os
import json
import logging
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field
from langchain_community.document_loaders import UnstructuredPDFLoader

from src.core.model import llm
from src.core.prompt import read_analyse_prompt

logger = logging.getLogger(__name__)


class PaperAnalysisResult(BaseModel):
    """单篇论文的分析结果"""
    paper_id: str
    title: Optional[str] = None
    core_problem: Optional[str] = None
    key_methodology_name: Optional[str] = None
    key_methodology_principle: Optional[str] = None
    key_methodology_novelty: Optional[str] = None
    datasets_used: List[str] = Field(default_factory=list)
    evaluation_metrics: List[str] = Field(default_factory=list)
    main_results: Optional[str] = None
    limitations: Optional[str] = None
    contributions: List[str] = Field(default_factory=list)
    summary: Optional[str] = None  # 300字压缩摘要
    error: Optional[str] = None


class IsolatedPaperReader:
    """
    独立上下文的论文阅读器

    每篇论文单独处理，避免context污染。
    主要功能：
    1. 下载/读取PDF
    2. 解析论文结构
    3. 提取结构化信息
    4. 生成压缩摘要
    """

    def __init__(
        self,
        download_dir: str = "./downloads",
        max_section_chars: int = 4000  # 每节最大字符数
    ):
        self.download_dir = download_dir
        self.max_section_chars = max_section_chars
        os.makedirs(download_dir, exist_ok=True)

    async def read_paper(
        self,
        paper: Dict[str, Any],
        mcp_tools: List[Any] = None
    ) -> PaperAnalysisResult:
        """
        独立阅读单篇论文

        Args:
            paper: 论文元数据（包含 paper_id, title, pdf_url 等）
            mcp_tools: MCP工具列表（用于下载）

        Returns:
            PaperAnalysisResult: 结构化分析结果
        """
        paper_id = paper.get("paper_id", "")
        title = paper.get("title", "Unknown")

        logger.info(f"Reading paper: {paper_id} - {title}")

        try:
            # 1. 下载PDF（如果需要）
            pdf_path = await self._download_pdf(paper, mcp_tools)
            if not pdf_path:
                return PaperAnalysisResult(
                    paper_id=paper_id,
                    title=title,
                    error="PDF下载失败"
                )

            # 2. 解析PDF
            sections = self._parse_pdf(pdf_path)
            if not sections:
                return PaperAnalysisResult(
                    paper_id=paper_id,
                    title=title,
                    error="PDF解析失败"
                )

            # 3. 提取结构化数据
            extraction = await self._extract_structured_data(
                title=title,
                abstract=sections.get("abstract", ""),
                method=sections.get("method", ""),
                results=sections.get("results", ""),
                conclusion=sections.get("conclusion", "")
            )

            # 4. 生成压缩摘要
            summary = await self._generate_summary(title, extraction)

            return PaperAnalysisResult(
                paper_id=paper_id,
                title=title,
                core_problem=extraction.get("core_problem"),
                key_methodology_name=extraction.get("key_methodology_name"),
                key_methodology_principle=extraction.get("key_methodology_principle"),
                key_methodology_novelty=extraction.get("key_methodology_novelty"),
                datasets_used=extraction.get("datasets_used", []),
                evaluation_metrics=extraction.get("evaluation_metrics", []),
                main_results=extraction.get("main_results"),
                limitations=extraction.get("limitations"),
                contributions=extraction.get("contributions", []),
                summary=summary
            )

        except Exception as e:
            logger.error(f"Error reading paper {paper_id}: {e}")
            return PaperAnalysisResult(
                paper_id=paper_id,
                title=title,
                error=str(e)
            )

    async def _download_pdf(
        self,
        paper: Dict[str, Any],
        mcp_tools: List[Any] = None
    ) -> Optional[str]:
        """下载PDF到本地"""
        paper_id = paper.get("paper_id", "")
        pdf_url = paper.get("pdf_url")

        if not pdf_url:
            # 尝试使用 paper_id 构造 URL
            if paper.get("source") == "arxiv":
                pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"

        if not pdf_url:
            return None

        # 构建保存路径
        safe_id = paper_id.replace("/", "_").replace("\\", "_")
        pdf_path = os.path.join(self.download_dir, f"{safe_id}.pdf")

        # 如果已经存在，直接返回
        if os.path.exists(pdf_path):
            return pdf_path

        # TODO: 使用 MCP 工具下载
        # 目前先跳过下载，假设PDF已经存在
        if os.path.exists(pdf_path):
            return pdf_path

        return None

    def _parse_pdf(self, pdf_path: str) -> Dict[str, str]:
        """解析PDF为结构化节"""
        try:
            loader = UnstructuredPDFLoader(pdf_path, strategy="hi_res", mode="elements")
            documents = loader.load()

            sections = {
                "abstract": "",
                "method": "",
                "results": "",
                "conclusion": "",
                "introduction": ""
            }

            current_section = "abstract"
            section_keywords = {
                "abstract": ["abstract", "summary"],
                "introduction": ["introduction", "1.", "背景"],
                "method": ["method", "methodology", "approach", "2.", "方法"],
                "results": ["result", "experiment", "evaluation", "3.", "结果"],
                "conclusion": ["conclusion", "discussion", "4.", "总结", "conclude"]
            }

            for doc in documents:
                content = doc.page_content
                content_lower = content.lower()

                # 检测当前内容属于哪个节
                for section_name, keywords in section_keywords.items():
                    if any(kw in content_lower for kw in keywords):
                        current_section = section_name
                        break

                # 累加到当前节
                sections[current_section] += " " + content

            # 截断每节防止溢出
            for section in sections:
                if len(sections[section]) > self.max_section_chars:
                    sections[section] = sections[section][:self.max_section_chars] + "..."

            return sections

        except Exception as e:
            logger.error(f"PDF parsing error for {pdf_path}: {e}")
            return {}

    async def _extract_structured_data(
        self,
        title: str,
        abstract: str,
        method: str,
        results: str,
        conclusion: str
    ) -> Dict[str, Any]:
        """从论文节中提取结构化数据"""
        prompt = f"""请从以下论文信息中提取结构化数据。

论文标题：{title}

摘要：
 abstract}

方法：
{method}

结果：
{results}

结论：
{conclusion}

请以JSON格式返回以下字段：
- core_problem: 核心问题（用"尽管...但..."或"为了..."句式）
- key_methodology_name: 关键方法名称
- key_methodology_principle: 方法原理（1-2句话）
- key_methodology_novelty: 创新点
- datasets_used: 使用的数据集列表
- evaluation_metrics: 评估指标列表
- main_results: 主要结果（带数值）
- limitations: 局限性
- contributions: 贡献列表（3-5条）

只返回JSON，不要其他内容。"""

        try:
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # 提取JSON
            json_str = self._extract_json(content)
            return json.loads(json_str)

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {}

    async def _generate_summary(
        self,
        title: str,
        extraction: Dict[str, Any]
    ) -> str:
        """生成300字压缩摘要"""
        prompt = f"""请为以下论文生成300字的中文摘要。

论文标题：{title}

核心问题：{extraction.get('core_problem', 'N/A')}
方法：{extraction.get('key_methodology_name', 'N/A')}
主要结果：{extraction.get('main_results', 'N/A')}

摘要应包含：
1. 研究问题
2. 主要方法
3. 关键结果
4. 主要贡献

请用中文生成约300字的摘要。"""

        try:
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()[:500]  # 限制500字符

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return ""

    def _extract_json(self, content: str) -> str:
        """从响应中提取JSON"""
        content = content.strip()

        if "```json" in content:
            parts = content.split("```json")
            if len(parts) > 1:
                content = parts[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            if len(parts) > 1:
                content = parts[1]

        if not content.startswith("{"):
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                content = content[start:end]

        return content


async def reading_pipeline(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    并行阅读管道 - 使用隔离子Agent处理多篇论文

    避免20+论文塞爆context的问题。
    """
    papers = state.get("papers", [])
    if not papers:
        return state

    logger.info(f"Starting reading pipeline for {len(papers)} papers")

    # 创建隔离子Reader
    reader = IsolatedPaperReader()

    # 并行处理所有论文（每个论文独立上下文）
    import asyncio
    results = await asyncio.gather(
        *[reader.read_paper(paper) for paper in papers],
        return_exceptions=True
    )

    # 收集成功的分析结果
    analyses = []
    failed_count = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Paper {i} failed: {result}")
            failed_count += 1
        elif isinstance(result, PaperAnalysisResult):
            if result.error:
                logger.warning(f"Paper {result.paper_id} error: {result.error}")
                failed_count += 1
            else:
                analyses.append(result)

    logger.info(f"Reading pipeline completed: {len(analyses)} successful, {failed_count} failed")

    # 更新状态
    state["paper_analyses"] = [a.model_dump() for a in analyses]
    state["failed_papers"] = failed_count

    return state