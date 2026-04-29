import pytest

from src.retrieval.citations import (
    Citation,
    CitationVerificationError,
    citation_from_chunk,
    verify_citations,
)
from src.retrieval.index import load_sample_corpus


def test_citation_from_chunk_and_verify() -> None:
    chunk = load_sample_corpus()[0]
    span = "components from a limited number of suppliers"
    citation = citation_from_chunk(chunk, span, label="C1")
    verified = verify_citations([citation], [chunk])
    assert verified == [citation]
    assert citation.span_offsets[0] >= 0


def test_verify_rejects_unretrieved_chunk() -> None:
    chunks = load_sample_corpus()
    citation = citation_from_chunk(chunks[0], "limited number of suppliers", label="C1")
    with pytest.raises(CitationVerificationError):
        verify_citations([citation], [chunks[1]])


def test_verify_rejects_tampered_offsets() -> None:
    chunk = load_sample_corpus()[0]
    citation = Citation(
        label="C1",
        cik=chunk.cik,
        accession=chunk.accession,
        section=chunk.section,
        span_text="limited number of suppliers",
        span_offsets=(0, 5),
        chunk_id=chunk.id,
        metadata=chunk.metadata,
    )
    with pytest.raises(CitationVerificationError):
        verify_citations([citation], [chunk])
