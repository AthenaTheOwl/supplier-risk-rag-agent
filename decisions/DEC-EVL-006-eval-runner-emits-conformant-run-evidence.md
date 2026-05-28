---
id: DEC-EVL-006-eval-runner-emits-conformant-run-evidence
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-006
date: 2026-05-27
status: approved
reversible: true
decision: |
  The eval-suite runner MUST emit a conformant Event ledger plus a
  final Run record per suite execution, with the replay-equivalence
  fields populated where derivable. The ledger lands at
  `ops/event-ledger/<run-id>.jsonl` and the Run record lands at
  `ops/run-records/<run-id>.json`; both conform to the cached
  cross-repo schemas mirrored from athena-site under
  `ops/schemas-cache/`. The validator gate at
  `scripts/validate_run_evidence.py` walks both directories on every
  CI run and exits non-zero on schema violations.
alternatives:
  - label: continue with metrics-only --json output
    rejected_because: |
      The existing `--json` flag captures per-suite metrics but
      writes no event timeline and no replay-equivalence fields. The
      amendment to `run.schema.json` in athena-site (DEC-CDCP-011)
      added the six new fields so cross-repo consumers can read a
      review packet without grepping a metrics file. Without an
      emitter that writes the new fields, the fields stay dead
      letters and the bridge to the consumer side (Codex's
      `trace-to-eval evidence from-cdcp-events` CLI in commit
      bfd1d48) has nothing to read.
  - label: emit only the Run record, skip the per-suite JSONL ledger
    rejected_because: |
      A Run record alone records the rollup but not the timeline. The
      consumer's packet generator needs `gate.check.*` and
      `tool.call.*` events to populate gate and tool lists in the
      run-evidence packet shape defined by the sibling consumer
      repo's `schemas/run-evidence.schema.json`. The ledger is the
      source of those events.
  - label: populate all six replay-equivalence fields including
      determinism and checkpoint_ref
    rejected_because: |
      The eval suites ship without an explicit `determinism:` block;
      the runner does no sampling against the sample corpus, so the
      seed/temperature/top_p triple has no derivable values today.
      The repo has no managed-task-runtime checkpoint store, so
      there is no checkpoint to reference. Populating those fields
      with placeholder values would lie about replay equivalence. The
      schema treats absence as "not derivable", which is the honest
      record. A suite that adds an explicit `determinism:` block to
      its YAML gets the field populated automatically.
  - label: write the ledger but not the Run record
    rejected_because: |
      Symmetric inverse of the previous alternative. Consumers split
      the packet shape into a Run rollup plus an event timeline; a
      ledger-only world breaks the cross-check the validator does
      ("ledger carries terminal event but no matching Run record").
      The Run record is the single artifact a reviewer reads first.
rationale: |
  This is Phase D of the run-evidence rollout that started with
  DEC-CDCP-011 in athena-site (commit f314fd7), which amended
  `run.schema.json` with six replay-equivalence fields. Phase B
  shipped the first emitter in procurement-negotiation-lab
  (DEC-FACTORY-007 + commit cbc02d4 + sample run-cb524eb06115).
  Phase B.1 (Codex commit bfd1d48 in the sibling consumer repo)
  shipped the consumer side: a `run-evidence.schema.json` packet
  format and a `trace-to-eval evidence from-cdcp-events` CLI that
  reads a CDCP event log and produces a packet. The missing piece in
  this repo was the emitter that writes the new schema fields in the
  first place.

  Without this DEC the schema fields stay dead letters here: the
  producer side never writes them, the consumer side has nothing to
  read. Naming the bridge in writing also makes it explicit which
  fields the eval runner can derive today (the two snapshot hashes,
  the repo-HEAD sandbox ref, the gate rollup) versus which ones wait
  for future work (determinism knobs, checkpoint refs).

  Keeping the emitter reversible via a task-level flag
  (`--no-emit-evidence`) and the validator gate (gates can be
  relaxed for emergency commits) means the discipline is opt-out by
  intent, not opt-in by accident.

  The eval-suite runner is the right Run boundary in this repo. The
  repo has no factory pipeline; each suite execution is the unit of
  work that carries a prompt surface, a tool surface, and a gate
  outcome. The four suites map one-to-one to four distinct failure
  modes (DEC-EVL-003), so per-suite Run records carry the right
  granularity for a reviewer.

  Phase D.1 (separate agent) will pipe one of this repo's sample
  ledgers through `trace-to-eval evidence from-cdcp-events` to
  produce a bridge demo packet, closing the loop between this
  emitter and the consumer side.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/athena-site/blob/main/decisions/DEC-CDCP-011-run-schema-replay-equivalence-fields.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/procurement-negotiation-lab/blob/main/decisions/DEC-FACTORY-007-factory-emits-conformant-run-evidence.md
  - kind: doc
    ref: src/evals/run_evidence.py
  - kind: doc
    ref: src/evals/runner.py
  - kind: doc
    ref: scripts/validate_run_evidence.py
  - kind: doc
    ref: ops/schemas-cache/run.schema.json
  - kind: doc
    ref: ops/schemas-cache/event.schema.json
  - kind: doc
    ref: .github/workflows/gates.yml
