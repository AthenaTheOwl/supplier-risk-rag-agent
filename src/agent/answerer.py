"""Cite-or-refuse answer assembly."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from src.agent.refusal import RefusalDecision, refusal_message, should_refuse
from src.config import Keys
from src.retrieval.citations import Citation, citation_from_chunk, verify_citations
from src.retrieval.ranker import HybridRanker, SearchResult, tokenize

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class AgentAnswer:
    text: str
    citations: list[Citation]
    refused: bool
    retrieved_ids: list[str]
    confidence: float


def _best_span(text: str, query: str, *, max_chars: int = 420) -> str:
    query_tokens = set(tokenize(query))
    sentences = [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]
    if not sentences:
        return text[:max_chars].strip()
    scored = []
    for sentence in sentences:
        overlap = len(query_tokens & set(tokenize(sentence)))
        scored.append((overlap, len(sentence), sentence))
    _, _, best = max(scored, key=lambda item: (item[0], -item[1]))
    if len(best) <= max_chars:
        return best
    return best[:max_chars].rsplit(" ", 1)[0].strip()


def _claim_from_span(span: str) -> str:
    return span.strip()


def _citation_block(citations: Sequence[Citation]) -> str:
    lines = ["", "Verified citations:"]
    for citation in citations:
        company = citation.metadata.get("company", "Unknown company")
        filing_type = citation.metadata.get("filing_type", "filing")
        year = citation.metadata.get("year", "unknown year")
        lines.append(
            f"[{citation.label}] {company}, {filing_type} {year}, {citation.section}, "
            f"{citation.accession}, offsets {citation.span_offsets[0]}-{citation.span_offsets[1]}"
        )
    return "\n".join(lines)


def answer_from_results(
    query: str,
    results: Sequence[SearchResult],
    *,
    max_citations: int = 4,
    decision: RefusalDecision | None = None,
) -> AgentAnswer:
    decision = decision or should_refuse(query, results)
    retrieved_ids = [result.chunk.id for result in results]
    if decision.refused:
        return AgentAnswer(
            text=refusal_message(query, decision),
            citations=[],
            refused=True,
            retrieved_ids=retrieved_ids,
            confidence=decision.top_score,
        )

    citations: list[Citation] = []
    lines = ["Based on the retrieved SEC filing excerpts:"]
    seen: set[str] = set()
    for result in results:
        if len(citations) >= max_citations:
            break
        company = result.chunk.company
        if company in seen and len(results) > max_citations:
            continue
        span = _best_span(result.chunk.text, query)
        label = f"C{len(citations) + 1}"
        citation = citation_from_chunk(result.chunk, span, label=label)
        citations.append(citation)
        seen.add(company)
        lines.append(f"- {company}: {_claim_from_span(span)} [{label}]")

    verify_citations(citations, [result.chunk for result in results])
    text = "\n".join(lines) + _citation_block(citations)
    return AgentAnswer(
        text=text,
        citations=citations,
        refused=False,
        retrieved_ids=retrieved_ids,
        confidence=decision.top_score,
    )


class SupplierRiskAgent:
    def __init__(self, ranker: HybridRanker) -> None:
        self.ranker = ranker

    def answer(
        self,
        query: str,
        *,
        top_k: int = 5,
        use_live_llm: bool = False,
        keys: Keys | None = None,
        llm_client: object | None = None,
    ) -> AgentAnswer:
        results = self.ranker.search(query, top_k=top_k)
        deterministic = answer_from_results(query, results)
        if deterministic.refused or not use_live_llm:
            return deterministic
        if keys is None or llm_client is None:
            return deterministic

        context = "\n\n".join(
            f"[{index + 1}] {result.chunk.company} {result.chunk.section}: {result.chunk.text}"
            for index, result in enumerate(results[:top_k])
        )
        prompt = (
            "Rewrite the deterministic answer in concise prose. Do not add facts. "
            "Keep the bracketed citation labels exactly as supplied.\n\n"
            f"Question: {query}\n\nContext:\n{context}\n\n"
            f"Deterministic answer:\n{deterministic.text}"
        )
        live_text = llm_client.complete(
            messages=[{"role": "user", "content": prompt}],
            system="You answer only from supplied filing excerpts and preserve citations.",
            max_tokens=700,
        )
        return AgentAnswer(
            text=live_text.strip() + _citation_block(deterministic.citations),
            citations=deterministic.citations,
            refused=False,
            retrieved_ids=deterministic.retrieved_ids,
            confidence=deterministic.confidence,
        )
