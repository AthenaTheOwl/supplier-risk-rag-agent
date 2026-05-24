# requirements: retrieval

## Scope

Spec 0002 backfills the retrieval subsystem that already ships under
`src/retrieval/`. The deterministic hybrid ranker, the Chroma
persistence helper, the local hashing embedder, and the optional
cross-encoder reranker all landed before the CDCP scaffold. This spec
names the requirements those modules answer so each one can carry a
DEC reference (or an allowlist entry until backfill).

The spec does not change code. It records the requirement IDs the
existing files already satisfy.

## Requirements

### R-RET-001: hybrid retrieval combines BM25, vector, and term overlap

WHEN the agent searches the indexed filing chunks for a query, THE
SYSTEM SHALL combine a BM25 score, a cosine similarity over chunk
embeddings, and a query/chunk term overlap ratio into a single ranked
score per chunk.

Acceptance:
- `src/retrieval/ranker.py` carries a `HybridRanker.search` that
  computes BM25, cosine, and overlap per chunk.
- The combined score uses fixed weights (BM25 at 0.60, vector at 0.25,
  overlap at 0.15) when the query and chunk share at least one term.
- Chunks with zero query/chunk overlap are scored at `0.03 * vector`
  so unrelated chunks fall out of the top-k.
- Tests under `tests/test_ranker.py` confirm the weighted score order
  on the sample corpus.

### R-RET-002: retrieval is deterministic for CI evals

WHEN the eval runner executes against the sample corpus without
network access, THE SYSTEM SHALL return the same ranked chunk order
on every run.

Acceptance:
- The default embedder is a local hashing embedder
  (`src/retrieval/embedder.py`) that does not call any remote API.
- The BM25 index, the cosine score, and the overlap count are pure
  functions of the in-memory corpus.
- `python -m src.evals.runner --suite all` produces a stable
  recall@5 number under repeated runs.

### R-RET-003: chunk metadata supports filtered retrieval

WHEN a caller passes a filter dict (by `cik`, `accession`, `section`,
or a metadata key) to `HybridRanker.search`, THE SYSTEM SHALL drop
chunks whose metadata does not match before ranking.

Acceptance:
- `HybridRanker._matches_filters` reads the four filter keys.
- List, tuple, and set values match by membership; scalar values match
  by equality.
- The ranker preserves the same weighted-score formula for the
  surviving chunks.

### R-RET-004: a reranker is opt-in, not default

WHEN a caller wants a learned reranker on top of the hybrid score,
THE SYSTEM SHALL accept a `reranker` argument to `HybridRanker` that
pulls a wider candidate pool and reorders the top-k, while keeping
the default behavior reranker-free.

Acceptance:
- `HybridRanker.__init__` accepts a `reranker` and `candidate_pool`
  argument.
- The default value of `reranker` is `None`; absent a reranker the
  weighted score order is the final order.
- The optional cross-encoder lives at `src/retrieval/reranker.py` and
  loads only when callers ask for it.
- The reverted experiment under `experiments/01-cross-encoder-rerank/`
  documents the rationale for keeping the reranker opt-in.

### R-RET-005: Chroma persistence is available for full-corpus runs

WHEN a developer runs full EDGAR ingestion outside CI, THE SYSTEM
SHALL provide a helper that writes the chunks to a local Chroma
collection so retrieval at larger corpus sizes does not rebuild the
in-memory index per query.

Acceptance:
- `src/retrieval/index.py` exposes `build_chroma_collection` against a
  `chromadb.PersistentClient` rooted at a caller-supplied path.
- The default Streamlit demo and CI evals do not call this helper;
  they use the in-memory ranker over the sample corpus.
- The Chroma path is treated as a developer-local artifact and is
  gitignored.
