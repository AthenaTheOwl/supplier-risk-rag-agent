# traceability: retrieval

| Requirement | Design surface | Planned proof | Owner role |
|---|---|---|---|
| R-RET-001 | `src/retrieval/ranker.py` weighted-score combination in `HybridRanker.search` | `DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md` + `tests/test_ranker.py` + `uv run python -m src.evals.runner --suite retrieval_quality` recall@5 ≥ 0.7 | `engineering.implementation` |
| R-RET-002 | `src/retrieval/embedder.py` `HashingEmbedder` + the BM25 + cosine + overlap pure-function path | `python -m src.evals.runner --suite all` returns the same recall@5 on repeat runs; allowlisted under `deferred:` until DEC-RET-002 lands | `science.proof-gate-runner` |
| R-RET-003 | `HybridRanker._matches_filters` reading `cik`, `accession`, `section`, and metadata keys | `tests/test_ranker.py` filter cases; allowlisted under `deferred:` until DEC-RET-003 lands | `engineering.implementation` |
| R-RET-004 | `HybridRanker.__init__` `reranker` argument + `src/retrieval/reranker.py` + `experiments/01-cross-encoder-rerank/notes.md` reverted result | `python -m src.evals.runner --suite all` defaults to no reranker; the experiment notes record the rationale; allowlisted under `deferred:` until DEC-RET-004 lands | `science.proof-gate-runner` |
| R-RET-005 | `src/retrieval/index.py` `build_chroma_collection` against a `chromadb.PersistentClient` | developer-local full-ingest run produces a Chroma collection on disk; allowlisted under `deferred:` until DEC-RET-005 lands | `engineering.implementation` |
