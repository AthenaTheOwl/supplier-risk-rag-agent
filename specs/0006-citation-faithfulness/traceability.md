# traceability: citation-faithfulness

| Requirement | Design surface | Planned proof | Owner role |
|---|---|---|---|
| R-CIT-001 | `src/retrieval/citations.py` `verify_citations` + `eval_suites/citation_faithfulness.yaml` ≥ 0.95 gate | `DEC-CIT-001-verbatim-span-verification-post-generation.md` + the eval suite numbers across the four-suite runner | `science.proof-gate-runner` |
| R-CIT-002 | `Citation` frozen dataclass with `cik`, `accession`, `section`, `span_text`, `span_offsets`, `chunk_id`, `metadata` | `Citation.as_dict()` round-trips through `app.py` citations expander; allowlisted under `deferred:` until DEC-CIT-002 lands | `engineering.implementation` |
| R-CIT-003 | `_to_chunk` accepting `DocumentChunk` or any SearchResult-like object | a verifier call with raw `SearchResult` objects resolves chunks without unwrap; allowlisted under `deferred:` until DEC-CIT-003 lands | `engineering.implementation` |
