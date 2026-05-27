"""
Workflow orchestrator for Agent v3.

Chains the full pipeline per AGENT.md MVP:
1. Create project
2. Upload/search papers
3. Parse papers
4. Generate paper cards
5. Extract evidence table
6. Build knowledge graph
7. Scope-based QA
8. Generate literature review
9. Generate innovation-point report
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.agent_v3.agents.evidence_agent import EvidenceAgent
from src.agent_v3.agents.kg_agent import KGAgent
from src.agent_v3.agents.paper_agent import PaperAgent
from src.agent_v3.core.config import AppConfig, load_config
from src.agent_v3.models import (
    InnovationReport,
    LiteratureReview,
    Paper,
    Project,
    QAAnswer,
    QAQuestion,
    RetrievalScope,
)
from src.agent_v3.parsers.pdf_parser import parse_pdf
from src.agent_v3.qa.scoped_qa import ScopedQA
from src.agent_v3.reports.innovation_report import InnovationReportGenerator
from src.agent_v3.reports.literature_review import LiteratureReviewGenerator

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Full pipeline orchestrator for the paper knowledge-base analysis agent.

    Usage:
        orch = Orchestrator()
        project = await orch.create_project("My Research")
        await orch.add_papers_from_dir(project, "/path/to/pdfs")
        await orch.process_project(project)
        answer = await orch.ask(project, "What are the main methods?")
        review = await orch.generate_review(project)
        innovation = await orch.generate_innovation_report(project)
    """

    def __init__(self, config: AppConfig | None = None):
        self.config = config or load_config()
        self.paper_agent = PaperAgent(self.config)
        self.evidence_agent = EvidenceAgent(self.config)
        self.kg_agent = KGAgent(self.config)
        self.qa = ScopedQA(self.config)
        self.review_gen = LiteratureReviewGenerator(self.config)
        self.innovation_gen = InnovationReportGenerator(self.config)

    async def create_project(self, name: str, description: str = "") -> Project:
        """Create a new research project."""
        project = Project(name=name, description=description)
        logger.info(f"Created project: {name} ({project.project_id})")
        return project

    async def add_paper(self, project: Project, paper: Paper) -> None:
        """Add a parsed paper to the project."""
        project.papers.append(paper)
        logger.info(f"Added paper: {paper.metadata.title[:50]}")

    async def add_papers_from_dir(self, project: Project, dir_path: str) -> int:
        """
        Parse and add all PDF papers from a directory.

        Returns:
            Number of papers added
        """
        path = Path(dir_path)
        if not path.exists():
            logger.error(f"Directory not found: {dir_path}")
            return 0

        pdf_files = list(path.glob("*.pdf"))
        count = 0
        for pdf_file in pdf_files:
            try:
                paper = parse_pdf(str(pdf_file))
                await self.add_paper(project, paper)
                count += 1
            except Exception as e:
                logger.error(f"Failed to parse {pdf_file}: {e}")

        logger.info(f"Added {count} papers from {dir_path}")
        return count

    async def process_project(self, project: Project) -> None:
        """
        Run the full processing pipeline on a project:
        paper cards -> evidence table -> knowledge graph
        """
        logger.info(f"Processing project: {project.name}")

        # Step 1: Generate paper cards
        logger.info("Step 1/3: Generating paper cards...")
        project.paper_cards = await self.paper_agent.generate_cards(project.papers)
        logger.info(f"Generated {len(project.paper_cards)} paper cards")

        # Step 2: Extract evidence table
        logger.info("Step 2/3: Extracting evidence table...")
        project.evidence_table = await self.evidence_agent.extract_all(
            project.paper_cards
        )
        logger.info(f"Extracted {len(project.evidence_table)} evidence records")

        # Step 3: Build knowledge graph
        logger.info("Step 3/3: Building knowledge graph...")
        project.knowledge_graph = await self.kg_agent.build_graph(
            project.paper_cards, project.evidence_table
        )
        logger.info(
            f"Built KG: {len(project.knowledge_graph.nodes)} nodes, "
            f"{len(project.knowledge_graph.edges)} edges"
        )

        logger.info(f"Project processing complete: {project.name}")

    async def ask(
        self,
        project: Project,
        question: str,
        scope: RetrievalScope | None = None,
    ) -> QAAnswer:
        """
        Ask a question over the project's paper library.

        Args:
            project: Processed project
            question: Question text
            scope: Optional retrieval scope

        Returns:
            QAAnswer with answer, evidence, and next actions
        """
        qa_question = QAQuestion(question=question, scope=scope)
        return await self.qa.answer(
            qa_question,
            project.paper_cards,
            project.evidence_table,
            project.knowledge_graph,
        )

    async def generate_review(
        self,
        project: Project,
        scope: RetrievalScope | None = None,
        research_goal: str = "",
    ) -> LiteratureReview:
        """Generate a literature review for the project."""
        return await self.review_gen.generate(
            project.paper_cards,
            project.evidence_table,
            project.knowledge_graph,
            scope,
            research_goal,
        )

    async def generate_innovation_report(
        self,
        project: Project,
        scope: RetrievalScope | None = None,
    ) -> InnovationReport:
        """Generate an innovation-point report for the project."""
        return await self.innovation_gen.generate(
            project.paper_cards,
            project.evidence_table,
            project.knowledge_graph,
            scope,
        )
