"""
Answer Generator - Generate answers with context

Generates answers using retrieved documents.
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """RAG response"""
    answer: str
    used_docs: List[str]
    reflection: str
    retrieval_needed: bool = True
    documents_evaluated: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnswerGenerator:
    """Generates answers using retrieved documents

    Used by SELF-RAG for answer generation with document context.
    """

    def __init__(self, llm: Any, max_context_docs: int = 5):
        """Initialize generator

        Args:
            llm: LLM instance
            max_context_docs: Maximum documents to use in context
        """
        self.llm = llm
        self.max_context_docs = max_context_docs

    async def generate_with_docs(self, query: str, docs: List[str]) -> RAGResponse:
        """Generate answer using documents

        Args:
            query: Query string
            docs: Retrieved documents

        Returns:
            RAGResponse: Generated response
        """
        start_time = time.time()

        if not docs:
            return await self._generate_without_docs(query, start_time)

        # Build context
        context = "\n\n".join([f"[文档{i+1}]\n{doc[:1000]}" for i, doc in enumerate(docs)])

        prompt = f"""
Based on the following references, answer the question.
Each document is numbered at the start.

References:
{context}

Question: {query}

Answer based on the references above.
- If references have relevant info, use it
- If not, say you cannot answer
- Cite the reference numbers you use
"""
        try:
            result = await self.llm.agenerate([prompt])
            answer = result.generations[0][0].text.strip()
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            answer = "Sorry, error generating answer."

        return RAGResponse(
            answer=answer,
            used_docs=[f"[文档{i+1}]" for i in range(len(docs))],
            reflection=f"Used {len(docs)} documents",
            retrieval_needed=True,
            documents_evaluated=len(docs),
            metadata={"generation_time": time.time() - start_time}
        )

    async def _generate_without_docs(self, query: str, start_time: float) -> RAGResponse:
        """Generate answer without documents

        Args:
            query: Query string
            start_time: Start time for timing

        Returns:
            RAGResponse: Generated response
        """
        logger.warning("No relevant documents, using model knowledge")

        prompt = f"""
Question: {query}

Answer directly.
"""
        try:
            result = await self.llm.agenerate([prompt])
            answer = result.generations[0][0].text.strip()
        except Exception:
            answer = "Sorry, error generating answer."

        return RAGResponse(
            answer=answer,
            used_docs=[],
            reflection="No documents, using model knowledge",
            retrieval_needed=True,
            documents_evaluated=0,
            metadata={"generation_time": time.time() - start_time}
        )


# Convenience function
async def generate_rag_answer(query: str, docs: List[str], llm: Any) -> RAGResponse:
    """Generate RAG answer in one line

    Args:
        query: Query string
        docs: Retrieved documents
        llm: LLM instance

    Returns:
        RAGResponse: Generated response
    """
    generator = AnswerGenerator(llm)
    return await generator.generate_with_docs(query, docs)
