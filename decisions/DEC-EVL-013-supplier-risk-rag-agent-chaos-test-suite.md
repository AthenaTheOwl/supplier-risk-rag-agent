---
id: DEC-EVL-013-supplier-risk-rag-agent-chaos-test-suite
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-034
amends: DEC-EVL-012-edgar-refresh-and-adversarial-refusal-suite
date: 2026-05-29
status: approved
reversible: true
decision: |
  The supplier-risk-rag-agent repo installs a chaos test suite at
  `tests/test_chaos_run_evidence.py` covering seven mutation classes
  that verify `scripts/validate_run_evidence.py` catches each
  mutation. Each test copies the canonical sample
  (`run-643dff8f3b9c`) into a synthetic root under `tmp_path`,
  applies one mutation against either the Run record or the event
  ledger, runs the validator against the mutated artifacts, and
  asserts the validator exits non-zero with an error message naming
  the broken rule. The canonical sample on disk SHALL NOT be
  modified by any test; mutations land inside `tmp_path` only.

  The seven mutation classes pair one-to-one with the validator's
  three enforcement layers:

  - M1 mutates `Run.prompt_snapshot_hash` to a different valid-shaped
    SHA-256 digest and asserts cross-check 1 trips with the
    `prompt_snapshot_hash mismatch` diagnostic.
  - M2 mutates `Run.tool_schemas_snapshot_hash` and asserts
    cross-check 2 trips with the `tool_schemas_snapshot_hash
    mismatch` diagnostic.
  - M3 inserts a phantom gate name into
    `Run.gate_results_summary.gates_passed` and asserts cross-check 4
    trips with the `gate_results_summary mismatch` diagnostic
    because no `gate.check.passed` event fired for that name.
  - M4 removes the terminal `gate.run.evidence_recorded` event from
    the ledger and asserts the required-event check for a done Run
    trips with the `no gate.run.evidence_recorded` diagnostic.
  - M5 drops `prompt_snapshot_hash` from the `pipeline.start` event's
    payload and asserts the typed-event-payload validation (the
    `oneOf` discriminator on the cached `event.schema.json`) rejects
    the event with the `is not valid under any of the given
    schemas` envelope.
  - M6 mutates `gate.run.evidence_recorded.payload.fields_populated`
    to claim a field the Run does not carry (the test picks
    `determinism`, which the canonical sample omits) and asserts
    cross-check 3 trips with the `does not match replay-equivalence
    fields populated on Run` diagnostic.
  - M7 keeps `Run.status == "done"` but removes
    `sandbox_image_ref` and asserts the required-for-done block
    trips with `sandbox_image_ref` named in the stderr.

  `.github/workflows/run-evidence-gates.yml` gains a fourth named
  job `chaos-validation` that runs the chaos suite under uv on
  Python 3.11. The job is a blocking contract gate; no
  `continue-on-error: true`; no `--no-verify` bypass.
alternatives:
  - label: Option A — fold the chaos tests into test_run_evidence_integration.py
    rejected_because: |
      The existing integration tests drive the producer side of the
      contract: they run the eval-suite runner end-to-end and feed
      the runner's output back into the validator. The chaos suite
      drives the consumer side: it starts from a known-good
      canonical sample, mutates the artifact in place, and asserts
      the validator catches the mutation. Tangling both surfaces in
      one file would obscure which failure mode a future regression
      hit. A separate file plus a fourth named CI job lets a
      chaos-suite regression fail on its own surface with its own
      diagnostic.
  - label: Option B — pick three mutation classes instead of seven
    rejected_because: |
      Three mutations would cover one validator layer at a time and
      ship faster. Seven was chosen because the validator's three
      enforcement layers each cover two or three distinct rules; a
      three-mutation suite would leave four rules uncovered. The
      seven-mutation suite covers every rule named in
      DEC-EVL-007's cross-check table plus the required-for-done
      block from DEC-EVL-006 and the typed-event-payload
      discriminator from Round 2. The marginal cost of the extra
      four tests is roughly one-second pytest runtime, which the
      job budget tolerates.
  - label: Option C — write a property-based hypothesis test instead of seven hand-coded mutations
    rejected_because: |
      A hypothesis property-based test (mutate any field at any
      level; assert the validator catches it) would be the
      tightest claim but would carry two costs the closing pass
      does not pay for. First, the property strategy itself needs
      a generator that produces only schema-valid mutations (so
      schema rejection does not mask the cross-check rejection)
      plus a shrink strategy that converges on minimal
      counter-examples; that is its own engineering surface.
      Second, a hypothesis failure prints a counter-example, not
      a named rule, so the diagnostic is weaker than the
      hand-coded suite's per-mutation message check. A future
      DEC can promote the chaos suite to property-based once the
      seven hand-coded tests have a year of regression history.
  - label: Option D — keep the test suite but omit the CI job
    rejected_because: |
      Without the CI job a chaos-suite regression would only
      surface on a local `pytest` run. The validator's contract is
      a block-merge gate per DEC-CDCP-015; the chaos suite is the
      meta-gate on that gate. Omitting the CI job would let a
      reviewer merge a regression that silently broke the chaos
      suite, which is the failure mode the suite exists to
      prevent. A named CI job mirrors the pattern the three
      sibling jobs (`universal-gates`, `packet-and-replay`,
      `replay-determinism`) already follow.
