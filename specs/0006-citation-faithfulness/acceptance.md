# acceptance: citation-faithfulness

## Gates

- `python scripts/voice_lint.py` exits 0 across the new spec files.
- `python scripts/spec_check.py` exits 0 with R-CIT-001 resolved by
  `DEC-CIT-001-verbatim-span-verification-post-generation.md` and
  R-CIT-002..003 listed under `deferred:` in the allowlist.
- `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean.
- `uv run python -m src.evals.runner --suite citation_faithfulness`
  stays at ≥ 0.95.

## Done means

Spec 0006 is done when:

1. The six ledger files land under
   `specs/0006-citation-faithfulness/`.
2. `DEC-CIT-001-*.md` lands under `decisions/`.
3. R-CIT-002 and R-CIT-003 land under `deferred:` in the allowlist.
4. `src/retrieval/citations.py` and `src/agent/answerer.py` are
   unchanged by this spec.

## Explicit non-acceptance

- No edits to `src/retrieval/citations.py`. The verifier code is the
  evidence; this spec records the why.
- No new LLM-as-judge claim-level scoring. That belongs to a future
  experiment (see follow-up 04 in
  `experiments/01-cross-encoder-rerank/notes.md`).
- No verifier disable flag in this spec. If latency becomes
  blocking, the rollback path in `DEC-CIT-001-*.md` names the flag
  pattern; the flag itself ships under a future DEC.
