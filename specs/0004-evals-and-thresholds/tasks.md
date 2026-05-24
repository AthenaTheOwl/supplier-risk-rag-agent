# tasks: evals-and-thresholds

Spec 0004 is a backfill spec. The four eval suites, the runner, and
the CI workflow already shipped. This ledger records the requirement
IDs and pairs the first one with a DEC.

## Spec ledger

- [x] `specs/0004-evals-and-thresholds/requirements.md` with
  R-EVL-001..005.
- [x] `specs/0004-evals-and-thresholds/design.md`.
- [x] `specs/0004-evals-and-thresholds/tasks.md` (this file).
- [x] `specs/0004-evals-and-thresholds/acceptance.md`.
- [x] `specs/0004-evals-and-thresholds/research.md`.
- [x] `specs/0004-evals-and-thresholds/traceability.md`.
- [x] `specs/README.md` lists the spec folder.

## Decision coverage

- [x] `decisions/DEC-EVL-001-four-suite-eval-gate-with-thresholds.md`
  resolves R-EVL-001.
- [ ] R-EVL-002..005 land in `decisions/.spec-check-allowlist.yaml`
  under `deferred:` until a backfill pass writes their DECs.

## Code under this spec (already shipped, not changed by this spec)

- `eval_suites/retrieval_quality.yaml`
- `eval_suites/citation_faithfulness.yaml`
- `eval_suites/supplier_risk_questions.yaml`
- `eval_suites/refusal_cases.yaml`
- `src/evals/runner.py`
- `.github/workflows/evals.yml`

## Verification

- [x] `python scripts/spec_check.py` exits 0 with R-EVL-001 resolved
  and R-EVL-002..005 deferred.
- [x] `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean.
- [x] `uv run python -m src.evals.runner --suite all` stays green
  across all four suites.
