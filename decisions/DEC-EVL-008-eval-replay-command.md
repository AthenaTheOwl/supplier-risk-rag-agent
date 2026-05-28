---
id: DEC-EVL-008-eval-replay-command
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-016
amends: DEC-EVL-007-eval-runner-run-evidence-cross-checks
date: 2026-05-28
status: approved
reversible: true
decision: |
  The eval-suite repo SHALL ship `scripts/replay_run.py` performing
  equivalence replay against a recorded Run record. The command is
  HEAD-strict: the recorded `sandbox_image_ref` SHA must equal the
  current `git rev-parse HEAD`, else the script exits 1 with a
  `git checkout <sha>` hint. On match, the script re-runs the eval
  suite the Run originated from against the checked-in sample corpus,
  compares the three replay-equivalence signals
  (`prompt_snapshot_hash`, `tool_schemas_snapshot_hash`,
  `gate_results_summary`) between the recorded Run and the fresh
  Run, and writes one `run.evidence.replayed` event to a NEW
  per-replay ledger file at
  `ops/event-ledger/replay-<run-id>-<ISO-timestamp>.jsonl` plus a
  detailed comparison report at
  `ops/replay-records/<run-id>/<replay-event-id>.json`. The original
  ledger file at `ops/event-ledger/<run-id>.jsonl` and the original
  Run record are not modified.

  `replay_method` is always `equivalence`. The deterministic
  refusal-precision path against the checked-in corpus does not call
  the LLM, but the LLM provider and model identity is folded into
  `tool_schemas_snapshot_hash`, so the strongest honest claim is that
  same suite + same corpus + same LLM identity produces same
  hashes + same gate rollup, i.e. the conditions for an identical
  run match. Byte-comparing LLM outputs is out of scope.

  Exit codes: 0 on equivalent (all three signals match), 1 on
  divergent or pre-flight failure. The summary printed to stdout
  names each diverging signal so the operator can dispatch on the
  failing signal.
alternatives:
  - label: deterministic replay claim (no equivalence framing)
    rejected_because: |
      Deterministic replay would require byte-comparing model outputs
      across runs, but the eval-suite runner does not call the LLM on
      the refusal-precision path against the sample corpus. The LLM
      identity still folds into `tool_schemas_snapshot_hash` so the
      identity is pinned, and the checked-in corpus is deterministic
      against the hashing embedder plus the named ranker weights.
      Claiming "deterministic" would overstate what the script
      verifies; "equivalence" is the honest framing. The cross-repo
      event schema accepts both `deterministic` and `equivalence` on
      `run.evidence.replayed.payload.replay_method`; this repo picks
      the conservative label.
  - label: relax HEAD-strict to "warn on mismatch"
    rejected_because: |
      Warning on HEAD mismatch instead of failing would let an
      operator replay against a different corpus, prompt set, or
      ranker config than the recorded Run captured. The hashes might
      still match (no code drift between the two SHAs) or might
      diverge for reasons unrelated to a real regression. The whole
      point of the HEAD-strict check is to pin the comparison to the
      commit that emitted the original Run; relaxing it would invite
      the operator to debug spurious divergences. Failing fast with a
      `git checkout` hint forces the right action at the moment of
      mismatch.
  - label: overwrite the original ledger with the replay event
    rejected_because: |
      The original ledger at `ops/event-ledger/<run-id>.jsonl` is
      append-only evidence of the original run. Adding a replay event
      to it would conflate two distinct runs in one timeline and
      break the existing cross-check that ties each ledger to one
      run-evidence emission. The per-replay ledger file at
      `replay-<run-id>-<timestamp>.jsonl` keeps the replay event
      adjacent to the source ledger by file-name prefix while leaving
      the source ledger byte-stable.
  - label: skip the per-replay ledger; write only the comparison report
    rejected_because: |
      The cross-repo `event.schema.json` carries a typed
      `run.evidence.replayed` branch precisely so a downstream
      consumer can read replay claims off the event ledger without
      walking a separate report directory. Dropping the ledger event
      would force the consumer to special-case replay artifacts.
      Emitting the event matches the producer/consumer contract the
      sibling consumer repo's bridge generator already expects.
