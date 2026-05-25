# traceability: retrieval

| Requirement | Design surface | Decision | Planned proof | Owner role |
|---|---|---|---|---|
| R-RET-001 | `src/retrieval/ranker.py` weighted-score combination in `HybridRanker.search` | [`DEC-RET-001`](../../decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md) | `tests/test_ranker.py` + `uv run python -m src.evals.runner --suite retrieval_quality` recall@5 ≥ 0.7 | `owner_role: engineering.implementation` |
| R-RET-002 | `src/retrieval/embedder.py` `HashingEmbedder` + the BM25 + cosine + overlap pure-function path | [`DEC-RET-002`](../../decisions/DEC-RET-002-deterministic-hashing-embedder-default.md) | `python -m src.evals.runner --suite all` returns the same recall@5 on repeat runs | `owner_role: science.proof-gate-runner` |
| R-RET-003 | `HybridRanker._matches_filters` reading `cik`, `accession`, `section`, and metadata keys | [`DEC-RET-003`](../../decisions/DEC-RET-003-chunk-metadata-filter-keys-cik-accession-section.md) | `tests/test_ranker.py` filter cases | `owner_role: engineering.implementation` |
| R-RET-004 | `HybridRanker.__init__` `reranker` argument + `src/retrieval/reranker.py` + `experiments/01-cross-encoder-rerank/notes.md` reverted result | [`DEC-RET-004`](../../decisions/DEC-RET-004-opt-in-reranker-via-constructor-and-runner-flag.md) | `python -m src.evals.runner --suite all` defaults to no reranker; the experiment notes record the rationale | `owner_role: science.proof-gate-runner` |
| R-RET-005 | `src/retrieval/index.py` `build_chroma_collection` against a `chromadb.PersistentClient` | [`DEC-RET-005`](../../decisions/DEC-RET-005-chroma-persistence-developer-local-only.md) | developer-local full-ingest run produces a Chroma collection on disk | `owner_role: engineering.implementation` |
