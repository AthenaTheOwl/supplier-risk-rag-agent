---
id: DEC-CIT-003-verifier-accepts-search-result-and-document-chunk-shapes
spec: specs/0006-citation-faithfulness/
requirement: R-CIT-003
date: 2026-05-24
status: approved
reversible: true
decision: |
  The citation verifier accepts either raw `DocumentChunk` objects
  or SearchResult-like objects (any object exposing a `chunk`
  attribute that resolves to a `DocumentChunk`). `_to_chunk(item)`
  in `src/retrieval/citations.py` walks the input: if the item is
  already a `DocumentChunk`, return it; if it exposes a `chunk`
  attribute, return that attribute; otherwise raise `TypeError`
  naming the offending type. The verifier's chunk-id lookup runs
  against the unwrapped chunks.
alternatives:
  - label: require callers to unwrap SearchResult before calling the verifier
    rejected_because: |
      Every call site would then have to remember to write
      `verify_citations(citations, [r.chunk for r in results])`.
      One forgotten unwrap shows up as a confusing AttributeError
      at chunk-id lookup time. Pushing the unwrap into the verifier
      removes the bookkeeping; the call site passes the search
      results directly and the verifier does the right thing.
  - label: accept any duck-typed object with the right attributes
    rejected_because: |
      Loose duck typing turns a wrong-shape input into a runtime
      failure deep inside the verifier (a chunk text lookup against
      a `None` attribute). The TypeError-with-named-offending-type
      rule turns the failure into a precise error at the boundary,
      which is the failure mode a future contributor wants.
  - label: a separate `verify_citations_from_results` function
    rejected_because: |
      Two functions for the same job invites drift. A bug fix in
      one would have to land in both; one would inevitably miss the
      paired update. The single function with a unwrap step at the
      boundary is one surface to maintain.
rationale: |
  The agent's call shape is the source of the constraint. The
  retriever returns `SearchResult` objects (chunk + score +
  per-component score breakdown); the answerer composes a cited
  answer over those results. Passing the same list to the verifier
  is the natural call shape. Forcing the answerer to unwrap before
  the verifier call adds friction without clarity.

  The `_to_chunk` helper is a four-line function. The first branch
  catches the common case (the answerer passes `SearchResult`
  objects); the second branch catches the test case (a test that
  builds `DocumentChunk` fixtures directly); the third branch
  raises with the offending type name so a future contributor who
  passes a wrong-shape object gets a precise error. The helper is
  the cheapest path to both call shapes working.

  The `TypeError` failure mode is loud on purpose. A silent passthrough
  on a wrong-shape input would let a bug land. The TypeError surfaces
  at PR time when a test exercises a new call site; the named
  offending type makes the fix obvious.
evidence:
  - kind: spec
    ref: specs/0006-citation-faithfulness/
  - kind: doc
    ref: src/retrieval/citations.py (`_to_chunk` helper)
  - kind: doc
    ref: src/agent/answerer.py (calls the verifier with `SearchResult` objects)
  - kind: doc
    ref: tests/test_citations.py (covers both call shapes)
rollback: |
  Single-file revert. Remove the `_to_chunk` helper and require all
  callers to pass `DocumentChunk` objects. Update `src/agent/answerer.py`
  to unwrap `SearchResult.chunk` before the verifier call. The cost
  of rollback is one call-site edit; the cost of carrying the helper
  is four lines of code. Re-run the four-suite eval gate after any
  change; the `citation_faithfulness` suite covers the verifier
  directly.
owner: engineering.implementation
---

## decision

The citation verifier accepts either raw `DocumentChunk` objects or
SearchResult-like objects (any object exposing a `chunk` attribute
that resolves to a `DocumentChunk`). `_to_chunk(item)` walks the
input; a wrong-shape input raises `TypeError` naming the offending
type.

## alternatives

- Require callers to unwrap before calling — every call site has to
  remember; one missed unwrap surfaces as a confusing AttributeError.
- Accept any duck-typed object — loose typing turns a wrong-shape
  input into a deep runtime failure.
- Two functions (one per shape) — invites drift.

## rationale

The retriever returns `SearchResult` objects; the answerer composes
over them. Passing the same list to the verifier is the natural
shape. The `_to_chunk` helper is four lines and turns the wrong-shape
case into a precise TypeError at the boundary.

## evidence

- `src/retrieval/citations.py` — the `_to_chunk` helper.
- `src/agent/answerer.py` — calls the verifier with `SearchResult`
  objects directly.
- `tests/test_citations.py` — covers both call shapes.

## rollback

Single-file revert. Remove the helper and require callers to pass
`DocumentChunk` objects. Update `src/agent/answerer.py` to unwrap
before the verifier call. The four-suite gate catches any
regression.
