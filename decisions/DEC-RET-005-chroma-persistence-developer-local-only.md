---
id: DEC-RET-005-chroma-persistence-developer-local-only
spec: specs/0002-retrieval/
requirement: R-RET-005
date: 2026-05-24
status: approved
reversible: true
decision: |
  Provide a `build_chroma_collection` helper in
  `src/retrieval/index.py` that writes already chunked filings to a
  local `chromadb.PersistentClient` rooted at a caller-supplied
  path, scoped to developer-local full-EDGAR runs. The Streamlit
  demo, the eval runner, and CI continue to use the in-memory
  `HybridRanker` over the sample JSONL corpus. The Chroma path on
  disk is gitignored; no Chroma artifact lands in the repo. Chroma
  itself stays in the production dependency set because the helper
  imports it at the top of `index.py` and the test suite imports
  the module.
alternatives:
  - label: make Chroma the default index for CI and the demo
    rejected_because: |
      The deployed Streamlit demo runs over a small sample corpus
      where in-memory BM25 plus the hashing embedder beats Chroma
      on cold-start latency and removes the persist-path
      configuration surface. CI also benefits from zero filesystem
      state between runs; a Chroma collection on a build agent
      would need cleanup tooling for no measured eval lift on the
      20-case retrieval_quality suite.
  - label: build a Chroma collection and commit it to the repo
    rejected_because: |
      Chroma collections are SQLite plus per-segment files; they
      are large binary artifacts that churn on every ingestion
      and bloat the git history. The sample JSONL corpus stays
      checked in; the helper produces a fresh collection on
      demand from the same JSONL.
  - label: write a thin in-memory shim against the Chroma API
    rejected_because: |
      Adds a parallel implementation that has to stay in sync
      with the real Chroma client. The helper is a one-screen
      function that calls
      `client.get_or_create_collection().upsert(...)`; a shim
      would be more code than the real call.
  - label: pick a different vector store (FAISS, Qdrant, sqlite-vec)
    rejected_because: |
      Each adds either a heavier native dependency (FAISS, Qdrant)
      or a less-mature local store (sqlite-vec). Chroma ships
      with a `PersistentClient` that works out of the box on the
      developer-local target, has no server process, and has
      first-class Python ergonomics. The Streamlit and Anthropic
      ecosystems both ship examples against it.
rationale: |
  The deployed demo and the CI evals do not need a persistent
  vector store at the current corpus size. The in-memory ranker
  with hashing embeddings is faster and stateless. The Chroma
  helper exists for the developer-local workflow where a
  full-EDGAR ingestion produces thousands of chunks across
  hundreds of filings, and the in-memory rebuild-per-query cost
  starts to matter.

  Gitignoring the Chroma path keeps the repo small and removes a
  data-staleness failure mode. The developer regenerates the
  collection from the same JSONL the in-memory ranker uses, so
  the two paths agree on the chunk set; only the storage
  substrate differs.

  Chroma stays in `[project.dependencies]` because
  `src/retrieval/index.py` imports `chromadb` inside the helper
  body. The import is module-local to keep import-time cost
  bounded, but the package has to resolve for the test that
  imports `index.py` to load. Moving Chroma to an optional group
  would push the import behind a guard; the cleaner shape is one
  required dependency that the helper calls into.
evidence:
  - kind: spec
    ref: specs/0002-retrieval/requirements.md (R-RET-005)
  - kind: doc
    ref: src/retrieval/index.py (build_chroma_collection +
      DocumentChunk.chroma_metadata)
  - kind: doc
    ref: src/retrieval/ranker.py (HybridRanker holds the in-memory
      path; the Chroma helper is not used by the ranker)
  - kind: doc
    ref: .gitignore (Chroma persist path entries)
  - kind: doc
    ref: src/ingest/ (the ingestion path that produces chunks
      consumed by both the in-memory ranker and the Chroma helper)
  - kind: decision
    ref: DEC-DEP-001-byok-streamlit-no-committed-keys.md (the
      deployed demo posture this helper does not change)
rollback: |
  Two-step revert. Remove the `build_chroma_collection` function
  from `src/retrieval/index.py` and drop `chromadb` from
  `[project.dependencies]` in `pyproject.toml`. The in-memory
  ranker is unaffected; CI and the deployed demo continue to run
  against the JSONL sample corpus. Any developer-local workflow
  that built a Chroma collection should commit the produced
  artifacts elsewhere or re-implement the helper in a personal
  fork. Re-run `python -m src.evals.runner --suite all` after
  the change to confirm the four-suite gate still passes.
owner: engineering.implementation
---

## decision

Provide a `build_chroma_collection` helper in
`src/retrieval/index.py` scoped to developer-local full-EDGAR
runs. The Streamlit demo, the eval runner, and CI continue to use
the in-memory `HybridRanker` over the sample JSONL corpus. The
Chroma path on disk is gitignored.

## alternatives

- Make Chroma the default for CI and the demo — adds cold-start
  latency and stateful build-agent files for no recall lift on
  the saturated 20-case suite.
- Commit a Chroma collection to the repo — large binary artifacts
  that churn on every ingestion and bloat git history.
- Thin in-memory shim against the Chroma API — parallel
  implementation that has to stay in sync with the real client.
- Switch vector store (FAISS, Qdrant, sqlite-vec) — heavier
  native dependency or less-mature local store; Chroma's
  `PersistentClient` covers the developer-local target with no
  server process.

## rationale

The deployed demo and CI evals do not need a persistent vector
store at the current corpus size. The in-memory ranker is faster
and stateless. The helper exists for the developer-local
workflow where a full-EDGAR ingestion produces thousands of
chunks and the rebuild-per-query cost starts to matter.
Gitignoring the Chroma path keeps the repo small and the
developer regenerates the collection from the same JSONL the
in-memory ranker reads, so both paths agree on the chunk set.

## evidence

- `src/retrieval/index.py` — the `build_chroma_collection`
  function and `DocumentChunk.chroma_metadata` projection.
- `src/retrieval/ranker.py` — the in-memory ranker that does not
  call the helper.
- `.gitignore` — entries that keep the Chroma persist path out
  of git history.
- `src/ingest/` — the ingestion path that produces chunks for
  both consumers.
- `DEC-DEP-001-byok-streamlit-no-committed-keys.md` — the
  deployed demo posture this helper does not change.

## rollback

Remove the `build_chroma_collection` function from
`src/retrieval/index.py` and drop `chromadb` from
`[project.dependencies]` in `pyproject.toml`. The in-memory
ranker is unaffected; CI and the deployed demo continue to run
against the JSONL sample corpus. Re-run the four-suite gate to
confirm.
