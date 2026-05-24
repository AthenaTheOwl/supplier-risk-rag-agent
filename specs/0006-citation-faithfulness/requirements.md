# requirements: citation-faithfulness

## Scope

Spec 0006 backfills the citation verifier that runs after the
answerer produces a candidate response. The verifier under
`src/retrieval/citations.py` asserts every cited span exists
verbatim in a retrieved chunk and that the offsets line up. The
citation_faithfulness eval suite at threshold ≥ 0.95 depends on this
verifier. This spec records the requirements the verifier answers.

## Requirements

### R-CIT-001: every citation is verified verbatim against a retrieved chunk

WHEN the answerer attaches a `Citation` to its response, THE SYSTEM
SHALL verify that the cited span exists verbatim in one of the
retrieved chunks the answerer received, that the span offsets line
up, and SHALL raise `CitationVerificationError` if any check fails.

Acceptance:
- `verify_citations(citations, retrieved_chunks)` in
  `src/retrieval/citations.py` walks each citation, looks up the
  chunk by id, validates the offsets, validates the substring at
  those offsets, and validates the substring is present in the chunk
  text.
- An unverifiable citation raises `CitationVerificationError` with
  the citation label naming the failure mode.
- The `citation_faithfulness` eval suite (≥ 0.95) depends on this
  verifier.

### R-CIT-002: citations carry filing-level identifiers

WHEN a citation lands in the response, THE SYSTEM SHALL include CIK,
accession, section, the span text, the span offsets, and the chunk
id, so a reviewer can trace the cited text to the source filing.

Acceptance:
- `Citation` is a frozen dataclass with `cik`, `accession`,
  `section`, `span_text`, `span_offsets`, `chunk_id`, and a free-form
  `metadata` dict.
- `Citation.as_dict()` returns a serializable view used by `app.py`
  to render the citations expander.
- `citation_from_chunk(chunk, span_text, label)` builds a citation
  from a retrieved chunk and a verbatim span, raising on missing
  spans.

### R-CIT-003: the verifier accepts SearchResult and DocumentChunk shapes

WHEN the answerer passes `retrieved_chunks` to the verifier, THE
SYSTEM SHALL accept either raw `DocumentChunk` objects or
SearchResult-like objects (objects exposing a `chunk` attribute), so
the answerer does not need to unwrap results before verification.

Acceptance:
- `_to_chunk(item)` in `src/retrieval/citations.py` handles both
  `DocumentChunk` and any object exposing a `chunk` attribute.
- A wrong-shape input raises `TypeError` with the offending type
  name.
- The verifier's chunk-id lookup runs against the unwrapped chunks.
