# tasks: retrieval

Spec 0002 is a backfill spec. The code already shipped; this ledger
records the requirements the code answers and pairs the first one
with a DEC.

## Spec ledger

- [x] `specs/0002-retrieval/requirements.md` with R-RET-001..005.
- [x] `specs/0002-retrieval/design.md`.
- [x] `specs/0002-retrieval/tasks.md` (this file).
- [x] `specs/0002-retrieval/acceptance.md`.
- [x] `specs/0002-retrieval/research.md`.
- [x] `specs/0002-retrieval/traceability.md`.
- [x] `specs/README.md` lists the spec folder.

## Decision coverage

- [x] `decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md`
  resolves R-RET-001.
- [ ] R-RET-002..005 land in `decisions/.spec-check-allowlist.yaml`
  under `deferred:` until a backfill pass writes their DECs.

## Code under this spec (already shipped, not changed by this spec)

- `src/retrieval/ranker.py`
- `src/retrieval/embedder.py`
- `src/retrieval/index.py`
- `src/retrieval/reranker.py`
- `src/retrieval/citations.py` (citation verification lives in this
  package; the requirement set for the verifier is owned by spec
  0006, not this one).

## Verification

- [x] `python scripts/spec_check.py` exits 0 with R-RET-001 resolved
  by its DEC and R-RET-002..005 deferred via the allowlist.
- [x] `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean against the cross-repo schema.
- [x] `uv run pytest --cov=src --cov-fail-under=70` stays green; the
  retrieval modules are unchanged.
- [x] `uv run python -m src.evals.runner --suite all` stays green; the
  ranker output is unchanged.
