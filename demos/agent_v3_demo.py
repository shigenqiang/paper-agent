"""
Agent v3 Demo - Paper Knowledge-Base Analysis Agent

Full pipeline demo per AGENT.md MVP:
1. Create project
2. Add papers (from PDF directory or manual text)
3. Parse -> paper cards -> evidence table -> knowledge graph
4. Scope-based QA
5. Generate literature review
6. Generate innovation-point report

Usage:
    PYTHONPATH=. python demos/agent_v3_demo.py
    PYTHONPATH=. python demos/agent_v3_demo.py --pdf-dir /path/to/pdfs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("agent_v3_demo")


async def run_demo(pdf_dir: str | None = None):
    """Run the full agent_v3 demo pipeline."""
    from src.agent_v3.core.config import load_config
    from src.agent_v3.models import Paper, PaperMetadata
    from src.agent_v3.workflow.orchestrator import Orchestrator

    config = load_config()
    orch = Orchestrator(config)

    # Step 1: Create project
    logger.info("=" * 60)
    logger.info("Step 1: Creating project")
    project = await orch.create_project(
        name="深度学习医学图像诊断研究",
        description="探索深度学习在医学图像诊断领域的研究现状和创新方向",
    )
    logger.info(f"Project created: {project.project_id}")

    # Step 2: Add papers
    logger.info("=" * 60)
    logger.info("Step 2: Adding papers")

    if pdf_dir:
        count = await orch.add_papers_from_dir(project, pdf_dir)
        logger.info(f"Added {count} papers from {pdf_dir}")
    else:
        # Demo with sample paper data (no PDF needed)
        sample_papers = [
            Paper(
                metadata=PaperMetadata(
                    title="Deep Learning for Medical Image Analysis: A Survey",
                    authors=["Wang", "Chen", "Liu"],
                    year=2023,
                    venue="IEEE TMI",
                    abstract="This survey provides a comprehensive review of deep learning methods for medical image analysis.",
                ),
                full_text=(
                    "Deep Learning for Medical Image Analysis: A Survey\n\n"
                    "Abstract: This survey provides a comprehensive review of deep learning methods "
                    "for medical image analysis, covering classification, segmentation, and detection tasks.\n\n"
                    "Introduction: Medical image analysis is crucial for clinical diagnosis. "
                    "Deep learning has revolutionized this field with CNNs, transformers, and diffusion models.\n\n"
                    "Methods: We reviewed 200+ papers published between 2018-2023, categorizing them "
                    "by architecture (CNN, Transformer, GAN, Diffusion), task (classification, segmentation, detection), "
                    "and modality (X-ray, CT, MRI, Ultrasound).\n\n"
                    "Results: CNNs remain dominant for classification (95% accuracy on chest X-ray). "
                    "Transformers show superior performance on segmentation tasks (Dice score 0.92). "
                    "Diffusion models are emerging for data augmentation.\n\n"
                    "Limitations: Most studies use small datasets (<1000 samples). "
                    "Lack of multi-center validation. Interpretability remains a challenge.\n\n"
                    "Conclusion: Deep learning shows great promise but needs larger datasets and better interpretability."
                ),
            ),
            Paper(
                metadata=PaperMetadata(
                    title="Attention-based U-Net for Organ Segmentation",
                    authors=["Zhang", "Li"],
                    year=2024,
                    venue="MICCAI",
                    abstract="We propose an attention-based U-Net architecture for multi-organ segmentation in CT scans.",
                ),
                full_text=(
                    "Attention-based U-Net for Organ Segmentation\n\n"
                    "Abstract: We propose an attention-based U-Net architecture for multi-organ segmentation in CT scans.\n\n"
                    "Introduction: Organ segmentation is fundamental for treatment planning. "
                    "Existing U-Net variants lack attention mechanisms for fine-grained features.\n\n"
                    "Method: We add channel and spatial attention gates to the standard U-Net decoder. "
                    "The model is trained on 500 CT scans from 3 hospitals.\n\n"
                    "Results: Our method achieves Dice score of 0.91 for liver, 0.88 for kidney, "
                    "and 0.85 for spleen segmentation. Outperforms baseline U-Net by 3-5%.\n\n"
                    "Limitations: Only tested on CT modality. Training requires GPU with 16GB+ memory. "
                    "Not validated on MRI or ultrasound.\n\n"
                    "Future work: Extend to multi-modal segmentation and reduce memory requirements."
                ),
            ),
            Paper(
                metadata=PaperMetadata(
                    title="Federated Learning for Privacy-Preserving Medical Imaging",
                    authors=["Park", "Kim", "Lee"],
                    year=2024,
                    venue="Nature Medicine",
                    abstract="We present a federated learning framework for training diagnostic models without sharing patient data.",
                ),
                full_text=(
                    "Federated Learning for Privacy-Preserving Medical Imaging\n\n"
                    "Abstract: We present a federated learning framework for training diagnostic models "
                    "without sharing patient data across institutions.\n\n"
                    "Introduction: Data privacy regulations (HIPAA, GDPR) limit data sharing for medical AI. "
                    "Federated learning enables collaborative training while keeping data local.\n\n"
                    "Method: We use FedAvg with differential privacy on 10 hospitals. "
                    "Each hospital trains locally on chest X-rays, then aggregates model updates.\n\n"
                    "Results: Federated model achieves 93% accuracy (vs 95% centralized), "
                    "with epsilon=1.0 differential privacy guarantee.\n\n"
                    "Limitations: Communication overhead is significant (3x slower than centralized). "
                    "Performance degrades with non-IID data distributions across hospitals. "
                    "Differential privacy adds noise that reduces accuracy by 2%.\n\n"
                    "Future work: Reduce communication cost with gradient compression. "
                    "Handle non-IID data with personalized federated learning."
                ),
            ),
        ]

        for paper in sample_papers:
            await orch.add_paper(project, paper)
        logger.info(f"Added {len(sample_papers)} sample papers")

    # Step 3: Process project (cards -> evidence -> KG)
    logger.info("=" * 60)
    logger.info("Step 3: Processing project (paper cards -> evidence table -> knowledge graph)")
    await orch.process_project(project)

    # Print results
    logger.info("=" * 60)
    logger.info("Processing Results:")
    logger.info(f"  Papers: {len(project.papers)}")
    logger.info(f"  Paper Cards: {len(project.paper_cards)}")
    logger.info(f"  Evidence Records: {len(project.evidence_table)}")
    logger.info(f"  KG Nodes: {len(project.knowledge_graph.nodes)}")
    logger.info(f"  KG Edges: {len(project.knowledge_graph.edges)}")

    # Print paper cards
    for card in project.paper_cards:
        logger.info(f"\n  Card: {card.title}")
        logger.info(f"    Research Q: {card.research_question[:80]}")
        logger.info(f"    Method: {card.method[:80]}")
        logger.info(f"    Findings: {len(card.key_findings)}")
        logger.info(f"    Limitations: {len(card.limitations)}")

    # Step 4: Scope-based QA
    logger.info("=" * 60)
    logger.info("Step 4: Scope-based QA")

    questions = [
        "这些论文使用了哪些主要方法？各有什么优缺点？",
        "当前研究的主要局限性是什么？有哪些研究空白？",
        "有哪些可能的创新方向？",
    ]

    for q in questions:
        logger.info(f"\n  Q: {q}")
        answer = await orch.ask(project, q)
        logger.info(f"  A: {answer.answer[:200]}...")
        logger.info(f"  Scope: {answer.scope_description}")
        logger.info(f"  Evidence: {len(answer.supporting_evidence)} items")
        if answer.uncertainty:
            logger.info(f"  Uncertainty: {answer.uncertainty[:100]}")

    # Step 5: Generate literature review
    logger.info("=" * 60)
    logger.info("Step 5: Generating literature review")
    review = await orch.generate_review(
        project,
        research_goal="探索深度学习在医学图像诊断中的应用现状和未来方向",
    )
    logger.info(f"  Title: {review.title}")
    logger.info(f"  Full text length: {len(review.full_text)} chars")

    # Save review
    output_dir = Path("output/agent_v3")
    output_dir.mkdir(parents=True, exist_ok=True)
    review_path = output_dir / f"literature_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    review_path.write_text(review.full_text, encoding="utf-8")
    logger.info(f"  Saved to: {review_path}")

    # Step 6: Generate innovation report
    logger.info("=" * 60)
    logger.info("Step 6: Generating innovation-point report")
    innovation = await orch.generate_innovation_report(project)
    logger.info(f"  Title: {innovation.title}")
    logger.info(f"  Innovation points: {len(innovation.innovation_points)}")
    for i, p in enumerate(innovation.innovation_points, 1):
        logger.info(f"    {i}. {p.name}: {p.description[:80]}")

    # Save innovation report
    innov_path = output_dir / f"innovation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    innov_path.write_text(innovation.full_text, encoding="utf-8")
    logger.info(f"  Saved to: {innov_path}")

    # Save project data as JSON
    project_data = {
        "project_id": project.project_id,
        "name": project.name,
        "papers": len(project.papers),
        "paper_cards": len(project.paper_cards),
        "evidence_records": len(project.evidence_table),
        "kg_nodes": len(project.knowledge_graph.nodes),
        "kg_edges": len(project.knowledge_graph.edges),
    }
    project_path = output_dir / f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    project_path.write_text(json.dumps(project_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"  Project data saved to: {project_path}")

    logger.info("=" * 60)
    logger.info("Demo complete!")
    return project


def main():
    parser = argparse.ArgumentParser(description="Agent v3 Demo")
    parser.add_argument("--pdf-dir", type=str, help="Directory containing PDF papers")
    args = parser.parse_args()

    asyncio.run(run_demo(args.pdf_dir))


if __name__ == "__main__":
    main()
