# traceability: evals-and-thresholds

| Requirement | Design surface | Decision | Planned proof | Owner role |
|---|---|---|---|---|
| R-EVL-001 | `eval_suites/*.yaml` + `src/evals/runner.py` + `.github/workflows/evals.yml` thresholds | `DEC-EVL-001-four-suite-eval-gate-with-thresholds.md` | a CI run on a PR shows the four per-suite numbers and the pass/fail per threshold | `science.proof-gate-runner` |
| R-EVL-002 | `src/evals/runner.py` running against the sample corpus with `HashingEmbedder` + the deterministic verifier | `DEC-EVL-002-deterministic-eval-runs-without-vendor-keys.md` | a repeat CI run produces identical metric numbers without vendor keys | `science.proof-gate-runner` |
| R-EVL-003 | the four suite files plus the `src/evals/runner.py` per-suite metric helpers | `DEC-EVL-003-each-suite-targets-a-distinct-failure-mode.md` | each suite carries its own case shape and failure-mode comment | `science.proof-gate-runner` |
| R-EVL-004 | `src/evals/runner.py` `--json` and `--reranker` flags + `experiments/01-cross-encoder-rerank/{baseline,variant}.json` | `DEC-EVL-004-experiments-re-use-the-same-four-suites-on-baseline-and-variant.md` | the reverted experiment's two JSON artifacts plus its `notes.md` | `science.proof-gate-runner` |
| R-EVL-005 | `ops/RELEASE_LEDGER.md` per-commit entries naming which gates passed | `DEC-EVL-005-eval-results-land-in-release-ledger.md` | the backfilled ledger including the reverted reranker entry | `control.coordinator` |
