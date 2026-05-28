---
id: DEC-EVL-007-eval-runner-run-evidence-cross-checks
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-012
amends: DEC-EVL-006-eval-runner-emits-conformant-run-evidence
date: 2026-05-28
status: approved
reversible: true
decision: |
  The eval-suite runner's run-evidence MUST satisfy four cross-checks
  that tie the Run record to its event ledger, plus a Run-level
  required-for-done field set. `scripts/validate_run_evidence.py`
  enforces the cross-checks on every CI run and fails the gate on any
  mismatch.

  Run-level required-for-done fields (a Run whose `status == "done"`
  must populate each of):
  - `prompt_snapshot_hash`
  - `tool_schemas_snapshot_hash`
  - `sandbox_image_ref`
  - `gate_results_summary`

  Required terminal event for a done Run: at least one event in the
  ledger with `type == "gate.run.evidence_recorded"`.

  Cross-checks:
  1. `Run.prompt_snapshot_hash` matches `pipeline.start.payload.prompt_snapshot_hash`.
  2. `Run.tool_schemas_snapshot_hash` matches `pipeline.start.payload.tool_schemas_snapshot_hash`.
  3. `gate.run.evidence_recorded.payload.fields_populated` matches the
     set of replay-equivalence fields populated on the Run record
     (compared as sorted sets).
  4. `Run.gate_results_summary` matches the rollup of `gate.check.passed`
     and `gate.check.failed` event names: `gates_passed` is the sorted
     set of names from `gate.check.passed` events, `gates_failed` is the
     sorted set from `gate.check.failed`, and `all_passed` is true iff
     `gates_failed` is empty.
alternatives:
  - label: validate schema conformance only; skip the four cross-checks
    rejected_because: |
      Schema validation catches field-shape regressions. It does not
      catch the case where two parts of the same Run carry different
      claims: a `pipeline.start` payload says one prompt hash and the
      Run record says another, or `fields_populated` declares a field
      the Run record never populated, or the Run's gate rollup
      contradicts the ledger's gate events. Codex's Round-2 audit
      caught exactly these split-claim regressions on the existing
      sample; the schema accepted each side, but the pair was
      inconsistent. Cross-checks are the discipline that closes the
      gap.
  - label: enforce required-for-done fields but skip the four cross-checks
    rejected_because: |
      Required-for-done catches the case where a done Run is missing a
      field outright. It does not catch the case where the field is
      populated but disagrees with the ledger. Both checks are needed:
      required-for-done covers presence; cross-checks cover consistency.
  - label: emit the cross-checks as warnings instead of failures
    rejected_because: |
      Warnings rot. A non-fatal warning sits in CI output until a
      reviewer notices and acts. The whole point of the gate is to
      catch the inconsistency at commit time, not at audit time. The
      gate runs against the cached schemas with no network call, so
      the cost of failing fast is bounded.
rationale: |
  This DEC amends DEC-EVL-006. DEC-EVL-006 named the emitter contract
  ("the runner emits a conformant ledger plus a Run record"). It did
  not name a cross-check contract between the two artifacts.

  Round-2 of the run-evidence rollout (athena-site commit `bfc735a`)
  amended `event.schema.json` with typed per-event-type payload
  schemas. Codex's audit of this repo's sample ledger
  `run-13f2a48fe8bc.jsonl` then found two failures of the new typed
  payloads:
  - `tool.call.completed` used `tool_id` where the schema requires
    `tool_name`.
  - `gate.run.evidence_recorded` omitted the required `run_id` from
    the payload (the envelope carried it; the payload did not).

  Round-3 (this DEC) fixes the emitter and adds cross-checks so the
  next audit cannot find a sample where the Run record's claims and
  the ledger's claims disagree. The cross-check shape mirrors what a
  downstream consumer (the `trace-to-eval-harness` packet generator) <!-- voice_lint:allow banned-harness -->
  would use to derive a review packet: it walks `pipeline.start` for
  the hash pair, `gate.check.*` for the gate-rollup pair, and
  `gate.run.evidence_recorded.fields_populated` for the
  replay-equivalence claim. Catching the mismatch on the producer side
  means the consumer's packet generator never has to handle the
  inconsistency case.

  Keeping the validator gate's failure mode bounded (exit code 1 plus
  one line per violation to stderr) means a future operator reads the
  CI log and knows exactly which cross-check fired. The four
  cross-checks plus the required-for-done set give a reviewer six
  distinct failure messages that map one-to-one to the six discipline
  rules.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: decision
    ref: decisions/DEC-EVL-006-eval-runner-emits-conformant-run-evidence.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/athena-site/blob/main/decisions/DEC-CDCP-013-typed-event-payload-schemas.md
  - kind: doc
    ref: src/evals/run_evidence.py
  - kind: doc
    ref: src/evals/runner.py
  - kind: doc
    ref: scripts/validate_run_evidence.py
  - kind: doc
    ref: tests/test_run_evidence.py
  - kind: doc
    ref: ops/event-ledger/run-2eab3c611b6a.jsonl
  - kind: doc
    ref: ops/run-records/run-2eab3c611b6a.json
