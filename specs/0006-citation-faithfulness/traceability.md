# traceability: citation-faithfulness

| Requirement | Design surface | Decision | Planned proof | Owner role |
|---|---|---|---|---|
| R-CIT-001 | `src/retrieval/citations.py` `verify_citations` + `eval_suites/citation_faithfulness.yaml` ≥ 0.95 gate | `DEC-CIT-001-verbatim-span-verification-post-generation.md` | the eval suite numbers across the four-suite runner | `science.proof-gate-runner` |
| R-CIT-002 | `Citation` frozen dataclass with `cik`, `accession`, `section`, `span_text`, `span_offsets`, `chunk_id`, `metadata` | `DEC-CIT-002-citations-carry-filing-level-identifiers.md` | `Citation.as_dict()` round-trips through `app.py` citations expander | `engineering.implementation` |
| R-CIT-003 | `_to_chunk` accepting `DocumentChunk` or any SearchResult-like object | `DEC-CIT-003-verifier-accepts-search-result-and-document-chunk-shapes.md` | a verifier call with raw `SearchResult` objects resolves chunks without unwrap | `engineering.implementation` |
