"""Citation span verification."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from src.retrieval.index import DocumentChunk


class CitationVerificationError(ValueError):
    """Raised when a citation does not point at a retrieved chunk span."""


@dataclass(frozen=True)
class Citation:
    label: str
    cik: str
    accession: str
    section: str
    span_text: str
    span_offsets: tuple[int, int]
    chunk_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "cik": self.cik,
            "accession": self.accession,
            "section": self.section,
            "span_text": self.span_text,
            "span_offsets": self.span_offsets,
            "chunk_id": self.chunk_id,
            "metadata": self.metadata,
        }


def citation_from_chunk(chunk: DocumentChunk, span_text: str, *, label: str) -> Citation:
    offset = chunk.text.find(span_text)
    if offset < 0:
        raise CitationVerificationError(f"Span for {label} is not present in chunk {chunk.id}")
    return Citation(
        label=label,
        cik=chunk.cik,
        accession=chunk.accession,
        section=chunk.section,
        span_text=span_text,
        span_offsets=(offset, offset + len(span_text)),
        chunk_id=chunk.id,
        metadata=dict(chunk.metadata),
    )


def _to_chunk(item: object) -> DocumentChunk:
    if isinstance(item, DocumentChunk):
        return item
    chunk = getattr(item, "chunk", None)
    if isinstance(chunk, DocumentChunk):
        return chunk
    raise TypeError(f"Expected DocumentChunk or SearchResult-like object, got {type(item)!r}")


def verify_citations(
    citations: Iterable[Citation],
    retrieved_chunks: Iterable[DocumentChunk | object],
) -> list[Citation]:
    chunk_by_id = {_to_chunk(item).id: _to_chunk(item) for item in retrieved_chunks}
    verified: list[Citation] = []
    for citation in citations:
        chunk = chunk_by_id.get(citation.chunk_id)
        if chunk is None:
            raise CitationVerificationError(
                f"Citation {citation.label} points to a chunk that was not retrieved."
            )
        start, end = citation.span_offsets
        if start < 0 or end > len(chunk.text) or start >= end:
            raise CitationVerificationError(f"Citation {citation.label} has invalid offsets.")
        if chunk.text[start:end] != citation.span_text:
            raise CitationVerificationError(
                f"Citation {citation.label} offsets do not match the cited text."
            )
        if citation.span_text not in chunk.text:
            raise CitationVerificationError(
                f"Citation {citation.label} span is not present in retrieved text."
            )
        verified.append(citation)
    return verified