rationale: |
  This DEC amends DEC-EVL-007. DEC-EVL-007 named the cross-check
  contract between a Run record and its event ledger; it stopped
  short of naming what "replay" means for an eval-suite Run.

  Round 5 of the run-evidence rollout completes the engineering-grade
  replay claim. The eval-suite runner is deterministic against the
  checked-in sample corpus: no sampling, hashing embedder, pinned
  ranker weights. The LLM provider and model identity is captured in
  `tool_schemas_snapshot_hash` so a change to either perturbs the
  hash and any replay run notices the divergence. Combined, this is
  enough to make a defensible equivalence claim: same suite + same
  corpus + same LLM identity means the run-evidence signals match,
  even though the script does not byte-compare model outputs.

  HEAD-strict is the discipline that makes the claim verifiable. The
  recorded `sandbox_image_ref` pins the producing commit; the replay
  command refuses to compare against a different commit, so the
  operator either runs the comparison at the right SHA or
  acknowledges that the comparison would be apples-to-oranges. This
  closes the gap where a stale Run record could pass a
  superficial replay against a drifted prompt or ranker config.

  Emitting `run.evidence.replayed` into a new per-replay ledger file
  matches the typed event-schema branch shipped by the source-of-truth
  schemas. A consumer reading the ledger directory finds one source
  ledger plus N per-replay ledgers per run; the file-name prefix
  pattern (`replay-<run-id>-...`) keeps the relationship discoverable
  without a separate index file. The comparison report at
  `ops/replay-records/<run-id>/<replay-event-id>.json` carries the
  detail a reviewer needs when the script reports divergence: the
  recorded value, the fresh value, and the per-signal match flag.

  Reversibility: the rollback path is to drop `scripts/replay_run.py`
  and the four `R-EVL-016..019` requirements and the seven replay
  tests. The original ledger and Run record stay byte-stable across
  rollback because the replay script never writes into them.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: decision
    ref: decisions/DEC-EVL-007-eval-runner-run-evidence-cross-checks.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/athena-site/blob/main/decisions/DEC-CDCP-013-typed-event-payload-schemas.md
  - kind: doc
    ref: scripts/replay_run.py
  - kind: doc
    ref: tests/test_replay_run.py
  - kind: doc
    ref: ops/replay-records/run-2eab3c611b6a/
  - kind: doc
    ref: ops/event-ledger/run-2eab3c611b6a.jsonl
  - kind: doc
    ref: ops/run-records/run-2eab3c611b6a.json
rollback: |
  Delete `scripts/replay_run.py` plus `tests/test_replay_run.py`.
  Delete the committed `ops/event-ledger/replay-*.jsonl` files and
  the `ops/replay-records/` tree. Drop the `R-EVL-016..019`
  requirements from `specs/0004-evals-and-thresholds/requirements.md`
  and the matching rows in the traceability table. Delete this DEC.
  No data migration is needed because the source ledger files and
  Run records stay byte-stable; the replay script writes only to
  the new per-replay ledger and the replay-records tree.
owner: control.coordinator
---

## decision

The eval-suite repo ships `scripts/replay_run.py` performing
equivalence replay against a recorded Run record. The script is
HEAD-strict, compares the three replay-equivalence signals between
the recorded Run and a fresh re-run of the same suite, and writes
one `run.evidence.replayed` event per replay into a new per-replay
ledger file plus a detailed comparison report under
`ops/replay-records/<run-id>/`.

## alternatives

- Deterministic replay (no equivalence framing): rejected because
  the script does not byte-compare LLM outputs. "Equivalence" is the
  honest label given the LLM identity sits in the surface hash.
