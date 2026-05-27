"""
Document Evaluator - Evaluate document relevance and utility

Core scoring logic for SELF-RAG.
"""
from dataclasses import dataclass
from typing import Any, List

from .score_parser import parse_llm_score


@dataclass
class DocumentEvaluation:
    """Document evaluation result"""
    document: str
    relevance_score: float  # 0-1
    utility_score: float    # 0-1
    should_use: bool
    reasoning: str


class DocumentEvaluator:
    """Evaluates documents for relevance and utility

    Used by SELF-RAG controller to decide which documents to use.
    """

    def __init__(self, llm: Any, relevance_threshold: float = 0.7,
                 utility_threshold: float = 0.5):
        """Initialize evaluator

        Args:
            llm: LLM instance
            relevance_threshold: Minimum relevance to use doc
            utility_threshold: Minimum utility to use doc
        """
        self.llm = llm
        self.relevance_threshold = relevance_threshold
        self.utility_threshold = utility_threshold

    async def evaluate_relevance(self, doc: str, query: str) -> float:
        """Evaluate document relevance to query

        Args:
            doc: Document content
            query: Query string

        Returns:
            float: Relevance score (0-1)
        """
        doc_preview = doc[:500] if len(doc) > 500 else doc

        prompt = f"""
Query: {query}

Document:
{doc_preview}...

Rate how relevant this document is to answering the query.
Consider:
- Is content directly related?
- Is information accurate?
- Does it help answer the question?

Score 0-1, where 1 is highly relevant, 0 is not relevant at all.
Return only a number.
"""
        try:
            result = await self.llm.agenerate([prompt])
            response = result.generations[0][0].text.strip()
            return parse_llm_score(response)
        except Exception:
            return 0.5

    async def evaluate_utility(self, doc: str, query: str,
                             partial_answer: str = "") -> float:
        """Evaluate document utility for current answer

        Args:
            doc: Document content
            query: Query string
            partial_answer: Current partial answer

        Returns:
            float: Utility score (0-1)
        """
        doc_preview = doc[:500] if len(doc) > 500 else doc

        prompt = f"""
Query: {query}

Current answer (if any):
{partial_answer if partial_answer else "(none)"}

Document:
{doc_preview}...

Rate how useful this document is for improving the current answer.
Consider:
- Does it provide new information or evidence?
- Does it help completeness?
- Does it have important citations?

Score 0-1, where 1 is very helpful, 0 is not helpful.
Return only a number.
"""
        try:
            result = await self.llm.agenerate([prompt])
            response = result.generations[0][0].text.strip()
            return parse_llm_score(response)
        except Exception:
            return 0.5

    async def should_use(self, doc: str, query: str,
                        partial_answer: str = "") -> bool:
        """Decide if document should be used

        Args:
            doc: Document content
            query: Query string
            partial_answer: Current partial answer

        Returns:
            bool: True if document meets thresholds
        """
        relevance = await self.evaluate_relevance(doc, query)
        if relevance < self.relevance_threshold:
            return False

        utility = await self.evaluate_utility(doc, query, partial_answer)
        if utility < self.utility_threshold:
            return False

        return True

    async def evaluate_batch(self, docs: List[str], query: str) -> List[DocumentEvaluation]:
        """Evaluate multiple documents

        Args:
            docs: List of documents
            query: Query string

        Returns:
            List[DocumentEvaluation]: Evaluation results
        """
        evaluations = []

        for doc in docs:
            relevance = await self.evaluate_relevance(doc, query)
            utility = await self.evaluate_utility(doc, query)
            should_use = (relevance >= self.relevance_threshold and
                         utility >= self.utility_threshold)

            evaluation = DocumentEvaluation(
                document=doc[:100] + "..." if len(doc) > 100 else doc,
                relevance_score=relevance,
                utility_score=utility,
                should_use=should_use,
                reasoning=f"relevance={relevance:.2f}, utility={utility:.2f}"
            )
            evaluations.append(evaluation)

        return evaluations
