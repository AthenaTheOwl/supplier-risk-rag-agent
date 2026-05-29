"""Abstention rules for unsupported or out-of-scope questions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.retrieval.ranker import SearchResult, tokenize

DEFAULT_CONFIDENCE_THRESHOLD = 0.18

DOMAIN_TERMS = {
    "10-k",
    "10-q",
    "20-f",
    "advanced",
    "capacity",
    "china",
    "citation",
    "concentration",
    "constraint",
    "constraints",
    "customer",
    "customers",
    "disclose",
    "disclosed",
    "edgar",
    "export",
    "filing",
    "filings",
    "foundry",
    "geographic",
    "geopolitical",
    "inventory",
    "manufacturing",
    "packaging",
    "procurement",
    "production",
    "risk",
    "risks",
    "sec",
    "semiconductor",
    "single-source",
    "sourcing",
    "supplier",
    "suppliers",
    "supply",
    "taiwan",
    "vendor",
}

UNSUPPORTED_PHRASES = {
    "best laptop",
    "personal phone",
    "private supplier contracts",
    "share price",
    "should i buy",
    "stock price",
    "super bowl",
    "uploaded contract",
    "weather",
}

# Adversarial supplier-risk patterns. These look in-scope (they
# carry domain terms like "supplier" or "TSMC" or "EUV") but they
# ask for information no SEC filing supplies: exact future numbers,
# confidential business data, named-individual identifications, or
# predictions about acquisitions/policy actions. The agent refuses
# any query whose lowercased text contains one of these substrings.
# See DEC-EVL-012 for the rationale.
ADVERSARIAL_PHRASES = {
    # exact future-number predictions
    "predict ",
    "will fail in",
    "will be acquired",
    "next quarter",
    "in 2027",
    "in 2028",
    "in 2029",
    "in 2030",
    "exact ",
    "forecast ",
    # confidential or non-public information
    "confidential",
    "secret ",
    "private contract",
    "private agreement",
    "personal phone",
    "personal email",
    "reveal ",
    # ratings / scores not present in filings
    "risk score",
    "risk rating",
}


@dataclass(frozen=True)
class RefusalDecision:
    refused: bool
    reason: str
    top_score: float = 0.0


def is_in_scope_question(query: str) -> bool:
    tokens = set(tokenize(query))
    return bool(tokens & DOMAIN_TERMS)


def should_refuse(
    query: str,
    results: Sequence[SearchResult],
    *,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> RefusalDecision:
    lower_query = query.lower()
    if any(phrase in lower_query for phrase in UNSUPPORTED_PHRASES):
        return RefusalDecision(True, "The question asks for unsupported non-filing information.")
    if any(phrase in lower_query for phrase in ADVERSARIAL_PHRASES):
        return RefusalDecision(
            True,
            "The question asks for predictions, confidential data, or information not "
            "disclosed in public SEC filings.",
        )
    if not is_in_scope_question(query):
        return RefusalDecision(True, "The question is outside supplier-risk filing analysis.")
    if not results:
        return RefusalDecision(True, "No filing excerpts were retrieved.")
    top = results[0]
    if top.score < threshold or top.overlap == 0:
        return RefusalDecision(
            True,
            "Retrieved excerpts are below the support threshold.",
            top_score=top.score,
        )
    return RefusalDecision(False, "Sufficient support retrieved.", top_score=top.score)


def refusal_message(query: str, decision: RefusalDecision) -> str:
    return (
        "I cannot answer that from the retrieved SEC filing excerpts. "
        f"Reason: {decision.reason} Query: {query!r}."
    )
