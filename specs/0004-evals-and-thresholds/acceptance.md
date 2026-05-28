# acceptance: evals-and-thresholds

## Gates

- `python scripts/voice_lint.py` exits 0 across the new spec files.
- `python scripts/spec_check.py` exits 0 with R-EVL-001..011 each
  resolved by a per-ID DEC.
- `python scripts/validate_decisions.py` exits 0 with the new DECs
  parsing clean.
- `python scripts/validate_run_evidence.py` exits 0 against the
  ledger and Run records emitted by the runner.
- `uv run python -m src.evals.runner --suite all` stays green.

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
