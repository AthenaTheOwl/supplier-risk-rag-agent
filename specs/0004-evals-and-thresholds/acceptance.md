# acceptance: evals-and-thresholds

## Gates

- `python scripts/voice_lint.py` exits 0 across the new spec files.
- `python scripts/spec_check.py` exits 0 with R-EVL-001..019 each
  resolved by a per-ID DEC.
- `python scripts/validate_decisions.py` exits 0 with the new DECs
  parsing clean.
- `python scripts/validate_run_evidence.py` exits 0 against the
  ledger and Run records emitted by the runner plus the per-replay
  ledger written by `scripts/replay_run.py`.
- `python -m src.evals.runner --suite all` stays green.
- `python scripts/replay_run.py --run-id run-2eab3c611b6a` exits 0
  with `replay_equivalent: true` on all three signals when run at
  the commit recorded in the sample's `sandbox_image_ref`.

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
