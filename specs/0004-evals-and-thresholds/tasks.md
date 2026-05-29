# tasks: evals-and-thresholds

Spec 0004 is a backfill spec. The four eval suites, the runner, and
the CI workflow already shipped. This ledger records the requirement
IDs and pairs the first one with a DEC.

## Spec ledger

- [x] `specs/0004-evals-and-thresholds/requirements.md` with
  R-EVL-001..036.
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
- [x] `decisions/DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration.md`
  resolves R-EVL-020..023 (Round-6 portable-URI migration; amends
  DEC-EVL-008 with the cross-repo `repo://` + `artifact://` URI
  grammar from athena-site DEC-CDCP-014 plus the two-pass
  emission pattern that fixes the sandbox_image_ref off-by-one).
- [x] `decisions/DEC-EVL-010-supplier-risk-rag-agent-ci-enforces-run-evidence-chain.md`
  resolves R-EVL-024..027 (CI enforcement of the run-evidence
  chain per athena-site DEC-CDCP-015).
- [x] `decisions/DEC-EVL-011-supplier-risk-replay-determinism-test.md`
  resolves R-EVL-028..030 (replay-determinism fixture +
  microsecond-resolution ledger filenames + named CI job;
  amends DEC-EVL-010).
- [x] `decisions/DEC-EVL-012-edgar-refresh-and-adversarial-refusal-suite.md`
  resolves R-EVL-031..033 (live EDGAR refresh script +
  refreshed_corpus fixture + adversarial refusal precision eval
  suite + paired refusal-logic update; amends DEC-EVL-011).
- [x] `decisions/DEC-EVL-013-supplier-risk-rag-agent-chaos-test-suite.md`
  resolves R-EVL-034..036 (chaos test suite covering seven
  mutation classes that verify
  `scripts/validate_run_evidence.py` catches each mutation +
  named `chaos-validation` CI job; amends DEC-EVL-012).

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

## Code added under R-EVL-020..023 (Round-6 portable-URI migration)

- `src/evals/run_evidence.py` URI helpers (`REPO_NAME`,
  `PENDING_SHA_TOKEN`, `repo_uri`, `artifact_uri`,
  `repo_relative`) and the two-pass `derive_sandbox_image_ref`
  signature.
- `src/evals/runner.py` per-suite Run-record assembly now uses
  `repo_uri()` on the input ref and sets `workspace_id` to the
  bare repo identity token.
- `scripts/validate_run_evidence.py` adds the `resolve_uri`
  helper plus the `_REPO_URI_RE` + `_ARTIFACT_URI_RE`
  patterns.
- `scripts/replay_run.py` mirrors the URI regex, accepts the
  legacy `<abs-path>@<sha>` shape during the migration round,
  and treats the `PENDING` placeholder as the implicit pin to
  current HEAD.
- `scripts/finalize_sandbox_ref.py` is the post-commit
  rewrite step that swaps `PENDING` for the data-containing
  commit's SHA.
- `tests/test_run_evidence.py` extends the unit tests with URI
  helpers + `resolve_uri` positive/negative branches.
- `tests/test_replay_run.py` adds a positive test for the
  PENDING auto-resolve path and finalizes the sandbox SHA in
  the prompt-drift and gate-rollup-drift negative tests.
- Regenerated sample at `ops/run-records/run-643dff8f3b9c.json`
  plus `ops/event-ledger/run-643dff8f3b9c.jsonl` emitted under
  the new URI grammar with the finalized SHA in place.

## Code added under R-EVL-031..033 (EDGAR refresh + adversarial refusal suite)

- `scripts/refresh_sample_corpus.py` (three-CIK manifest +
  keyword-overlap truncation + offline-stub fallback).
- `data/refreshed_corpus/chunks.jsonl` + `manifest.json` (live
  EDGAR fixture from NVDA + TSM + AMAT 10-K / 20-F filings).
- `eval_suites/adversarial_refusal_precision.yaml` (10
  adversarial supplier-risk cases).
- `src/agent/refusal.py` (`ADVERSARIAL_PHRASES` set + matching
  branch in `should_refuse`).
- `src/evals/runner.py` (new entries in `GATES`, `GATE_LABELS`,
  `_evaluate_suite`, `_tool_name_for_suite`).
- `ops/run-records/run-c63148a1afa2.json` +
  `ops/event-ledger/run-c63148a1afa2.jsonl` (initial run-evidence
  for the new suite).
- `reports/adversarial_refusal_precision_report.html` +
  `reports/adversarial_refusal_precision_metrics.json` (HTML +
  JSON reports for the initial run).

## Code added under R-EVL-034..036 (chaos test suite for run-evidence validator)

- `tests/test_chaos_run_evidence.py` (`_build_synthetic_root`
  helper + baseline test + seven mutation tests + suite-level
  guard).
- `.github/workflows/run-evidence-gates.yml` `chaos-validation`
  job (ubuntu-latest, uv sync on Python 3.11, pytest on
  `tests/test_chaos_run_evidence.py`).

## Verification

- [x] `python scripts/spec_check.py` exits 0 with R-EVL-001..036
  resolved.
- [x] `python scripts/validate_decisions.py` exits 0 with the new
  DEC parsing clean.
- [x] `python scripts/validate_run_evidence.py` exits 0 against the
  produced ledger + Run record.
- [x] `python -m src.evals.runner --suite all` stays green
  across all four suites.
- [x] `python scripts/replay_run.py --run-id run-643dff8f3b9c`
  exits 0 with `replay_equivalent: true` on all three signals
  when run at the commit recorded in the sample's
  `sandbox_image_ref`.
