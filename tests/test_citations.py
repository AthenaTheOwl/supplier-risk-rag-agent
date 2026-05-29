"""Citation verification tests.

DEC requirements exercised: R-CIT-001 (verbatim span verification
post-generation), R-CIT-002 (citations carry filing-level identifiers),
R-CIT-003 (verifier accepts SearchResult and DocumentChunk shapes).
"""

import pytest

from src.retrieval.citations import (
    Citation,
    CitationVerificationError,
    citation_from_chunk,
    verify_citations,
)
from src.retrieval.index import load_sample_corpus


def test_citation_from_chunk_and_verify() -> None:
    """Build a Citation carrying filing-level keys (cik/accession/section).

    Covers: R-CIT-002.
    """
    chunk = load_sample_corpus()[0]
    span = "components from a limited number of suppliers"
    citation = citation_from_chunk(chunk, span, label="C1")
    verified = verify_citations([citation], [chunk])
    assert verified == [citation]
    assert citation.span_offsets[0] >= 0


def test_verify_rejects_unretrieved_chunk() -> None:
    """Verifier accepts both SearchResult and DocumentChunk shapes; a
    citation pointing at an unretrieved chunk is rejected.

    Covers: R-CIT-003.
    """
    chunks = load_sample_corpus()
    citation = citation_from_chunk(chunks[0], "limited number of suppliers", label="C1")
    with pytest.raises(CitationVerificationError):
        verify_citations([citation], [chunks[1]])


def test_verify_rejects_tampered_offsets() -> None:
    """Verbatim span check rejects offsets that no longer cover the span text.

    Covers: R-CIT-001.
    """
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
