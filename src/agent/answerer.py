"""Cite-or-refuse answer assembly."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace

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
    generation_mode: str = "deterministic"
    generation_reason: str | None = None


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


def _render_verified_answer(citations: Sequence[Citation]) -> str:
    lines = ["Based on the retrieved SEC filing excerpts:"]
    for citation in citations:
        company = citation.metadata.get("company", "Unknown company")
        lines.append(f"- {company}: {_claim_from_span(citation.span_text)} [{citation.label}]")
    return "\n".join(lines) + _citation_block(citations)


def _unique_json_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated JSON field")
        result[key] = value
    return result


def _live_citation_order(
    response: str, citations: Sequence[Citation],
) -> tuple[list[Citation] | None, str | None]:
    """Accept a complete permutation; no generated prose crosses this boundary."""
    try:
        payload = json.loads(response, object_pairs_hook=_unique_json_fields)
    except (TypeError, ValueError):
        return None, "The response was not valid JSON."
    if not isinstance(payload, dict) or set(payload) != {"citation_labels"}:
        return None, "The response must contain only citation_labels."
    labels = payload["citation_labels"]
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        return None, "citation_labels must be a list of labels."
    if len(set(labels)) != len(labels):
        return None, "Each citation label must appear exactly once."
    by_label = {citation.label: citation for citation in citations}
    if set(labels) - set(by_label):
        return None, "The response included an unknown citation label."
    if not labels or set(labels) != set(by_label):
        return None, "The response omitted verified citation labels."
    return [by_label[label] for label in labels], None


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

    verify_citations(citations, [result.chunk for result in results])
    text = _render_verified_answer(citations)
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

        prompt = (
            "Order the verified evidence by relevance to the question. Return only a JSON "
            'object with one key, "citation_labels", whose value is a complete permutation '
            "of the supplied citation labels. Include every label exactly once. "
            "Do not add prose, facts, fields, or new labels.\n\n"
            "Required JSON shape (reorder only these unbracketed labels): "
            f"{json.dumps({'citation_labels': [c.label for c in deterministic.citations]})}\n\n"
            f"Question: {query}\n\nVerified evidence:\n{deterministic.text}"
        )
        try:
            live_text = llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                system="You order verified evidence. Return only the required JSON object.",
                max_tokens=700,
            )
        except Exception as exc:
            return replace(
                deterministic,
                generation_mode="live_failed",
                generation_reason=f"Provider call failed ({exc.__class__.__name__}).",
            )
        ordered, reason = _live_citation_order(live_text, deterministic.citations)
        if ordered is None:
            return replace(
                deterministic, generation_mode="live_rejected", generation_reason=reason,
            )
        verify_citations(ordered, [result.chunk for result in results])
        return AgentAnswer(
            text=_render_verified_answer(ordered),
            citations=ordered,
            refused=False,
            retrieved_ids=deterministic.retrieved_ids,
            confidence=deterministic.confidence,
            generation_mode="live_ordered",
        )
