# traceability: citation-faithfulness

| Requirement | Design surface | Decision | Planned proof | Owner role |
|---|---|---|---|---|
| R-CIT-001 | `src/retrieval/citations.py` `verify_citations` + `eval_suites/citation_faithfulness.yaml` ≥ 0.95 gate | `DEC-CIT-001-verbatim-span-verification-post-generation.md` | the eval suite numbers across the four-suite runner | `owner_role: science.proof-gate-runner` |
| R-CIT-002 | `Citation` frozen dataclass with `cik`, `accession`, `section`, `span_text`, `span_offsets`, `chunk_id`, `metadata` | `DEC-CIT-002-citations-carry-filing-level-identifiers.md` + amendment `DEC-CIT-002-amendment-reversibility-mitigation.md` (forward route via `CitationV2` dual-type; see `docs/citation-shape-evolution.md`) | `Citation.as_dict()` round-trips through `app.py` citations expander | `owner_role: engineering.implementation` |
| R-CIT-003 | `_to_chunk` accepting `DocumentChunk` or any SearchResult-like object | `DEC-CIT-003-verifier-accepts-search-result-and-document-chunk-shapes.md` | a verifier call with raw `SearchResult` objects resolves chunks without unwrap | `owner_role: engineering.implementation` |
| R-CIT-004 | `src/agent/portfolio_rollup.py` parser and rollup model + `app.py` `Investor rollup` tab | `DEC-CIT-004-deterministic-investor-rollup-over-verified-evidence.md` | `tests/test_portfolio_rollup.py` parser, verified-card, and refused-no-match cases | `owner_role: engineering.implementation` |
