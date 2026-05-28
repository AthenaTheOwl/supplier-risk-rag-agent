# tasks: evals-and-thresholds

Spec 0004 is a backfill spec. The four eval suites, the runner, and
the CI workflow already shipped. This ledger records the requirement
IDs and pairs the first one with a DEC.

## Spec ledger

- [x] `specs/0004-evals-and-thresholds/requirements.md` with
  R-EVL-001..019.
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
- [x] `decisions/DEC-EVL-008-eval-replay-command.md` resolves
  R-EVL-016..019 (Round-5 of the run-evidence rollout; amends
  DEC-EVL-007 with the equivalence-replay command shipped as
  `scripts/replay_run.py`).

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

## Code added under R-EVL-016..019 (Round-5 equivalence-replay rollout)

- `scripts/replay_run.py` (HEAD-strict equivalence-replay command)
- `tests/test_replay_run.py` (positive path plus four negative
  paths: HEAD mismatch, missing Run record, prompt drift, rubric
  drift)
- `ops/event-ledger/replay-<run-id>-<timestamp>.jsonl` (per-replay
  ledger carrying the `run.evidence.replayed` event)
- `ops/replay-records/<run-id>/<replay-event-id>.json` (detailed
  comparison report)
- Regenerated `ops/run-records/run-2eab3c611b6a.json` plus
  `ops/event-ledger/run-2eab3c611b6a.jsonl` so the recorded
  `sandbox_image_ref` SHA pins the current commit (no code drift
  between the Round-3 producing commit and the Round-5 commit; the
  prompt and tool-surface hashes stay byte-identical, only the
  sandbox SHA, the event timestamps, and the event UUIDs change).

## Verification

- [x] `python scripts/spec_check.py` exits 0 with R-EVL-001..019
  resolved.
- [x] `python scripts/validate_decisions.py` exits 0 with the new
  DEC parsing clean.
- [x] `python scripts/validate_run_evidence.py` exits 0 against the
  produced ledger + Run record plus the per-replay ledger.
- [x] `python -m src.evals.runner --suite all` stays green
  across all four suites.
- [x] `python scripts/replay_run.py --run-id run-2eab3c611b6a`
  exits 0 with `replay_equivalent: true` on all three signals.
