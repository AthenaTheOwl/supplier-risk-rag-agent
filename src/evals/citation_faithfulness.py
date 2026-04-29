from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agent.answerer import SupplierRiskAgent
from src.retrieval.citations import CitationVerificationError, verify_citations


@dataclass(frozen=True)
class CitationMetrics:
    faithfulness: float
    answered_rate: float
    total: int


def evaluate_citations(cases: list[dict[str, Any]], agent: SupplierRiskAgent) -> CitationMetrics:
    verified_cases = 0
    answered = 0
    for case in cases:
        answer = agent.answer(case["query"])
        if answer.refused or not answer.citations:
            continue
        answered += 1
        retrieved_chunks = [
            chunk for chunk in agent.ranker.chunks if chunk.id in set(answer.retrieved_ids)
        ]
        try:
            verify_citations(answer.citations, retrieved_chunks)
        except CitationVerificationError:
            continue
        verified_cases += 1
    total = len(cases)
    return CitationMetrics(
        faithfulness=verified_cases / total if total else 0.0,
        answered_rate=answered / total if total else 0.0,
        total=total,
    )
