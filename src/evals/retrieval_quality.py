from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.retrieval.ranker import HybridRanker


@dataclass(frozen=True)
class RetrievalMetrics:
    recall_at_5: float
    mrr: float
    total: int


def _matches(result_accession: str, result_cik: str, case: dict[str, Any]) -> bool:
    expected_accessions = set(case.get("expected_accessions") or [])
    expected_ciks = {str(cik).zfill(10) for cik in case.get("expected_ciks") or []}
    return result_accession in expected_accessions or result_cik in expected_ciks


def evaluate_retrieval(cases: list[dict[str, Any]], ranker: HybridRanker) -> RetrievalMetrics:
    hits = 0
    reciprocal_rank_sum = 0.0
    for case in cases:
        results = ranker.search(case["query"], top_k=5)
        first_rank = 0
        for index, result in enumerate(results, start=1):
            if _matches(result.chunk.accession, result.chunk.cik, case):
                first_rank = index
                break
        if first_rank:
            hits += 1
            reciprocal_rank_sum += 1.0 / first_rank
    total = len(cases)
    return RetrievalMetrics(
        recall_at_5=hits / total if total else 0.0,
        mrr=reciprocal_rank_sum / total if total else 0.0,
        total=total,
    )