- Relax HEAD-strict to a warning: rejected because relaxing it
  invites the operator to debug spurious divergences against a
  different commit's corpus or prompts.
- Overwrite the original ledger: rejected because the source ledger
  is append-only evidence of the original run; per-replay ledgers
  keep the two runs separable.
- Skip the per-replay ledger; write only the report: rejected
  because the typed `run.evidence.replayed` branch in the
  source-of-truth event schema exists so a consumer can read the
  replay claim off the ledger without walking a side directory.

## rationale

This DEC amends DEC-EVL-007. DEC-EVL-007 named the cross-check
contract between a Run record and its event ledger; it did not name
what "replay" means for an eval-suite Run.

The eval-suite runner is deterministic against the checked-in sample
corpus, and the LLM identity folds into
`tool_schemas_snapshot_hash`. Together, that is enough to make a
defensible equivalence claim: same suite + same corpus + same LLM
identity means the three replay-equivalence signals
(`prompt_snapshot_hash`, `tool_schemas_snapshot_hash`,
`gate_results_summary`) match between the recorded Run and a fresh
re-run.

HEAD-strict is the discipline that makes the claim verifiable. The
recorded `sandbox_image_ref` pins the producing commit; refusing to
compare against a different commit closes the gap where a stale
Run record could pass a superficial replay against a drifted prompt
or ranker config.

The new per-replay ledger file plus the comparison report under
`ops/replay-records/<run-id>/` give a consumer two paths to the same
claim: the event ledger for a typed schema-checkable form, and the
report for a richer per-signal breakdown.

## evidence

- `specs/0004-evals-and-thresholds/requirements.md` lists
  `R-EVL-016..019`.
- `athena-site/decisions/DEC-CDCP-013-*` is the source-of-truth
  schema amendment that added the typed `run.evidence.replayed`
  branch.
- `scripts/replay_run.py` carries the replay command.
- `tests/test_replay_run.py` carries the positive + four negative
  tests covering equivalence, HEAD mismatch, missing record, prompt
  drift, and rubric drift.
- `ops/event-ledger/replay-run-2eab3c611b6a-*.jsonl` plus
  `ops/replay-records/run-2eab3c611b6a/*.json` are the canonical
  replay artifacts emitted by running the script against the
  Round-3 sample regenerated under the current commit.

## rollback

Delete `scripts/replay_run.py` plus `tests/test_replay_run.py`.
Delete the committed `ops/event-ledger/replay-*.jsonl` files and the
`ops/replay-records/` tree. Drop the `R-EVL-016..019` requirements
plus their traceability rows. Delete this DEC. No data migration is
needed because the source ledger files and Run records stay
byte-stable; the replay script writes only to the new per-replay
ledger and the replay-records tree.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-016` `scripts/replay_run.py` is the canonical replay
  command for an eval-suite Run; it reads
  `ops/run-records/<run-id>.json` plus
  `ops/event-ledger/<run-id>.jsonl` and exits 1 with a clear
  diagnostic when either file is missing.
- `R-EVL-017` Replay is HEAD-strict: the recorded
  `sandbox_image_ref` SHA must equal the current
  `git rev-parse HEAD`; mismatch exits 1 with a
  `git checkout <sha>` hint.
- `R-EVL-018` Replay compares the three replay-equivalence signals
  (`prompt_snapshot_hash`, `tool_schemas_snapshot_hash`,
  `gate_results_summary`); `replay_equivalent` is true iff all three
  match; the script exits 1 on any divergence.
- `R-EVL-019` Replay emits one `run.evidence.replayed` event into a
  new per-replay ledger file at
  `ops/event-ledger/replay-<run-id>-<timestamp>.jsonl` plus a
  detailed comparison report at
  `ops/replay-records/<run-id>/<replay-event-id>.json`; the source
  ledger and the source Run record are not modified.
