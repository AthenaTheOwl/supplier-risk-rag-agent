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

### R-EVL-020: run-evidence emitter produces portable repo:// URIs

WHEN the eval-suite runner emits a Run record, THE SYSTEM SHALL
populate `Run.sandbox_image_ref` as
`repo://supplier-risk-rag-agent@<sha>/`, every
`Run.inputs[].ref` as
`repo://supplier-risk-rag-agent@<sha>/<rel-path>`, and
`Run.workspace_id` as the bare repo identity token
`supplier-risk-rag-agent` per the cross-repo URI grammar defined
in athena-site DEC-CDCP-014.

Acceptance:
- `Run.sandbox_image_ref` matches
  `^repo://supplier-risk-rag-agent@([a-f0-9]{40}|PENDING)/$`.
- Every `Run.inputs[].ref` whose path lives inside the repo
  matches
  `^repo://supplier-risk-rag-agent@([a-f0-9]{40}|PENDING)/.+$`.
- `Run.workspace_id` equals the literal string
  `supplier-risk-rag-agent`.
- The producer-side URI helpers (`repo_uri`, `artifact_uri`,
  `repo_relative`) live in `src/evals/run_evidence.py`.

### R-EVL-021: validator resolves repo:// URIs and accepts legacy paths

WHEN `scripts/validate_run_evidence.py` runs, THE SYSTEM SHALL
ship a `resolve_uri` helper that returns a local file path for
`repo://` URIs, returns `None` for `artifact://` URIs, and
passes legacy local paths through unchanged.

Acceptance:
- `resolve_uri("repo://supplier-risk-rag-agent@<sha>/<path>")`
  returns `<portfolio-root>/supplier-risk-rag-agent/<path>` as
  a `Path` object.
- `resolve_uri("artifact://supplier-risk-rag-agent/<id>")`
  returns `None`.
- `resolve_uri("/abs/legacy/path")` returns
  `Path("/abs/legacy/path")` unchanged.
- A malformed URI that does not match either scheme falls
  through to the legacy-path branch.

### R-EVL-022: replay extracts SHA from URI grammar with PENDING tolerance

WHEN `scripts/replay_run.py` parses the recorded
`Run.sandbox_image_ref`, THE SYSTEM SHALL pull the SHA out of
either the new `repo://supplier-risk-rag-agent@<sha>/` shape
(via the same regex the validator uses) or the legacy
`<abs-path>@<sha>` shape (via a split on the last `@`). The
HEAD-strict pre-flight SHALL treat the `PENDING` placeholder
as "current HEAD is the implicit pin" so a freshly regenerated
sample replays without an intervening finalize step.

Acceptance:
- A Run record with the new URI shape and a real 40-char SHA
  drives HEAD-strict against the SHA group.
- A Run record with the legacy `<abs-path>@<sha>` shape still
  parses (backwards compatibility during the migration round).
- A Run record carrying
  `repo://supplier-risk-rag-agent@PENDING/` runs replay against
  current HEAD without erroring on the placeholder.

### R-EVL-023: sandbox_image_ref off-by-one fixed via two-pass emission

WHEN the eval-suite runner emits a Run record, THE SYSTEM SHALL
record `PENDING` in place of the sandbox SHA, and
`scripts/finalize_sandbox_ref.py` SHALL rewrite the placeholder
to the SHA of the commit that physically contains the
data-bearing Run record on disk.

Acceptance:
- The fresh-emit Run record carries
  `sandbox_image_ref == "repo://supplier-risk-rag-agent@PENDING/"`.
- `scripts/finalize_sandbox_ref.py --run-id <id> --sha <sha>`
  rewrites the placeholder to
  `repo://supplier-risk-rag-agent@<sha>/` in place, preserving
  the existing serialization shape (sorted keys, two-space
  indent, trailing newline).
- The finalize step is idempotent: rewriting an
  already-finalized record with the same SHA is a no-op;
  rewriting with a different SHA requires `--force`.
- After finalize, the recorded SHA matches the
  data-containing commit, not its parent.

### R-EVL-024: CI workflow exists and triggers correctly

WHEN a contributor opens a pull request against `main` or pushes
directly to `main`, THE SYSTEM SHALL run the
`.github/workflows/run-evidence-gates.yml` workflow on an
`ubuntu-latest` runner under Python 3.11 and SHALL run, in a
single `universal-gates` job, the contract gates that depend only
on this repo's working tree: schema-cache-freshness, voice-lint,
bom-check, spec-check, decisions-validation, the four sibling
typed-artifact validators (roles, tools, policies, skills, dreams),
typed-event-payload-validation, and pytest under uv.

