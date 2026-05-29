---
id: DEC-EVL-011-supplier-risk-replay-determinism-test
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-028
amends: DEC-EVL-010-supplier-risk-rag-agent-ci-enforces-run-evidence-chain
date: 2026-05-29
status: approved
reversible: true
decision: |
  The supplier-risk-rag-agent repo SHALL install a replay-determinism
  test fixture at `tests/test_replay_determinism.py` that replays the
  canonical sample `run-643dff8f3b9c` `RERUNS` times (default 3,
  override via env var) at the recorded sandbox SHA and asserts that
  every replay produces an identical canonicalized SHA-256 hash over
  the three replay-equivalence fields (`prompt_snapshot_hash`,
  `tool_schemas_snapshot_hash`, and `gate_results_summary`). The
  fixture checks out the recorded sandbox SHA before the loop,
  restores the original HEAD on teardown (including the failure
  paths), and writes a failure bundle to `artifacts/failbundles/`
  carrying the first two diverging canonical traces plus the unique
  hash set on divergence.

  The fixture depends on per-replay ledger filenames staying distinct
  across the loop. `scripts/replay_run.py._now_filename_iso` SHALL
  therefore produce a microsecond-resolution label
  (`%Y%m%dT%H%M%S.%fZ`) so three replays inside the same wall-clock
  second land on three distinct ledger paths under
  `ops/event-ledger/`. The legacy per-second format
  (`%Y%m%dT%H%M%SZ`) collided when rapid replays opened the ledger
  within the same second; the fixture surfaced the collision as a
  missing-ledger assertion failure on every rerun after the first.

  `.github/workflows/run-evidence-gates.yml` SHALL carry a named
  `replay-determinism` job (separate from the existing
  `universal-gates` and `packet-and-replay` jobs) that checks out the
  repo with `fetch-depth: 0`, syncs dev deps under uv on Python 3.11,
  runs `pytest tests/test_replay_determinism.py -v --no-cov` with
  `RERUNS=3`, and uploads `artifacts/failbundles/` on failure. The
  job carries no `continue-on-error: true` and bypasses no pre-commit
  hooks via `--no-verify` or equivalent. Replay-determinism is a
  blocking contract gate per DEC-CDCP-015.
alternatives:
  - label: Option A — fold the determinism check into the single replay-smoke step in packet-and-replay
    rejected_because: |
      The packet-and-replay job already checks out the sandbox SHA
      once and runs replay once. Running the replay three times in
      that job would double the job's wall-clock cost and tangle
      two concerns (packet-gen + replay-smoke vs. determinism)
      into one job whose failure surface would be harder to read.
      A separate `replay-determinism` job lets the determinism
      gate fail independently with its own artifact upload so the
      operator can dispatch on the unique-hash list without
      walking the packet-gen logs first.
  - label: Option B — keep the per-second timestamp format and append a UUID suffix to the ledger filename
    rejected_because: |
      A UUID suffix would also guarantee uniqueness across rapid
      replays, but it would obscure the chronological order of
      replay events when an operator lists the ledger directory.
      Microsecond resolution preserves the wall-clock ordering
      (sort by filename = sort by time) while still guaranteeing
      uniqueness up to the OS clock resolution (sub-microsecond
      collisions are not reachable from Python on the runner
      images this repo targets). The lexicographic-ordering
      property is load-bearing for the test's set-difference
      logic that snapshots the directory before each replay.
  - label: Option C — defer the determinism check to a nightly cron
    rejected_because: |
      A nightly cron would only catch determinism drift after the
      offending commit lands on main. The replay-equivalence
      fields are the contract surface DEC-EVL-010 already gates
      on every PR; a per-PR determinism check is the right shape
      to keep main verifiable on every merge. The job's wall-clock
      cost (one replay loop of three iterations against a checked-
      in sample with the deterministic hybrid ranker) is well
      under a minute on the runner image.
  - label: Option D — mark the determinism job informational via continue-on-error
    rejected_because: |
      DEC-CDCP-015 explicitly forbids `continue-on-error: true` on
      any contract gate because it defeats the chain. An
      informational determinism gate would look like enforcement
      in the workflow file but would not block the merge;
      reviewers would see green checks and assume the contract
      held. The point of installing the determinism fixture is
      that main cannot accept a drift-introducing commit; the
      enforcement contract requires the job to block.
