from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agent.answerer import SupplierRiskAgent


@dataclass(frozen=True)
class AbstentionMetrics:
    refusal_precision: float
    total: int


def evaluate_abstention(cases: list[dict[str, Any]], agent: SupplierRiskAgent) -> AbstentionMetrics:
    correct = 0
    for case in cases:
        answer = agent.answer(case["query"])
        expected_refusal = bool(case.get("expected_refusal", True))
        if answer.refused == expected_refusal:
            correct += 1
    total = len(cases)
    return AbstentionMetrics(refusal_precision=correct / total if total else 0.0, total=total)