Acceptance:
- The workflow file at
  `.github/workflows/run-evidence-gates.yml` parses as valid YAML.
- The workflow's `on:` trigger names `pull_request` (no branch
  filter) and `push: branches: [main]`.
- The `universal-gates` job sets `runs-on: ubuntu-latest` and
  `python-version: "3.11"`.
- The `universal-gates` job calls every script named above as a
  named step.
- A clean checkout passes every step on a green run.

### R-EVL-025: CI workflow gates packet generation and validation

WHEN the `run-evidence-gates.yml` workflow runs, THE SYSTEM SHALL
carry a `packet-and-replay` job that checks out the sibling
consumer repo at a sibling path under the workspace, pip-installs
it as editable, runs `python -m trace_to_eval evidence
from-cdcp-events ops/event-ledger/run-643dff8f3b9c.jsonl --out
/tmp/packet.json --portfolio-root <workspace>`, then runs
`python -m trace_to_eval evidence validate /tmp/packet.json`.

Acceptance:
- The `packet-and-replay` job carries two `actions/checkout@v4`
  steps: one for this repo and one for the sibling consumer repo.
- The packet-generation step exits 0 against the canonical sample.
- The packet-validation step exits 0 against the generated packet.
- The `--portfolio-root` flag points at the workspace root so the
  sibling consumer's `repo://` URI resolver maps producer refs to
  local files inside the runner's workspace.

### R-EVL-026: CI workflow replay smoke checks out recorded sandbox SHA

WHEN the `run-evidence-gates.yml` workflow's `packet-and-replay`
job reaches the replay-smoke step, THE SYSTEM SHALL extract the
recorded sandbox SHA from `Run.sandbox_image_ref` via `jq` + a
sed regex matching `^repo://[^@]+@([a-f0-9]{40})/.*`, run
`git checkout <sandbox-sha>` against a full-history clone
(`fetch-depth: 0`), and run
`python scripts/replay_run.py --run-id run-643dff8f3b9c`.

Acceptance:
- The repo checkout step sets `fetch-depth: 0` so the recorded
  SHA is reachable in the runner.
- The sandbox-SHA extraction step fails (exit 1) with a clear
  diagnostic when `sandbox_image_ref` does not match the
  `repo://` URI grammar with a 40-char SHA.
- The replay step exits 0 only when `replay_equivalent: true`
  on all three signals (`prompt_snapshot_hash`,
  `tool_schemas_snapshot_hash`, `gate_results_summary`).
- A mutated canonical sample (e.g. a swapped
  `gate_results_summary`) trips the replay step's divergence
  branch and turns the job red.

### R-EVL-027: no contract gate is non-blocking

WHEN any step of the `run-evidence-gates.yml` workflow runs, THE
SYSTEM SHALL ensure no contract gate carries `continue-on-error:
true` and no step bypasses pre-commit hooks via `--no-verify` or
equivalent. Every gate listed in athena-site DEC-CDCP-015 blocks
the merge.

Acceptance:
- A grep for `continue-on-error: true` against
  `.github/workflows/run-evidence-gates.yml` returns no matches.
- A grep for `--no-verify` against the same file returns no
  matches.
- A red gate (e.g. a failed pytest assertion) turns the job red
  and blocks the merge per GitHub's default branch-protection
  contract.

### R-EVL-028: replay-determinism fixture asserts hash-equal across reruns

WHEN an operator (or CI) runs the replay-determinism fixture, THE
SYSTEM SHALL replay the canonical sample `run-643dff8f3b9c`
`RERUNS` times (default 3, override via the `RERUNS` env var) at
the recorded sandbox SHA, extract the three replay-equivalence
fields from each fresh replay record's `comparison.<field>.fresh`
slot, canonicalize the tuple via
`json.dumps(triple, sort_keys=True, separators=(",", ":"))`,
SHA-256-hash the byte string, and assert every replay produced the
same hash. On divergence THE SYSTEM SHALL write a failure bundle
to `artifacts/failbundles/` carrying `determinism_failure.json`,
`trace_0.json`, and `trace_1.json` for the first two diverging
replays, and fail loudly with the bundle path in the assertion
message.

Acceptance:
- `tests/test_replay_determinism.py` exists and parses as Python.
- The fixture saves the current HEAD (branch name when on a
  branch, otherwise the SHA) before the loop and restores it on
  teardown including the failure paths.
- The fixture checks out the recorded sandbox SHA from
  `Run.sandbox_image_ref` before the replay loop.
