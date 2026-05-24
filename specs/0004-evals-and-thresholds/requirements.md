# requirements: evals-and-thresholds

## Scope

Spec 0004 backfills the eval discipline this repo ships. Four named
suites under `eval_suites/*.yaml` plus the runner under
`src/evals/runner.py` plus the CI workflow `.github/workflows/evals.yml`
gate every prompt and model change. This spec records the requirements
that gate set answers.

## Requirements

### R-EVL-001: four named eval suites block PRs with explicit thresholds

WHEN a PR changes any prompt, model id, retrieval weight, or
verifier rule, THE SYSTEM SHALL run the four eval suites
(retrieval-quality, citation-faithfulness, supplier-risk-questions,
refusal-cases) and SHALL block merge if any suite drops below its
threshold (retrieval recall@5 ≥ 0.7, citation faithfulness ≥ 0.95,
refusal precision ≥ 0.85).

Acceptance:
- `eval_suites/retrieval_quality.yaml`,
  `eval_suites/citation_faithfulness.yaml`,
  `eval_suites/supplier_risk_questions.yaml`, and
  `eval_suites/refusal_cases.yaml` carry the four case sets.
- `src/evals/runner.py` walks each suite and prints per-suite metrics.
- `.github/workflows/evals.yml` runs the runner on push and PR.
- The thresholds are non-zero-defect: any single regression below the
  threshold fails the gate.

### R-EVL-002: eval cases are checked-in and deterministic

WHEN the eval runner executes in CI, THE SYSTEM SHALL produce the
same per-suite metrics without network access or vendor API keys.

Acceptance:
- The retrieval and refusal suites consume the in-memory sample
  corpus and the deterministic hybrid ranker.
- The citation-faithfulness suite verifies cited spans against the
  retrieved chunks using `src/retrieval/citations.py` without an LLM
  call.
- A re-run on the same commit produces identical metric numbers.

### R-EVL-003: each suite targets a distinct failure mode

WHEN a suite fires a regression, THE SYSTEM SHALL name the failure
mode the suite covers, so engineers can map a failed gate to a
narrow class of root cause.

Acceptance:
- `retrieval_quality` covers chunk recall (the right chunks make it
  into the top-k).
- `citation_faithfulness` covers verbatim-span verification (the
  cited span exists in a retrieved chunk).
- `supplier_risk_questions` covers end-to-end answer composition
  (required terms present, expected accessions cited).
- `refusal_cases` covers abstention precision (out-of-scope or
  unsupported queries get refused, not paraphrased).

### R-EVL-004: experiment ablations re-use the same suites

WHEN an experiment under `experiments/NN-*/` proposes a variant of
the production pipeline, THE SYSTEM SHALL run the same four suites
on baseline and variant and record the per-suite deltas.

Acceptance:
- `src/evals/runner.py` accepts a `--json` output flag and a variant
  flag (e.g. `--reranker`).
- Each experiment folder carries `baseline.json`, `variant.json`,
  and a `notes.md` with the decision and the deltas.
- The reverted cross-encoder experiment under
  `experiments/01-cross-encoder-rerank/` documents the format.

### R-EVL-005: eval failures land in the release ledger

WHEN a release passes or fails any of the four suites, THE SYSTEM
SHALL record which gates the release passed in
`ops/RELEASE_LEDGER.md` so a future reviewer can read the eval
history without re-running CI.

Acceptance:
- `ops/RELEASE_LEDGER.md` carries one entry per released commit and
  names which gates passed.
- A reverted experiment (such as the cross-encoder reranker) is
  recorded as a release entry that names the gate that failed.
- Future automation may parse the ledger; today it is human-edited.