rollback: |
  Drop the `cross_check` extension in
  `scripts/validate_run_evidence.py` back to the round-2 shape that
  only flagged terminal-event-without-record. Drop the
  `REQUIRED_FIELDS_FOR_DONE` and `REPLAY_EQUIVALENCE_FIELDS`
  constants. Drop the seven validator tests in
  `tests/test_run_evidence.py` that depend on the cross-check
  output. Revert the `pipeline.done` emission in
  `src/evals/runner.py` and revert the `tool_name` rename plus the
  `run_id` payload add to keep the producer compatible with the
  round-1 emitter shape. Delete this DEC and the
  `R-EVL-012..R-EVL-015` requirements added to spec 0004. No data
  migration is needed because the ledger files stay append-only and
  the rollback is a code-only revert.
owner: control.coordinator
---

## decision

The eval-suite runner's run-evidence must satisfy four cross-checks
that tie the Run record to its event ledger, plus a Run-level
required-for-done field set covering `prompt_snapshot_hash`,
`tool_schemas_snapshot_hash`, `sandbox_image_ref`, and
`gate_results_summary`. The validator gate at
`scripts/validate_run_evidence.py` enforces both layers on every CI
run.

## alternatives

- Validate schema conformance only: rejected because schema validation
  accepts each artifact in isolation but does not catch the case where
  two halves of the same Run carry contradictory claims. Codex's Round-2
  audit found exactly this regression on the prior sample.
- Enforce required-for-done fields but skip the four cross-checks:
  rejected because required-for-done covers field presence; the
  cross-checks cover field consistency. Both layers are needed.
- Emit the cross-checks as warnings instead of failures: rejected
  because warnings rot and the whole point of the gate is to fail at
  commit time, not at audit time.

## rationale

This DEC amends DEC-EVL-006. The earlier DEC named the emitter
contract; it did not name a cross-check contract between the Run
record and the event ledger. Round-2 of the run-evidence rollout
(athena-site `bfc735a`) introduced typed per-event-type payload
schemas, and Codex's audit found two payload-shape regressions on the
sample ledger this repo shipped under DEC-EVL-006 (`tool_id` instead
of `tool_name`; missing `run_id` on the evidence event payload).

Round-3 fixes the emitter, adds the cross-checks, and regenerates the
sample. The cross-check shape mirrors what a downstream consumer (the
`trace-to-eval-harness` packet generator) would use to derive a <!-- voice_lint:allow banned-harness -->
review packet, so catching the mismatch on the producer side means
the consumer's packet generator never has to handle the inconsistency
case.

## evidence

- `specs/0004-evals-and-thresholds/requirements.md` lists
  `R-EVL-012..R-EVL-015`.
- `athena-site/decisions/DEC-CDCP-013-*` is the source-of-truth schema
  amendment that added typed payload schemas.
- `src/evals/runner.py` carries the fixed emitter plus the new
  `pipeline.done` event with the gate-rollup payload.
- `scripts/validate_run_evidence.py` carries the four cross-checks
  plus the required-for-done enforcement.
- `tests/test_run_evidence.py` carries the positive + six negative
  validator tests.
- `ops/event-ledger/run-2eab3c611b6a.jsonl` +
  `ops/run-records/run-2eab3c611b6a.json` are the regenerated sample
  that satisfies every rule in this DEC.

## rollback

Revert `pipeline.done` emission in the runner and the `tool_name`
rename plus the payload `run_id` add. Drop the `cross_check`
extension in the validator back to the round-2 shape. Drop the seven
validator tests in `test_run_evidence.py`. Delete this DEC and the
`R-EVL-012..R-EVL-015` requirements. No data migration is needed.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-012` Run records whose `status == "done"` populate
  `prompt_snapshot_hash`, `tool_schemas_snapshot_hash`,
  `sandbox_image_ref`, and `gate_results_summary`; the validator
  fails any done Run missing or empty for any of those fields.
- `R-EVL-013` Every Run whose `status == "done"` has at least one
  `gate.run.evidence_recorded` event in its ledger.
- `R-EVL-014` The Run record's `prompt_snapshot_hash` and
  `tool_schemas_snapshot_hash` match the `pipeline.start` event
  payload, and the `gate.run.evidence_recorded.fields_populated`
  matches the set of replay-equivalence fields populated on the Run.
- `R-EVL-015` The Run record's `gate_results_summary` matches the
  rollup of `gate.check.passed` and `gate.check.failed` event names
  in the ledger.