rollback: |
  Remove the run-evidence emission calls from
  `src/evals/runner.py` (revert the runner-wiring commit), drop the
  `validate_run_evidence` step from
  `.github/workflows/gates.yml`, delete
  `scripts/validate_run_evidence.py` and
  `src/evals/run_evidence.py`, then delete the
  `R-EVL-006..011` requirements from spec 0004 and remove this DEC.
  The cached `event.schema.json` stays because other validators may
  need it. No data migration is needed because the ledger and record
  files are append-only audit trails with no foreign-key fan-out.
  Re-run `uv run python -m src.evals.runner --suite all` after the
  rollback to confirm the original metrics-only behavior.
owner: control.coordinator
---

## decision

The eval-suite runner emits a conformant Event ledger plus a final
Run record per suite execution, with the six replay-equivalence
fields populated where derivable. The ledger lands at
`ops/event-ledger/<run-id>.jsonl`; the Run record lands at
`ops/run-records/<run-id>.json`. A validator gate enforces
conformance to the cross-repo schemas on every CI run.

## alternatives

- Continue with metrics-only `--json` output: rejected because the
  new schema fields would never be written and the bridge to the
  consumer side would have nothing to read.
- Emit only the Run record and skip the ledger: rejected because the
  packet generator needs the timeline to populate gate and tool
  lists.
- Populate all six fields including determinism and checkpoint_ref:
  rejected because the eval suites ship without an explicit
  `determinism:` block and the repo has no checkpoint store; the
  schema treats absence as "not derivable".
- Emit the ledger but skip the Run record: rejected because the
  validator cross-check pairs a terminal event with a matching Run
  record by design.

## rationale

DEC-CDCP-011 in athena-site amended `run.schema.json` with six
replay-equivalence fields. Phase B shipped the first emitter in
procurement-negotiation-lab (DEC-FACTORY-007). Codex's commit
bfd1d48 in the sibling consumer repo shipped the consumer side: a
`run-evidence.schema.json` packet format and a
`trace-to-eval evidence from-cdcp-events` CLI. Without an emitter
that populates the new schema fields here, the fields are dead
letters and the bridge between agents and engineering-grade trust
does not exist in this repo. This DEC names the bridge.

## evidence

- `specs/0004-evals-and-thresholds/requirements.md` lists the
  `R-EVL-006..011` requirements this DEC resolves.
- `athena-site/decisions/DEC-CDCP-011-*` records the source-of-truth
  schema amendment.
- `procurement-negotiation-lab/decisions/DEC-FACTORY-007-*` is the
  Phase B precedent.
- `src/evals/run_evidence.py` is the emitter module.
- `src/evals/runner.py` wires the emitter into the per-suite loop.
- `scripts/validate_run_evidence.py` is the validator gate.
- `ops/schemas-cache/run.schema.json` and
  `ops/schemas-cache/event.schema.json` mirror the cross-repo
  contract.
- Phase D.1 will pipe a sample ledger through
  `trace-to-eval evidence from-cdcp-events` to produce a bridge
  packet, closing the producer/consumer loop.

## rollback

Revert the runner wiring, drop the validator gate from
`.github/workflows/gates.yml`, delete
`scripts/validate_run_evidence.py` and `src/evals/run_evidence.py`,
then delete the `R-EVL-006..011` requirements and remove this DEC.
The cached schemas stay because other validators may need them. No
migration is needed because the ledger files are append-only audit
trails with no fan-out.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-006` eval-suite runner emits a conformant Event ledger to
  `ops/event-ledger/<run-id>.jsonl` on every suite execution.
- `R-EVL-007` eval-suite runner emits a conformant Run record to
  `ops/run-records/<run-id>.json` per suite execution.
- `R-EVL-008` `prompt_snapshot_hash` and
  `tool_schemas_snapshot_hash` are always populated.
- `R-EVL-009` `sandbox_image_ref` is populated from the repo HEAD.
- `R-EVL-010` `gate_results_summary` is populated by aggregating
  `gate.check.*` events fired for the per-suite thresholds
  (`recall_at_5_threshold`, `citation_faithfulness_threshold`,
  `answer_quality_threshold`, `refusal_precision_threshold`).
- `R-EVL-011` `validate_run_evidence.py` runs on every push to main
  and exits non-zero on schema violations.
