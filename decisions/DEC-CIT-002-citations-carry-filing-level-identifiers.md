---
id: DEC-CIT-002-citations-carry-filing-level-identifiers
spec: specs/0006-citation-faithfulness/
requirement: R-CIT-002
date: 2026-05-24
status: approved
reversible: false
decision: |
  Make `Citation` a frozen dataclass with seven fields: `cik`,
  `accession`, `section`, `span_text`, `span_offsets`, `chunk_id`,
  and a free-form `metadata` dict. The `as_dict()` method returns a
  serializable view used by `app.py` to render the citations
  expander. A factory function `citation_from_chunk(chunk,
  span_text, label)` builds a citation from a retrieved chunk and a
  verbatim span, raising on missing spans. Every shipped citation
  in the agent's response carries all seven fields.
alternatives:
  - label: store only the span text and chunk id (drop CIK / accession / section)
    rejected_because: |
      A reviewer auditing a cited claim needs to find the source
      filing. CIK plus accession plus section names the filing
      unambiguously; chunk_id alone points at the in-memory chunk
      but not at the SEC document. The audit story requires the
      filing-level identifiers.
  - label: lazy-load filing identifiers from the chunk on render
    rejected_because: |
      The citation is the audit artifact; embedding the identifiers
      at construction time makes the citation self-describing.
      Lazy-loading at render time couples the rendered citation to
      the in-memory corpus state, which is the wrong direction
      (citations should survive a corpus refresh).
  - label: mutable dataclass for ease of editing
    rejected_because: |
      Citations are evidence. A mutable citation could be edited
      after the verifier signed off, breaking the audit trail. The
      frozen dataclass enforces the contract: a citation is built,
      verified, and shipped without modification.
rationale: |
  The verifier's job is to catch hallucinated citations. A citation
  with only the span text could pass verification (the substring
  exists in some chunk) without naming which filing the substring
  came from. The seven fields together resolve the citation to a
  single source: the SEC document at CIK + accession, the section
  within the document, the chunk inside that section, and the span
  inside the chunk. A reviewer can replay the trace without
  re-running the agent.

  The frozen dataclass is the right shape because the citation is
  the audit artifact. The verifier produces a Pass/Fail; if the
  citation could be edited between verification and rendering, the
  audit trail would be unreliable. The freeze guarantees that what
  the verifier signed off on is what `app.py` rendered.

  The `metadata` dict carries forward-looking fields (company name,
  filing date) without baking them into the dataclass shape. A
  future spec may promote one of those keys to a first-class field;
  today the metadata bag is the escape hatch.
evidence:
  - kind: spec
    ref: specs/0006-citation-faithfulness/
  - kind: doc
    ref: src/retrieval/citations.py (`Citation` frozen dataclass; `as_dict`)
  - kind: doc
    ref: src/retrieval/citations.py (`citation_from_chunk` factory)
  - kind: doc
    ref: app.py (citations expander reads `Citation.as_dict()`)
  - kind: doc
    ref: tests/test_citations.py (verifier tests against the dataclass shape)
rollback: |
  Multi-file revert. The `Citation` shape is consumed by `app.py`,
  the verifier in `src/retrieval/citations.py`, the answerer in
  `src/agent/answerer.py`, the eval suites under
  `eval_suites/citation_faithfulness.yaml`, and the tests under
  `tests/test_citations.py`. Dropping a field would require
  updating every consumer; the `reversible: false` flag in the
  front-matter signals the lock-in. To shrink the shape, ship a
  new dataclass alongside the existing one, migrate consumers, and
  then remove the old shape in a follow-up commit. Re-run the
  four-suite gate after any change.
owner: engineering.implementation
---

## decision

Make `Citation` a frozen dataclass with seven fields: `cik`,
`accession`, `section`, `span_text`, `span_offsets`, `chunk_id`, and
a free-form `metadata` dict. `as_dict()` returns a serializable view.
`citation_from_chunk(chunk, span_text, label)` builds a citation
from a chunk and a verbatim span, raising on missing spans.

## alternatives

- Span text + chunk_id only — loses the audit trail to the source
  filing.
- Lazy-load filing identifiers at render time — couples the rendered
  citation to in-memory corpus state.
- Mutable dataclass — citations could be edited after the verifier
  signed off; audit trail unreliable.

## rationale

The verifier's job is to catch hallucinated citations. The seven
fields resolve a citation to a single source: SEC document at CIK +
accession, section, chunk, span. A reviewer can replay the trace
without re-running the agent. The freeze guarantees that what the
verifier signed off on is what gets rendered.

## evidence

- `src/retrieval/citations.py` — the `Citation` dataclass and the
  `citation_from_chunk` factory.
- `app.py` — the citations expander reads `Citation.as_dict()`.
- `tests/test_citations.py` — verifier tests against the dataclass
  shape.

## rollback

Multi-file revert. The dataclass shape is consumed by `app.py`, the
verifier, the answerer, the eval suite, and the tests. Dropping a
field would require updating every consumer. The `reversible: false`
flag signals the lock-in; shrinking the shape would ship a parallel
dataclass and migrate consumers.
