# acceptance: retrieval

## Gates

- `python scripts/voice_lint.py` exits 0 across the new spec files.
- `python scripts/spec_check.py` exits 0 with R-RET-001 resolved by
  `DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md` and
  R-RET-002..005 listed under `deferred:` in
  `decisions/.spec-check-allowlist.yaml`.
- `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean against `decision.schema.json`.
- `uv run pytest --cov=src --cov-fail-under=70` stays green.
- `uv run python -m src.evals.runner --suite all` stays green.

## Done means

Spec 0002 is done when:

1. The six ledger files land under `specs/0002-retrieval/`.
2. `DEC-RET-001-*.md` lands under `decisions/`.
3. R-RET-002..005 land under `deferred:` in the allowlist, each with
   a one-line note pointing at the next backfill pass.
4. The retrieval modules under `src/retrieval/` are unchanged by this
   spec.

## Explicit non-acceptance

- No edits to `src/retrieval/*.py`. The code is the evidence; this
  spec records the why.
- No DEC files for R-RET-002..005 in this pass. They get DECs as
  later backfill passes pick them up; until then the allowlist
  records the gap.
- No new ranker weights, no new reranker default, no new index
  backend.
