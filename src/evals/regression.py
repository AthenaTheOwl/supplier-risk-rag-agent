from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agent.answerer import SupplierRiskAgent


@dataclass(frozen=True)
class RegressionMetrics:
    answer_quality: float
    total: int


def evaluate_regression(cases: list[dict[str, Any]], agent: SupplierRiskAgent) -> RegressionMetrics:
    passing = 0
    for case in cases:
        answer = agent.answer(case["query"])
        expected_accessions = set(case.get("expected_accessions") or [])
        cited_accessions = {citation.accession for citation in answer.citations}
        required_terms = {term.lower() for term in case.get("required_terms") or []}
        answer_text = answer.text.lower()
        terms_present = all(term in answer_text for term in required_terms)
        citations_present = bool(answer.citations)
        expected_hit = not expected_accessions or bool(cited_accessions & expected_accessions)
        if not answer.refused and citations_present and terms_present and expected_hit:
            passing += 1
    total = len(cases)
    return RegressionMetrics(answer_quality=passing / total if total else 0.0, total=total)
