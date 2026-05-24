# tasks: citation-faithfulness

Spec 0006 is a backfill spec. The verifier and the eval suite
already shipped. This ledger records the requirement IDs and pairs
the first one with a DEC.

## Spec ledger

- [x] `specs/0006-citation-faithfulness/requirements.md` with
  R-CIT-001..003.
- [x] `specs/0006-citation-faithfulness/design.md`.
- [x] `specs/0006-citation-faithfulness/tasks.md` (this file).
- [x] `specs/0006-citation-faithfulness/acceptance.md`.
- [x] `specs/0006-citation-faithfulness/research.md`.
- [x] `specs/0006-citation-faithfulness/traceability.md`.
- [x] `specs/README.md` lists the spec folder.

## Decision coverage

- [x] `decisions/DEC-CIT-001-verbatim-span-verification-post-generation.md`
  resolves R-CIT-001.
- [ ] R-CIT-002 and R-CIT-003 land in
  `decisions/.spec-check-allowlist.yaml` under `deferred:` until a
  backfill pass writes their DECs.

## Code under this spec (already shipped, not changed by this spec)

- `src/retrieval/citations.py`
- `src/agent/answerer.py` (the call site)
- `eval_suites/citation_faithfulness.yaml`

## Verification

- [x] `python scripts/spec_check.py` exits 0 with R-CIT-001 resolved
  and R-CIT-002..003 deferred.
- [x] `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean.
- [x] `uv run python -m src.evals.runner --suite citation_faithfulness`
  stays green at ≥ 0.95.