rationale: |
  This DEC amends DEC-EVL-010. DEC-EVL-010 landed the CI enforcement
  chain for the producer-side run-evidence contract, including a
  single-shot replay-smoke step that runs the canonical sample once
  and asserts `replay_equivalent: true` on all three signals. A
  single-shot replay does not catch the failure mode where two
  nominally-identical replays produce different hashes — for
  example, a prompt or tool-surface change that lands without an
  accompanying sample regen, or a gate-set rename that flips the
  rollup shape between runs. The Workflow B audit + the ChatGPT
  pulse determinism pattern both call out the same gap: a
  three-rerun loop is the strongest claim a producer-side test can
  make without byte-comparing model outputs.

  Translating that pattern into this repo's run-evidence framing
  yields the fixture installed under this DEC. Each replay produces
  a fresh comparison report under `ops/replay-records/<run-id>/`
  plus a per-replay ledger under `ops/event-ledger/`. The fixture
  reads the `fresh` half of each comparison report's three
  replay-equivalence signals, canonicalizes the tuple
  (`json.dumps(..., sort_keys=True, separators=(",", ":"))`),
  SHA-256-hashes the byte string, and asserts every replay produced
  the same hash. The HEAD-strict pre-flight is delegated to
  `scripts/replay_run.py`; the fixture saves the current HEAD before
  the loop and restores it on teardown so the test never leaves the
  working tree on the sandbox SHA.

  The per-second timestamp bug surfaced once the fixture started
  reading the per-replay ledger directory after each iteration.
  Three replays inside the same wall-clock second collided on the
  ledger filename — only one ledger file appeared instead of three,
  and the set-difference assertion that counts fresh ledgers
  collapsed to zero on every rerun after the first. The fix swaps
  the `%Y%m%dT%H%M%SZ` format string for the microsecond-resolution
  form `f"{now:%Y%m%dT%H%M%S}.{now.microsecond:06d}Z"`. A single
  `datetime.now(UTC)` call keeps the seconds field and the
  microseconds field consistent across the format-string boundary.

  The named CI job mirrors the pattern shipped under
  procurement-negotiation-lab's `run-evidence-gates.yml` for
  symmetry across the portfolio. Running the determinism fixture as
  a third job (alongside `universal-gates` and `packet-and-replay`)
  gives the contract chain three independently-failing surfaces:
  schema + universal validators, packet-gen + single-shot replay,
  and three-rerun determinism. Each surface fails with its own
  artifact upload so the operator dispatches on the failing signal
  without walking the other two jobs' logs.

  Reversibility: dropping the determinism fixture is a delete of
  one test file plus the matching CI job stanza. Reverting the
  microsecond-resolution fix would re-introduce the collision; the
  fix is keyed off the format-string literal in
  `scripts/replay_run.py._now_filename_iso` and a follow-up DEC
  could swap it for any uniqueness-preserving alternative (UUID
  suffix, monotonic counter, etc.). R-EVL-028..030 in
  `specs/0004-evals-and-thresholds/requirements.md` can be dropped
  alongside the code revert.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: decision
    ref: decisions/DEC-EVL-010-supplier-risk-rag-agent-ci-enforces-run-evidence-chain.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/athena-site/blob/main/decisions/DEC-CDCP-015-ci-enforces-run-evidence-chain.md
  - kind: doc
    ref: tests/test_replay_determinism.py
  - kind: doc
    ref: scripts/replay_run.py
  - kind: doc
    ref: .github/workflows/run-evidence-gates.yml
  - kind: doc
    ref: ops/run-records/run-643dff8f3b9c.json
rollback: |
  Delete `tests/test_replay_determinism.py`. Revert the
  microsecond-resolution change to
  `scripts/replay_run.py._now_filename_iso` (restore the
  `%Y%m%dT%H%M%SZ` format string). Delete the `replay-determinism`
  job stanza from `.github/workflows/run-evidence-gates.yml`. Drop
  R-EVL-028..030 from `specs/0004-evals-and-thresholds/requirements.md`
  and the matching rows from
  `specs/0004-evals-and-thresholds/traceability.md`. Delete this
  DEC. The canonical sample at `ops/run-records/run-643dff8f3b9c.json`
  is not touched by rollback because the single-shot replay-smoke
  gate under DEC-EVL-010 still depends on it.
owner: control.coordinator
---

## decision

The supplier-risk-rag-agent repo installs a replay-determinism test
fixture at `tests/test_replay_determinism.py` that replays the
canonical sample `run-643dff8f3b9c` three times (default; override
via `RERUNS` env var) at the recorded sandbox SHA and asserts every
replay produces the same SHA-256 hash over the three
replay-equivalence fields. `scripts/replay_run.py._now_filename_iso`
switches to microsecond resolution so rapid replays land on distinct
per-replay ledger paths. `.github/workflows/run-evidence-gates.yml`
gains a named `replay-determinism` job that runs the fixture under
uv on Python 3.11 with `fetch-depth: 0` on the checkout so the
recorded sandbox SHA is reachable. The job is a blocking contract
gate; no `continue-on-error: true`; no `--no-verify` bypass.

