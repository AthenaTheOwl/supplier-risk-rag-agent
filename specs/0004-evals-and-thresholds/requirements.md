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

### R-EVL-006: eval-suite runner emits a conformant Event ledger

WHEN the eval-suite runner executes any of the four suites, THE
SYSTEM SHALL append an event-ledger file at
`ops/event-ledger/<run-id>.jsonl` whose lines validate against the
cached `ops/schemas-cache/event.schema.json`.

Acceptance:
- Each suite execution writes at least one `pipeline.start`, one
  `tool.call.completed`, one `gate.check.passed` or
  `gate.check.failed`, and one `gate.run.evidence_recorded` event.
- Every line in the JSONL file parses as JSON and conforms to the
  cached event schema.
- The `run_id` field on each event matches the file name.

### R-EVL-007: eval-suite runner emits a conformant Run record

WHEN the eval-suite runner finishes a suite execution, THE SYSTEM
SHALL write `ops/run-records/<run-id>.json` whose body validates
against the cached `ops/schemas-cache/run.schema.json`.

Acceptance:
- Required fields populated: `id`, `spec_id` = the suite YAML path,
  `agent_id` = `<llm-provider>:<llm-model>`, `runtime` =
  `supplier-risk-rag-agent-evals`, `workspace_id` = the repo path,
  `started_at`, `finished_at`, `status` (`done` or `failed`),
  `inputs` (one `eval_suite` entry).
- The validator gate `scripts/validate_run_evidence.py` exits zero
  against the produced file.

### R-EVL-008: prompt and tool-schema hashes are always populated

WHEN the eval-suite runner emits a Run record, THE SYSTEM SHALL
populate the `prompt_snapshot_hash` and `tool_schemas_snapshot_hash`
fields with SHA-256 digests of canonicalized prompt and retrieval
or LLM surface inputs.

Acceptance:
- `prompt_snapshot_hash` covers the extraction, answer, and refusal
  prompt files under `src/agent/prompts/`.
- `tool_schemas_snapshot_hash` covers the ranker config (weights and
  `top_k`), the LLM provider and model, the embedding model, and the
  reranker config when one is in use.
- Both digests match the schema pattern `^[a-f0-9]{64}$`.

### R-EVL-009: sandbox_image_ref pins the producing commit

WHEN the eval-suite runner emits a Run record, THE SYSTEM SHALL
populate `sandbox_image_ref` with `<repo-path>@<HEAD-SHA>` so a
reviewer can pin the replay context to the producing commit.

Acceptance:
- The field is populated whenever the runner can resolve `git
  rev-parse HEAD` against the repo working tree.
- The field is omitted (not populated with placeholder text) when
  `git rev-parse` fails.

### R-EVL-010: gate_results_summary aggregates fired gate events

WHEN the eval-suite runner emits a Run record, THE SYSTEM SHALL
populate `gate_results_summary` from the `gate.check.passed` and
`gate.check.failed` events fired during the suite execution.

Acceptance:
- Names in `gates_passed` and `gates_failed` come from the
  `payload.gate_name` field of each event.
- `all_passed` is true iff `gates_failed` is empty.
- For the four shipped suites the gate names are
  `recall_at_5_threshold`,
  `citation_faithfulness_threshold`,
  `answer_quality_threshold`,
  `refusal_precision_threshold`.

### R-EVL-011: validate_run_evidence gates commits

WHEN a commit lands on the main branch, THE SYSTEM SHALL run
`scripts/validate_run_evidence.py` as a CI gate and SHALL block the
merge if any ledger line or Run record fails to validate.

Acceptance:
- The validator runs in `.github/workflows/gates.yml` alongside
  `spec_check.py`, `validate_decisions.py`, and the others.
- A schema-violating record produces exit code 1 with the violation
  list on stderr.
- The validator runs offline against the cached schemas; no network
  call is required.
