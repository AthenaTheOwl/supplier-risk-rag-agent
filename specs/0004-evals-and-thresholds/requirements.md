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

### R-EVL-012: Run records carry required-for-done replay fields

WHEN the eval-suite runner finishes a suite execution with
`status == "done"`, THE SYSTEM SHALL populate `prompt_snapshot_hash`,
`tool_schemas_snapshot_hash`, `sandbox_image_ref`, and
`gate_results_summary` on the Run record.

Acceptance:
- A Run with `status == "done"` and any of those four fields missing
  or empty fails `scripts/validate_run_evidence.py` with a clear
  message naming the absent field.
- Other Run statuses (`running`, `needs_review`, `failed`,
  `cancelled`) are not subject to this rule; absence of replay fields
  on a non-done Run is acceptable.

### R-EVL-013: a done Run has a terminal evidence event

WHEN a Run record's `status` is `done`, THE SYSTEM SHALL have at
least one `gate.run.evidence_recorded` event in the matching
`ops/event-ledger/<run-id>.jsonl` file.

Acceptance:
- A done Run whose ledger lacks any `gate.run.evidence_recorded`
  event fails `scripts/validate_run_evidence.py`.
- The validator names the run_id and the missing event type in the
  failure output.

### R-EVL-014: snapshot hashes match between Run and pipeline.start

WHEN the eval-suite runner emits a Run record and the matching
`pipeline.start` event, THE SYSTEM SHALL ensure
`Run.prompt_snapshot_hash` equals the event payload's
`prompt_snapshot_hash`, `Run.tool_schemas_snapshot_hash` equals the
event payload's `tool_schemas_snapshot_hash`, and the
`gate.run.evidence_recorded.payload.fields_populated` set equals the
set of replay-equivalence fields populated on the Run record.

Acceptance:
- A Run whose `prompt_snapshot_hash` disagrees with the
  `pipeline.start` payload fails the validator.
- A Run whose `tool_schemas_snapshot_hash` disagrees with the
  `pipeline.start` payload fails the validator.
- An `gate.run.evidence_recorded` event whose `fields_populated`
  declares a field that the Run record does not carry (or omits a
  field that the Run record does carry) fails the validator.

### R-EVL-015: gate_results_summary matches the gate.check.* rollup

WHEN the eval-suite runner emits a Run record, THE SYSTEM SHALL
ensure `Run.gate_results_summary` matches the rollup of
`gate.check.passed` and `gate.check.failed` events fired in the
matching ledger.

Acceptance:
- `gates_passed` on the Run equals the sorted set of `gate_name`
  values from `gate.check.passed` events.
- `gates_failed` on the Run equals the sorted set of `gate_name`
  values from `gate.check.failed` events.
- `all_passed` on the Run is true iff `gates_failed` is empty.
- Any mismatch fails the validator with a message naming both sides
  of the disagreement.

### R-EVL-016: replay_run.py is the canonical equivalence-replay command

WHEN an operator wants to verify that a recorded eval-suite Run
still produces the same run-evidence signals against the current
working tree, THE SYSTEM SHALL provide `scripts/replay_run.py
--run-id run-<id>` as the canonical replay command. The command
loads `ops/run-records/<run-id>.json` plus
`ops/event-ledger/<run-id>.jsonl` and exits 1 with a clear
diagnostic when either file is missing.

Acceptance:
- A `--run-id` that matches no file under `ops/run-records/` exits
  1 with a `Run record not found` message naming the missing path.
- A Run record present without a matching ledger file exits 1 with
  an `event ledger not found` message.
- The command honors the same
  `SUPPLIER_RISK_RAG_RUN_RECORDS_DIR` and
  `SUPPLIER_RISK_RAG_EVENT_LEDGER_DIR` env vars the runner uses,
  plus `SUPPLIER_RISK_RAG_REPLAY_RECORDS_DIR` for the per-replay
  records dir.

### R-EVL-017: replay is HEAD-strict against sandbox_image_ref

WHEN `scripts/replay_run.py` runs, THE SYSTEM SHALL parse the SHA
out of the recorded `Run.sandbox_image_ref` and SHALL exit 1 when
the current `git rev-parse HEAD` does not equal that SHA.

Acceptance:
- HEAD mismatch produces a stderr line carrying both the recorded
  SHA and the current HEAD plus a `git checkout <sha>` hint.
- A Run record whose `sandbox_image_ref` does not parse (missing
  `@` separator, empty SHA) exits 1 with a clear message instead
  of running the comparison against an unpinned commit.
- HEAD match proceeds to the suite re-execution.

### R-EVL-018: replay compares three replay-equivalence signals

WHEN `scripts/replay_run.py` reaches the comparison step, THE
SYSTEM SHALL compare `prompt_snapshot_hash`,
`tool_schemas_snapshot_hash`, and `gate_results_summary` between
the recorded Run and the fresh re-run. `replay_equivalent` is true
iff all three match; the command exits 1 on any divergence.

Acceptance:
- A mutated `prompt_snapshot_hash` on the recorded Run trips
  divergence and the printed summary names
  `prompt_snapshot_hash: MISMATCH`.
- A mutated `gate_results_summary` on the recorded Run trips
  divergence and the printed summary names
  `gate_results_summary: MISMATCH`.
- The comparison treats `gate_results_summary.gates_passed` and
  `gates_failed` as sets (sort-insensitive), and the `all_passed`
  bool as a strict equality.

### R-EVL-019: replay emits run.evidence.replayed into a new ledger file

WHEN `scripts/replay_run.py` finishes the comparison, THE SYSTEM
SHALL append one `run.evidence.replayed` event to a NEW per-replay
ledger file at
`ops/event-ledger/replay-<run-id>-<ISO-timestamp>.jsonl` and write
a detailed comparison report at
`ops/replay-records/<run-id>/<replay-event-id>.json`. The original
ledger file and the original Run record SHALL NOT be modified.

Acceptance:
- The per-replay ledger carries exactly one event whose
  `type == "run.evidence.replayed"` and whose payload carries
  `run_id`, `packet_ref`, `replay_equivalent`, and
  `replay_method == "equivalence"`.
- The event validates against the `run.evidence.replayed` branch of
  the cached `event.schema.json`.
- The comparison report carries per-signal `recorded`/`fresh`
  values plus the per-signal `match` flag.
- The source ledger file at
  `ops/event-ledger/<run-id>.jsonl` is byte-identical before and
  after the replay command runs.
