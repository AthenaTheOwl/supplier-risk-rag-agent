# acceptance: evals-and-thresholds

## Gates

- `python scripts/voice_lint.py` exits 0 across the new spec files.
- `python scripts/spec_check.py` exits 0 with R-EVL-001 resolved by
  `DEC-EVL-001-four-suite-eval-gate-with-thresholds.md` and
  R-EVL-002..005 listed under `deferred:` in the allowlist.
- `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean.
- `uv run python -m src.evals.runner --suite all` stays green.

## Done means

Spec 0004 is done when:

1. The six ledger files land under
   `specs/0004-evals-and-thresholds/`.
2. `DEC-EVL-001-*.md` lands under `decisions/`.
3. R-EVL-002..005 land under `deferred:` in the allowlist with
   one-line notes.
4. The eval suites, runner, and workflow stay unchanged by this spec.

## Explicit non-acceptance

- No edits to `eval_suites/*.yaml`, `src/evals/`, or
  `.github/workflows/evals.yml`. The eval gate is the evidence; this
  spec records the why.
- No threshold changes. The current thresholds (recall@5 ≥ 0.70,
  faithfulness ≥ 0.95, refusal precision ≥ 0.85) stay in place;
  changing them requires a future DEC.
- No new suite added. A future spec may add a claim-level
  faithfulness suite (see experiment 04 follow-up) once the design
  lands.