- On a clean working tree at the recorded SHA, the fixture
  passes (`hashes` is a set of size one) and removes the
  per-replay ledgers and reports it created during the loop.
- On divergence, the failure bundle lands under
  `artifacts/failbundles/` and the assertion message names the
  bundle path relative to the repo root.

### R-EVL-029: replay ledger filenames carry microsecond resolution

WHEN `scripts/replay_run.py` builds a per-replay ledger filename,
THE SYSTEM SHALL produce a label of shape
`%Y%m%dT%H%M%S.<microseconds>Z` so three replays inside the same
wall-clock second land on three distinct paths under
`ops/event-ledger/`. The label SHALL come from a single
`datetime.now(UTC)` call so the seconds field and the microseconds
field stay consistent across the format-string boundary.

Acceptance:
- `scripts/replay_run.py._now_filename_iso` returns a string
  matching `^[0-9]{8}T[0-9]{6}\.[0-9]{6}Z$`.
- Three consecutive calls to `_now_filename_iso()` inside the same
  wall-clock second return three distinct strings.
- The replay-records glob in the determinism fixture
  (`replay-<run-id>-*.jsonl`) matches both the legacy per-second
  format and the new microsecond format during the migration
  round.
- The determinism fixture's set-difference assertion that counts
  fresh ledgers per iteration succeeds with `len(fresh_ledgers) == 1`
  on every iteration.

### R-EVL-030: CI workflow carries named replay-determinism job

WHEN the `run-evidence-gates.yml` workflow runs, THE SYSTEM SHALL
carry a named `replay-determinism` job (separate from
`universal-gates` and `packet-and-replay`) that runs on
`ubuntu-latest` under Python 3.11, checks out the repo with
`fetch-depth: 0`, syncs dev deps under uv, runs
`uv run pytest tests/test_replay_determinism.py -v --no-cov` with
`RERUNS=3`, and uploads `artifacts/failbundles/` on failure via
`actions/upload-artifact@v4`.

Acceptance:
- The workflow file parses as valid YAML and lists
  `replay-determinism` as a distinct job under `jobs:`.
- The job carries no `continue-on-error: true` on any step.
- The job's checkout step sets `fetch-depth: 0` so the recorded
  sandbox SHA is reachable in the runner.
- The job's failure-bundle upload step uses
  `if: failure()` and `if-no-files-found: ignore`.
- A red determinism fixture turns the job red and blocks the
  merge per GitHub's default branch-protection contract.

### R-EVL-031: live EDGAR refresh script writes a bounded fixture

WHEN an operator runs the EDGAR refresh wrapper script, THE SYSTEM
SHALL fetch one annual filing from each of three configured CIKs
(NVDA, TSM, AMAT), keyword-rank the resulting chunks against a
supplier-risk vocabulary, truncate to two chunks per CIK, and write
the fixture to `data/refreshed_corpus/chunks.jsonl` plus a refresh
manifest to `data/refreshed_corpus/manifest.json`. The canonical
sample corpus at `data/sample_corpus/` SHALL NOT be touched.

Acceptance:
- `scripts/refresh_sample_corpus.py` exists and parses as Python.
- The script reads a three-CIK manifest (NVDA, TSM, AMAT) and
  calls `refresh_edgar_corpus` with `max_per_cik=1` and
  `filing_types=["10-K", "20-F"]`.
- The script truncates each CIK's chunk set by keyword overlap
  with the `RISK_KEYWORDS` vocabulary and keeps the top two
  chunks per CIK.
- The script falls back to an offline-stub fixture when the SEC
  fetch fails; the refresh manifest's `source` field records
  which path produced the fixture (`live_edgar` or `offline_stub`).
- The output JSONL loads through `load_jsonl_corpus` without a
  separate parser.

### R-EVL-032: adversarial refusal precision suite covers in-scope-looking adversarial queries

WHEN the eval-suite runner runs the
`adversarial_refusal_precision` suite, THE SYSTEM SHALL load 10
adversarial supplier-risk cases from
`eval_suites/adversarial_refusal_precision.yaml`, evaluate
abstention against each case via `evaluate_abstention`, and gate
the run at `refusal_precision >= 0.85`. The agent's refusal logic
SHALL refuse any query whose lowercased text matches a phrase in
the `ADVERSARIAL_PHRASES` set in `src/agent/refusal.py`.

Acceptance:
- `eval_suites/adversarial_refusal_precision.yaml` carries 10
  adversarial cases, each marked `expected_refusal: true` with an
  `expected_behavior` label.
- `src/agent/refusal.py` carries the `ADVERSARIAL_PHRASES` set
  plus a new branch in `should_refuse` that triggers when any
  phrase matches the lowercased query.
