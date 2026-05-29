---
id: dream-2026-W22-backlog-002
target_kind: backlog_item
mode: failure_clustering
human_review_required: true
status: candidate
evidence:
  - kind: doc
    ref: tests/test_replay_determinism.py
  - kind: doc
    ref: scripts/replay_run.py
  - kind: doc
    ref: scripts/validate_run_evidence.py
  - kind: doc
    ref: ops/run-records/run-643dff8f3b9c.json
  - kind: doc
    ref: ops/event-ledger/run-643dff8f3b9c.jsonl
  - kind: decision
    ref: decisions/DEC-EVL-008-eval-replay-command.md
---

## title

Ship a replay chaos suite that mutates the canonical sample and asserts the gate chain catches each mutation

## rationale

The W22 voice-lint update unblocked `tests/test_replay_determinism.py`,
which asserts that re-running the replay command N times against
the canonical sample produces the same equivalence hashes every
time. That test catches non-determinism in the replay path itself.
What it does not catch: a quietly-broken validator that accepts
a malformed Run record, or a quietly-broken replay command that
returns `replay_equivalent: true` for a mutated sample.

The proposed work ships a chaos suite under `tests/chaos/` that
generates a corpus of mutated samples from `run-643dff8f3b9c` and
asserts the gate chain detects each mutation. Concrete mutations:

1. Strip a required field from the Run record. `validate_run_evidence`
   must exit non-zero.
2. Mismatch a `run_id` between the Run record and a ledger event.
   The Round-3 cross-check must fire.
3. Replace `prompt_snapshot_hash` in the recorded sample with a
   random hash. `scripts/replay_run.py` must exit non-zero with
   `replay_equivalent: false`.
4. Mutate one `Run.inputs[].ref` to a `repo://` URI pointing at a
   non-existent path. `resolve_uri` must surface the missing-file
   error.
5. Replace the recorded sandbox SHA with a SHA that exists but
   pins a different tree. `_enforce_head` must trip the divergence
   message.
6. Mutate the typed payload of a `run.evidence.replayed` event so
   it no longer matches the `$ref` shape. The typed-payload
   validator must fire.

Each mutation is a single fixture file under
`tests/chaos/fixtures/`. The chaos suite reads each fixture,
runs the named gate against it, and asserts the expected
failure mode fires.

The suite is the audit complement to the determinism harness.
The determinism harness asserts "the gate is stable across
replays". The chaos suite asserts "the gate is correctly
discriminating".

## cost

Medium. One new test directory, six fixtures (each is a small
mutation of the canonical sample), and a parametrized test that
runs each fixture through the relevant gate. The fixtures are
generated from a single source script so they stay in sync with
the canonical sample shape.

## risk

If the chaos fixtures drift out of sync with the canonical
sample (the canonical sample regenerates under a new schema
version), the chaos suite starts asserting against a stale
shape. Mitigation: ship the fixtures as derivations of the
canonical sample at test collection time, not as checked-in
JSON files. The fixture-generation script reads the canonical
sample, applies the mutation, and feeds the result to the gate
under test.

A second risk: the chaos suite makes CI slower if every mutation
fixture requires its own subprocess invocation of the gate
script. Mitigation: run the chaos suite as a nightly cron
workflow, not on every PR. The DEC-EVL-010 contract chain
already covers the happy path on every PR.

## timeline

Next month. The work is well-scoped but not urgent; the
determinism harness already catches the most-likely failure
mode (a code change that silently flips a replay hash). The
chaos suite catches "the gate stopped discriminating", which is
a rarer but more dangerous failure shape.

## promotion path

The operator opens a draft DEC-EVL-011, writes the chaos suite
in a feature branch under `tests/chaos/`, adds a new nightly
workflow at `.github/workflows/chaos-suite.yml`, confirms each
of the six mutations triggers the expected gate failure, and
merges. The DEC names the audit pattern and the nightly cron
trigger; spec 0004 gains R-EVL-029..034 covering the six
mutation classes.

## risks if promoted blindly

- The six-mutation list is the starting set, not the universal
  set. A future schema extension may add a seventh failure mode
  the chaos suite does not cover. Mitigation: the DEC explicitly
  names "extend the chaos suite when a new gate ships" as a
  follow-up rule.
- Running the chaos suite nightly means a regression lands on
  main before the suite catches it. The trade is acceptable
  because the PR-time contract chain already gates the
  happy-path failures.
