"""Small deterministic planner for retrieval subqueries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryPlan:
    original_query: str
    subqueries: list[str]


def plan_query(query: str) -> QueryPlan:
    normalized = " ".join(query.split())
    subqueries = [normalized]
    lower = normalized.lower()
    if "customer concentration" in lower:
        subqueries.append("customer concentration revenue dependence")
    if "export" in lower or "china" in lower:
        subqueries.append("export controls china restrictions")
    if "advanced packaging" in lower or "capacity" in lower:
        subqueries.append("advanced packaging capacity constraints")
    return QueryPlan(original_query=normalized, subqueries=list(dict.fromkeys(subqueries)))