- `src/evals/runner.py` carries `adversarial_refusal_precision`
  under `GATES`, `GATE_LABELS`, `_evaluate_suite`, and
  `_tool_name_for_suite`.
- The four pre-existing eval suites (retrieval_quality,
  citation_faithfulness, supplier_risk_questions, refusal_cases)
  stay green at the same scores after the refusal-logic update.
- `python -m src.evals.runner --suite adversarial_refusal_precision`
  exits 0 with a 1.000 refusal precision score against the 10
  shipped cases.

### R-EVL-033: adversarial refusal suite emits conformant run evidence

WHEN the eval-suite runner finishes the
`adversarial_refusal_precision` suite, THE SYSTEM SHALL write a
Run record at `ops/run-records/<run-id>.json` and a ledger at
`ops/event-ledger/<run-id>.jsonl` that pass
`scripts/validate_run_evidence.py`. Reports at
`reports/adversarial_refusal_precision_report.html` and
`reports/adversarial_refusal_precision_metrics.json` SHALL carry
the same data in the report shape the existing suites use.

Acceptance:
- The Run record carries `spec_id ==
  "eval_suites/adversarial_refusal_precision.yaml"` and the
  required-for-done replay fields (`prompt_snapshot_hash`,
  `tool_schemas_snapshot_hash`, `sandbox_image_ref`,
  `gate_results_summary`).
- The ledger carries `pipeline.start`, `tool.call.completed`,
  one `gate.check.passed` or `gate.check.failed`,
  `pipeline.done`, and `gate.run.evidence_recorded` events with
  the matching `run_id`.
- `scripts/validate_run_evidence.py` exits zero against the
  produced ledger and Run record.
- The HTML and JSON reports under `reports/` carry the same
  per-suite metric shape as the existing
  `baseline_eval_report.html`.

### R-EVL-034: chaos test suite verifies the validator against seven mutation classes

WHEN an operator (or CI) runs the chaos test suite, THE SYSTEM
SHALL copy the canonical sample (`run-643dff8f3b9c`) into a
synthetic root under `tmp_path`, apply each of seven mutation
classes (M1..M7) against the Run record or the event ledger, run
`scripts/validate_run_evidence.py` against the mutated artifacts,
and assert the validator exits non-zero with a stderr message
naming the broken rule. The canonical sample on disk SHALL NOT
be modified by any test.

Acceptance:
- `tests/test_chaos_run_evidence.py` exists and parses as Python.
- The suite carries a baseline test that asserts the unmutated
  canonical sample passes the validator (exit code 0).
- The suite carries one test per mutation class
  (M1..M7) plus a suite-level guard counting the expected
  mutation test names.
- Each mutation test asserts the validator exits non-zero AND the
  stderr names the broken rule (the assertion fails loudly when
  the validator returns exit code 0, because a zero exit on a
  mutated sample names a real validator gap).
- The canonical sample on disk at
  `ops/run-records/run-643dff8f3b9c.json` and
  `ops/event-ledger/run-643dff8f3b9c.jsonl` is byte-identical
  before and after the suite runs.

### R-EVL-035: chaos mutation classes cover all three validator layers

WHEN the chaos test suite runs, THE SYSTEM SHALL cover the
validator's three enforcement layers (typed-event-payload
validation via the cached event schema's oneOf discriminator,
four cross-checks tying the Run record to its ledger, and the
required-for-done block on done Runs) via the seven mutation
classes.

Acceptance:
- M1 mutates `Run.prompt_snapshot_hash` to a different valid-shaped
  digest and asserts cross-check 1 trips with the
  `prompt_snapshot_hash mismatch` diagnostic.
- M2 mutates `Run.tool_schemas_snapshot_hash` and asserts
  cross-check 2 trips with the `tool_schemas_snapshot_hash
  mismatch` diagnostic.
- M3 inserts a phantom gate name into
  `Run.gate_results_summary.gates_passed` and asserts cross-check
  4 trips with the `gate_results_summary mismatch` diagnostic.
- M4 removes the terminal `gate.run.evidence_recorded` event from
  the ledger and asserts the required-event check trips with the
  `no gate.run.evidence_recorded event in the ledger`
  diagnostic.
- M5 drops `prompt_snapshot_hash` from the `pipeline.start`
  event's payload and asserts the typed-event-payload validation
  rejects the event with the `is not valid under any of the
  given schemas` envelope phrase plus the `pipeline.start`
  event type surfaced in stderr.