## alternatives

- Option A (fold determinism into the existing replay-smoke step):
  rejected because it would tangle two concerns into one job and
  obscure the failure surface.
- Option B (UUID suffix instead of microsecond resolution):
  rejected because UUID suffixes break the chronological ordering
  property the test's set-difference logic depends on.
- Option C (nightly cron): rejected because it only catches drift
  after the offending commit lands on main; DEC-CDCP-015 names the
  chain as a block-merge contract.
- Option D (informational gate via continue-on-error): rejected
  because DEC-CDCP-015 explicitly forbids `continue-on-error: true`
  on any contract gate.

## rationale

This DEC amends DEC-EVL-010. The single-shot replay-smoke step the
prior DEC installed asserts `replay_equivalent: true` on one
replay; it cannot catch a drift-introducing commit whose two
nominally-identical replays produce different hashes. A
three-rerun loop is the strongest claim a producer-side test can
make without byte-comparing model outputs; the ChatGPT pulse
determinism pattern + the Workflow B audit both call out the same
shape.

The per-second timestamp bug surfaced as a missing-ledger
assertion failure during the fixture's first local run. Three
replays inside the same wall-clock second collided on the ledger
filename — only one ledger file appeared, and the set-difference
that counts fresh ledgers per iteration dropped to zero on every
rerun after the first. The microsecond-resolution fix preserves
the chronological-ordering property the directory-snapshot logic
in the fixture depends on.

The named CI job mirrors the pattern from
procurement-negotiation-lab so the portfolio carries a consistent
determinism-gate shape across product repos.

## evidence

- `tests/test_replay_determinism.py` carries the fixture.
- `scripts/replay_run.py._now_filename_iso` switches to microsecond
  resolution.
- `.github/workflows/run-evidence-gates.yml` gains the named
  `replay-determinism` job.
- `decisions/DEC-EVL-010-supplier-risk-rag-agent-ci-enforces-run-evidence-chain.md`
  is the parent DEC this one amends.
- `athena-site/decisions/DEC-CDCP-015-ci-enforces-run-evidence-chain.md`
  defines the portfolio-wide CI enforcement contract this DEC
  extends with the determinism leg.
- `ops/run-records/run-643dff8f3b9c.json` is the canonical sample
  the fixture replays against.

## rollback

Delete `tests/test_replay_determinism.py`. Revert the format-string
change to `scripts/replay_run.py._now_filename_iso`. Delete the
`replay-determinism` job stanza from
`.github/workflows/run-evidence-gates.yml`. Drop R-EVL-028..030
from `specs/0004-evals-and-thresholds/requirements.md` and the
matching rows from
`specs/0004-evals-and-thresholds/traceability.md`. Delete this DEC.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-028` The repo ships `tests/test_replay_determinism.py`
  that replays the canonical sample `run-643dff8f3b9c` `RERUNS`
  times (default 3) at the recorded sandbox SHA, extracts the
  three replay-equivalence fields from each fresh replay record,
  canonicalizes the tuple via
  `json.dumps(..., sort_keys=True, separators=(",", ":"))`,
  SHA-256-hashes the byte string, and asserts every replay
  produced the same hash. On divergence the fixture writes a
  failure bundle to `artifacts/failbundles/` with the unique hash
  set, the first two diverging canonical traces, and the
  canonical sample identity, then fails with the bundle path in
  the assertion message. The fixture saves the current HEAD
  before the loop and restores it on teardown including the
  failure paths.
- `R-EVL-029` `scripts/replay_run.py._now_filename_iso` returns a
  microsecond-resolution label
  (`%Y%m%dT%H%M%S.<microseconds>Z`) so three replays inside the
  same wall-clock second land on three distinct per-replay
  ledger paths under `ops/event-ledger/`. A single
  `datetime.now(UTC)` call keeps the seconds field and the
  microseconds field consistent across the format-string
  boundary. The existing replay-records glob in the
  determinism fixture (`replay-<run-id>-*.jsonl`) matches both
  the legacy per-second format and the new microsecond format
  during the migration round.
- `R-EVL-030` `.github/workflows/run-evidence-gates.yml` carries
  a named `replay-determinism` job (separate from
  `universal-gates` and `packet-and-replay`) that runs on
  `ubuntu-latest` under Python 3.11, checks out the repo with
  `fetch-depth: 0`, syncs dev deps under uv, runs
  `uv run pytest tests/test_replay_determinism.py -v --no-cov`
  with `RERUNS=3`, and uploads `artifacts/failbundles/` on
  failure via `actions/upload-artifact@v4`. The job carries no
  `continue-on-error: true` and bypasses no pre-commit hooks via
  `--no-verify` or equivalent.