rationale: |
  This DEC amends DEC-EVL-012 and closes the final gap in the
  engineering-grade rollout of the run-evidence chain. The four
  prior DECs (006, 007, 010, 011) landed the producer-side emitter,
  the validator's four cross-checks, the CI enforcement contract,
  and the replay-determinism fixture. The validator carries three
  layers of enforcement (typed-event-payload validation via the
  cached schema's `oneOf` discriminator, four cross-checks tying
  the Run record back to its ledger, and a required-for-done block
  on done Runs) and a silent regression in any of those layers
  would cost the chain its contract value.

  Two failure shapes the chaos suite catches that the existing
  gates do not. First, a refactor of
  `scripts/validate_run_evidence.py` that drops a cross-check by
  accident (for example, removing the cross-check 3 block during a
  cleanup of dead-looking code) would leave every CI run green
  because the producer-side eval-suite runner always emits a
  consistent Run + ledger pair; the validator's cross-check would
  never fire on a real run. A chaos test that intentionally writes
  an inconsistent pair is the only way to catch the missing check.

  Second, a schema cache refresh that lands a stale
  `event.schema.json` (the `pipeline.start` branch loses its
  required-key constraint, say) would let the producer emit an
  underspecified pipeline.start without the validator complaining.
  M5 catches this case by writing a pipeline.start payload missing
  the required `prompt_snapshot_hash` and asserting the validator
  rejects it. The schema-cache-freshness gate
  (`scripts/check_schema_cache_freshness.py`) compares the cached
  schema against the upstream source, but that comparison would
  miss a coordinated regression where both the cache and the
  upstream lose the same constraint; M5 anchors the contract to a
  concrete payload shape so the gate fires regardless of which
  side drifted.

  The seven-mutation choice maps to the validator's three
  enforcement layers without overlap: M1+M2 cover the two
  hash-equality cross-checks, M3 covers the gate-rollup cross-check,
  M4+M7 cover the required-event and required-field rules on done
  Runs, M5 covers the typed-event-payload validation, and M6 covers
  the fields-populated cross-check. A future regression in any one
  rule turns exactly one chaos test red, which dispatches the fix
  to the broken layer.

  Test isolation is via `tmp_path` plus a `_build_synthetic_root`
  helper that copies the schemas-cache, the scripts directory, and
  the canonical sample into a fresh per-test root. The validator
  resolves paths relative to its own location, so the synthetic
  root carries the same on-disk shape as the repo. The canonical
  sample on disk is never modified.

  Reversibility: dropping this DEC means deleting
  `tests/test_chaos_run_evidence.py`, the `chaos-validation` job
  stanza in `.github/workflows/run-evidence-gates.yml`,
  R-EVL-034..036 in
  `specs/0004-evals-and-thresholds/requirements.md` and the
  matching rows in `traceability.md`, plus this DEC. The validator
  and the canonical sample are not touched by rollback.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: decision
    ref: decisions/DEC-EVL-012-edgar-refresh-and-adversarial-refusal-suite.md
  - kind: decision
    ref: decisions/DEC-EVL-007-eval-runner-run-evidence-cross-checks.md
  - kind: doc
    ref: tests/test_chaos_run_evidence.py
  - kind: doc
    ref: scripts/validate_run_evidence.py
  - kind: doc
    ref: .github/workflows/run-evidence-gates.yml
  - kind: doc
    ref: ops/run-records/run-643dff8f3b9c.json
  - kind: doc
    ref: ops/event-ledger/run-643dff8f3b9c.jsonl
