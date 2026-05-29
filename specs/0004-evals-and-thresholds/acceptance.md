# acceptance: evals-and-thresholds

## Gates

- `python scripts/voice_lint.py` exits 0 across the new spec files.
- `python scripts/spec_check.py` exits 0 with R-EVL-001..030 each
  resolved by a per-ID DEC.
- `python scripts/validate_decisions.py` exits 0 with the new DECs
  parsing clean.
- `python scripts/validate_run_evidence.py` exits 0 against the
  ledger and Run records emitted by the runner plus the per-replay
  ledger written by `scripts/replay_run.py`.
- `python -m src.evals.runner --suite all` stays green.
- `python scripts/replay_run.py --run-id run-643dff8f3b9c` exits 0
  with `replay_equivalent: true` on all three signals when run at
  the commit recorded in the sample's `sandbox_image_ref` (or, for
  a freshly regenerated sample carrying the PENDING placeholder,
  at any HEAD per the implicit-pin rule from R-EVL-022).
- `python -m pytest tests/test_replay_determinism.py -v` exits 0
  with three replays of `run-643dff8f3b9c` producing one SHA-256
  hash over the three replay-equivalence fields per R-EVL-028.

## Done means

Spec 0004 is done when:

1. The six ledger files land under
   `specs/0004-evals-and-thresholds/`.
2. `DEC-EVL-001-*.md` lands under `decisions/`.
3. R-EVL-002..005 each resolved by their per-ID DEC.
4. R-EVL-006..011 resolved by DEC-EVL-006 (Phase D run-evidence
   rollout) and the runner emits one Run record + JSONL ledger per
   suite execution.
5. R-EVL-012..015 resolved by DEC-EVL-007 (Round-3 run-evidence
   rollout) and the validator enforces Run-level required-for-done
   fields plus four cross-checks tying the Run record to its event
   ledger.
6. R-EVL-016..019 resolved by DEC-EVL-008 (Round-5 equivalence-replay
   rollout) and `scripts/replay_run.py` ships HEAD-strict
   equivalence replay emitting one `run.evidence.replayed` event
   per replay into a new per-replay ledger file plus a detailed
   comparison report under `ops/replay-records/<run-id>/`.
7. R-EVL-020..023 resolved by DEC-EVL-009 (Round-6 portable-URI
   migration) and the eval-suite emitter produces portable
   `repo://supplier-risk-rag-agent@<sha>/<path>` URIs in
   `sandbox_image_ref` and `inputs[].ref` plus the bare repo
   identity token on `workspace_id`. The validator and replay
   command accept both URI shapes and the legacy local path
   during the migration round.
   `scripts/finalize_sandbox_ref.py` closes the two-pass
   emission loop so the recorded SHA pins the data-bearing
   commit instead of its parent.

## Explicit non-acceptance

- No threshold changes under spec 0004. The current thresholds
  (recall@5 >= 0.70, faithfulness >= 0.95, refusal precision >=
  0.85) stay in place; changing them requires a future DEC.
- No new eval suite added. A future spec may add a claim-level
  faithfulness suite (see experiment 04 follow-up) once the design
  lands.
- Run-evidence emission MUST NOT change the per-suite metrics or the
  pass/fail outcome of the eval gate. The emitter is a write-side
  observer; the run-record bytes carry the evidence trail, not the
  judgement.
