# tasks: evals-and-thresholds

Spec 0004 is a backfill spec. The four eval suites, the runner, and
the CI workflow already shipped. This ledger records the requirement
IDs and pairs the first one with a DEC.

## Spec ledger

- [x] `specs/0004-evals-and-thresholds/requirements.md` with
  R-EVL-001..015.
- [x] `specs/0004-evals-and-thresholds/design.md`.
- [x] `specs/0004-evals-and-thresholds/tasks.md` (this file).
- [x] `specs/0004-evals-and-thresholds/acceptance.md`.
- [x] `specs/0004-evals-and-thresholds/research.md`.
- [x] `specs/0004-evals-and-thresholds/traceability.md`.
- [x] `specs/README.md` lists the spec folder.

## Decision coverage

- [x] `decisions/DEC-EVL-001-four-suite-eval-gate-with-thresholds.md`
  resolves R-EVL-001.
- [x] R-EVL-002..005 resolved by their per-ID DECs.
- [x] `decisions/DEC-EVL-006-eval-runner-emits-conformant-run-evidence.md`
  resolves R-EVL-006..011 (Phase D of the run-evidence rollout).
- [x] `decisions/DEC-EVL-007-eval-runner-run-evidence-cross-checks.md`
  resolves R-EVL-012..015 (Round-3 of the run-evidence rollout;
  amends DEC-EVL-006 with Run-level required-for-done enforcement
  and four cross-checks tying the Run record to its ledger).

## Code under this spec (already shipped, not changed by this spec)

- `eval_suites/retrieval_quality.yaml`
- `eval_suites/citation_faithfulness.yaml`
- `eval_suites/supplier_risk_questions.yaml`
- `eval_suites/refusal_cases.yaml`
- `.github/workflows/evals.yml`

## Code added under R-EVL-006..011 (Phase D run-evidence rollout)

- `src/evals/run_evidence.py` (new emitter module)
- `src/evals/runner.py` (Run + Event ledger emission wired into the
  per-suite loop)
- `scripts/validate_run_evidence.py` (validator gate)
- `ops/schemas-cache/event.schema.json` (cached cross-repo schema)
- `tests/test_run_evidence.py` + `tests/test_run_evidence_integration.py`
- `.github/workflows/gates.yml` (validate_run_evidence step)
- `ops/event-ledger/<run-id>.jsonl` + `ops/run-records/<run-id>.json`
  (sample artifacts from one suite execution)

## Verification

- [x] `python scripts/spec_check.py` exits 0 with R-EVL-001..011
  resolved.
- [x] `python scripts/validate_decisions.py` exits 0 with the new
  DEC parsing clean.
- [x] `python scripts/validate_run_evidence.py` exits 0 against the
  produced ledger + Run record.
- [x] `uv run python -m src.evals.runner --suite all` stays green
  across all four suites.