- M6 mutates
  `gate.run.evidence_recorded.payload.fields_populated` to claim
  the `determinism` field (not populated on the canonical sample)
  and asserts cross-check 3 trips with the `does not match
  replay-equivalence fields populated on Run` diagnostic.
- M7 keeps `Run.status == "done"` but removes
  `sandbox_image_ref` and asserts the validator exits non-zero
  with `sandbox_image_ref` named in stderr.

### R-EVL-036: CI workflow carries named chaos-validation job

WHEN the `run-evidence-gates.yml` workflow runs, THE SYSTEM SHALL
carry a named `chaos-validation` job (separate from
`universal-gates`, `packet-and-replay`, and
`replay-determinism`) that runs on `ubuntu-latest` under Python
3.11, syncs dev deps under uv, and runs
`uv run pytest tests/test_chaos_run_evidence.py -v --no-cov`.

Acceptance:
- The workflow file parses as valid YAML and lists
  `chaos-validation` as a distinct job under `jobs:`.
- The job carries no `continue-on-error: true` on any step.
- The job bypasses no pre-commit hooks via `--no-verify` or
  equivalent.
- A red chaos fixture turns the job red and blocks the merge
  per GitHub's default branch-protection contract.

### R-EVL-037: schemas-cache mirrors upstream systems-thinking fields

WHEN a contributor edits a DEC, a dream candidate, or a Run
record under this repo, THE SYSTEM SHALL resolve the four optional
systems-thinking fields (`systems_map`,
`transferable_principle`, `falsification_test`,
`adoption_ladder`) against `ops/schemas-cache/decision.schema.json`,
`ops/schemas-cache/dream-output.schema.json`, and
`ops/schemas-cache/run.schema.json`, all three byte-identical to
the upstream amendment at athena-site under DEC-CDCP-020.

Acceptance:
- `python scripts/check_schema_cache_freshness.py` exits 0.
- Each of the three cached schemas declares the four fields
  under `properties` with type strings (`string`, `string`,
  `string`, `object`).
- A DEC carrying the four fields validates against the cached
  schema without error.

### R-EVL-038: AGENTS.md names the systems-thinking discipline

WHEN a coding agent (or a new author) reads `.agents/AGENTS.md`,
THE SYSTEM SHALL present a top-level "Systems-thinking discipline
(per DEC-CDCP-020)" section that names the four fields, the
WARN-now-FAIL-later ratchet, and the 30-day organic-adoption
window.

Acceptance:
- `.agents/AGENTS.md` carries a section whose heading matches
  `Systems-thinking discipline (per DEC-CDCP-020)`.
- The section names all four fields (`systems_map`,
  `transferable_principle`, `falsification_test`,
  `adoption_ladder`) and the 30-day ratchet language.
- The section sits above the existing "Coding style" section so
  every author hits the discipline on first read.

### R-EVL-039: validate_decisions emits a non-fatal WARN on missing fields

WHEN `python scripts/validate_decisions.py` runs against the
repo's DEC set, THE SYSTEM SHALL emit a stderr WARN line for each
DEC whose `status` is `approved` and whose front-matter is missing
any of the four systems-thinking fields. Exit code SHALL stay 0
so the bootstrap-friendly default holds until a future amendment
DEC ratchets the warning to FAIL.

Acceptance:
- Running the script against the current repo prints a WARN
  block to stderr listing the historical DECs missing the four
  fields.
- The script exits 0 (`echo $?` returns 0) on a green run with
  WARN entries present.
- A DEC carrying all four fields produces no WARN entry against
  its path.
- The three retrofitted DECs (DEC-EVL-011..013) produce no WARN
  entry; the remaining 29 historical DECs produce one WARN entry
  each until a future coverage pass.

### R-EVL-040: three most recent DECs carry the four systems-thinking fields

WHEN a reviewer reads the front-matter of the three most recent
DECs in `decisions/`, THE SYSTEM SHALL present the four
systems-thinking fields populated with substantive content on
each of DEC-EVL-011, DEC-EVL-012, and DEC-EVL-013.

Acceptance:
- DEC-EVL-011 carries `systems_map`,
  `transferable_principle`, `falsification_test`, and
  `adoption_ladder` keys with non-empty content; the
  `adoption_ladder` object carries `minimum_viable`,
  `mid_adoption`, `full_adoption`, and `monitoring_signals`.
- DEC-EVL-012 carries the same four fields with the same
  `adoption_ladder` shape.
- DEC-EVL-013 carries the same four fields with the same
  `adoption_ladder` shape.
- `python scripts/validate_decisions.py` emits no WARN against
  any of the three retrofitted DECs.