rollback: |
  Delete `tests/test_chaos_run_evidence.py`. Delete the
  `chaos-validation` job stanza from
  `.github/workflows/run-evidence-gates.yml`. Drop R-EVL-034..036
  from `specs/0004-evals-and-thresholds/requirements.md` and the
  matching rows from
  `specs/0004-evals-and-thresholds/traceability.md`. Delete this
  DEC. The canonical sample at
  `ops/run-records/run-643dff8f3b9c.json` plus
  `ops/event-ledger/run-643dff8f3b9c.jsonl` and
  `scripts/validate_run_evidence.py` are not touched by rollback.
owner: control.coordinator
systems_map: |
  Meta-gate on a validator. The validator is a contract enforcer; the
  chaos suite is the test that the enforcer itself still enforces.
  Same producer-consumer separation the run-evidence chain exposes:
  the suite plays the role of an adversarial producer, the validator
  plays the consumer, and a silent regression in the consumer is the
  failure shape no green CI run otherwise catches.
transferable_principle: |
  Any contract validator whose producer always emits a consistent
  artifact needs an adversarial-mutation suite to catch silent
  regressions in the validator itself; otherwise a refactor that
  drops a check passes every real run.
falsification_test: |
  If a future regression introduces an eighth mutation class the
  current seven do not cover and the validator misses it, the
  three-layers-without-overlap claim is falsified for that class and
  the suite needs an eighth test plus a coverage-map update.
adoption_ladder:
  minimum_viable: |
    Ship the seven mutation tests + the baseline test + the
    suite-level guard; run locally under pytest.
  mid_adoption: |
    Add the named `chaos-validation` CI job; require it as a
    blocking gate per DEC-CDCP-015.
  full_adoption: |
    Promote to a property-based test once the seven hand-coded
    cases have a year of regression history; sibling repos in the
    portfolio install the same chaos-suite shape against their own
    contract validators.
  monitoring_signals:
    - chaos-validation job pass/fail trend per PR
    - count of new mutation classes added per quarter
    - count of validator-regression bugs caught by the chaos suite vs. caught in production
---

## decision

The supplier-risk-rag-agent repo installs a chaos test suite at
`tests/test_chaos_run_evidence.py` covering seven mutation classes
that verify `scripts/validate_run_evidence.py` catches each
mutation. Each test copies the canonical sample
(`run-643dff8f3b9c`) into a synthetic root under `tmp_path`,
applies one mutation, runs the validator, and asserts the validator
exits non-zero with an error message naming the broken rule. The
canonical sample on disk is not modified. The CI workflow gains a
fourth named `chaos-validation` job that runs the suite under uv
on Python 3.11 as a blocking contract gate.

## alternatives

- Option A (fold into test_run_evidence_integration.py): rejected
  because tangling producer-side end-to-end tests with consumer-side
  mutation tests obscures which surface a future regression hits.
- Option B (three mutation classes): rejected because it would
  leave four validator rules uncovered for marginal runtime savings.
- Option C (hypothesis property test): rejected because the
  property strategy + shrinker is its own engineering surface and
  the diagnostic is weaker than per-rule message checks.
- Option D (suite without CI job): rejected because the suite is
  the meta-gate on the validator; without CI enforcement a
  regression in the suite itself would not block a merge.

## rationale

This DEC amends DEC-EVL-012 and closes the closing-pass gap on the
engineering-grade rollout. The four prior DECs (006, 007, 010, 011)
landed the producer-side emitter, the validator's three enforcement
layers, the CI enforcement contract, and the replay-determinism
fixture. Without a chaos test on the validator, a refactor that
silently dropped a cross-check or a schema-cache refresh that
landed an underspecified branch would leave every CI run green
against a corrupt sample. The seven-mutation suite anchors the
contract to concrete payload shapes so the gate fires regardless
of which side drifted.

The seven-mutation choice maps to the validator's three layers
without overlap: M1+M2 cover the hash-equality cross-checks, M3
covers the gate-rollup cross-check, M4+M7 cover the required-event
and required-field rules on done Runs, M5 covers the
typed-event-payload validation via the cached `event.schema.json`
oneOf discriminator, and M6 covers the fields-populated
cross-check. A regression in any one rule turns exactly one chaos
test red so the operator dispatches the fix to the broken layer
without walking the other six.

Test isolation is via `tmp_path` plus the `_build_synthetic_root`
helper. The canonical sample at
`ops/run-records/run-643dff8f3b9c.json` and
`ops/event-ledger/run-643dff8f3b9c.jsonl` is read-only across the
test session; every mutation lands inside `tmp_path`.

## evidence

- `tests/test_chaos_run_evidence.py` carries the seven mutation
  tests plus a baseline test that the unmutated canonical sample
  passes the validator plus a suite-level guard counting the
  expected mutation tests.
- `scripts/validate_run_evidence.py` is the validator under test.
- `ops/run-records/run-643dff8f3b9c.json` plus
  `ops/event-ledger/run-643dff8f3b9c.jsonl` are the canonical
  sample the chaos suite mutates copies of.
- `.github/workflows/run-evidence-gates.yml` gains the
  `chaos-validation` job.
- `decisions/DEC-EVL-012-edgar-refresh-and-adversarial-refusal-suite.md`
  is the parent DEC this one amends.
- `decisions/DEC-EVL-007-eval-runner-run-evidence-cross-checks.md`
  defines the four cross-checks the chaos suite verifies.

## rollback

Delete `tests/test_chaos_run_evidence.py`. Delete the
`chaos-validation` job stanza from
`.github/workflows/run-evidence-gates.yml`. Drop R-EVL-034..036
from `specs/0004-evals-and-thresholds/requirements.md` and the
matching rows from
`specs/0004-evals-and-thresholds/traceability.md`. Delete this
DEC.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-034` The repo ships `tests/test_chaos_run_evidence.py`
  carrying seven mutation tests (M1..M7) that each copy the
  canonical sample into a synthetic root under `tmp_path`, apply
  one mutation against the Run record or the event ledger, run
  `scripts/validate_run_evidence.py` against the mutated artifacts,
  and assert the validator exits non-zero with a stderr message
  naming the broken rule. The canonical sample on disk is not
  modified by any test. A baseline test asserts the unmutated
  sample passes the validator; a suite-level guard asserts the
  module carries every expected mutation test name.
- `R-EVL-035` The seven mutation classes cover the validator's
  three enforcement layers: M1+M2 verify the two hash-equality
  cross-checks (`prompt_snapshot_hash` and
  `tool_schemas_snapshot_hash` matching the `pipeline.start`
  event's payload), M3 verifies the gate-rollup cross-check, M4
  verifies the required terminal `gate.run.evidence_recorded`
  event on done Runs, M5 verifies the typed-event-payload
  validation via the cached `event.schema.json` oneOf
  discriminator, M6 verifies the
  `gate.run.evidence_recorded.fields_populated` cross-check, and
  M7 verifies the required-for-done block rejects a done Run
  missing `sandbox_image_ref`.
- `R-EVL-036` `.github/workflows/run-evidence-gates.yml` carries
  a named `chaos-validation` job (separate from
  `universal-gates`, `packet-and-replay`, and
  `replay-determinism`) that runs on `ubuntu-latest` under
  Python 3.11, syncs dev deps under uv, and runs
  `uv run pytest tests/test_chaos_run_evidence.py -v --no-cov`.
  The job carries no `continue-on-error: true` and bypasses no
  pre-commit hooks via `--no-verify` or equivalent. A red chaos
  fixture turns the job red and blocks the merge per GitHub's
  default branch-protection contract.
