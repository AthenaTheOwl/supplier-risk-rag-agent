---
id: DEC-EVL-010-supplier-risk-rag-agent-ci-enforces-run-evidence-chain
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-024
amends: DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration
date: 2026-05-29
status: approved
reversible: true
decision: |
  The supplier-risk-rag-agent repo SHALL ship a single CI workflow at
  `.github/workflows/run-evidence-gates.yml` that enforces the
  run-evidence gate chain defined in athena-site DEC-CDCP-015 on every
  `pull_request` and every `push` to the `main` branch. The contract
  gates are: schema-cache-freshness, voice-lint, bom-check, spec-check,
  decisions-validation (plus the four sibling validators for roles,
  tools, policies, skills, and dreams), typed-event-payload-validation
  (which runs the Round 2 oneOf discriminator validation AND the Round
  3 Run/Event cross-checks), the language test runner (pytest under
  uv), packet-generation-from-canonical-sample against the sibling
  consumer repo, packet-validation against the consumer-side packet
  schema, and replay-smoke against the SHA recorded in the canonical
  sample's `Run.sandbox_image_ref`. Every gate is blocking; no gate
  carries `continue-on-error: true`; no step skips hooks via
  `--no-verify` or equivalent bypass.

  The pre-existing `.github/workflows/gates.yml` workflow continues to
  run gates 1-7 as a redundant safety net. The new
  `run-evidence-gates.yml` workflow is the canonical contract enforcer
  and adds gates 8-10 (packet-gen, packet-validate, replay-smoke) that
  `gates.yml` did not previously carry.

  The canonical sample for the packet-gen + replay-smoke gates is
  `run-643dff8f3b9c`, the regenerated Round-6 sample whose
  `sandbox_image_ref` pins the data-bearing commit per DEC-EVL-009.
  Sandbox SHA extraction uses the `repo://` URI grammar from
  DEC-CDCP-014: `jq` reads `sandbox_image_ref` out of the Run record,
  a sed regex pulls the 40-char SHA out of the URI shape, and
  `git checkout <sha>` is the pre-flight before `scripts/replay_run.py`.
  The workflow uses `fetch-depth: 0` on the repo checkout so the
  recorded SHA is reachable in the runner.
alternatives:
  - label: Option A — extend the existing `gates.yml` workflow in place
    rejected_because: |
      `gates.yml` already runs the universal gates in a single job. Adding
      the packet-gen + replay-smoke gates to that job would force every
      gates.yml run to also check out the sibling consumer repo and
      install it from source, which slows the universal gates path and
      tangles two concerns into one job. A separate workflow lets the
      universal gates path stay lean and lets the packet-and-replay job
      carry its own dependencies (jq, sibling consumer repo checkout,
      sandbox-SHA-strict git checkout) without coupling. The redundant
      universal-gates job inside `run-evidence-gates.yml` is cheap (same
      runner image, cached pip) and gives a second blocking signal on
      the contract gates per DEC-CDCP-015's "every contract gate
      blocks" rule.
  - label: Option B — defer packet-gen and replay-smoke to a nightly cron
    rejected_because: |
      A nightly cron would only catch contract drift after the offending
      commit landed on main. DEC-CDCP-015 names the gate chain as a
      block-merge contract: every PR and every push must verify the
      chain, not a sampled subset. A nightly cron is the right shape
      for expensive smoke runs against live providers, not for the
      packet-gen + replay-smoke gates which run offline against
      checked-in artifacts in under a minute.
  - label: Option C — mark the new gates as informational via continue-on-error
    rejected_because: |
      DEC-CDCP-015 explicitly forbids `continue-on-error: true` on any
      contract gate because it defeats the purpose of the chain. An
      informational gate looks like enforcement in the workflow file
      but does not block the merge; reviewers see green checks and
      assume the contract held. The point of the contract is that
      main cannot accept a Run record whose packet does not generate
      or whose replay does not converge. Informational mode would
      reintroduce the failure shape DEC-CDCP-015 ends.
  - label: Option D — drop the redundant validators (roles, tools, policies, skills, dreams)
    rejected_because: |
      DEC-CDCP-015's universal contract gates name decisions-validation
      "where present" but do not enumerate the sibling validators. Each
      sibling validator gates a specific typed artifact directory shipped
      under this repo (roles/, tools/, policies/, skills/, dreams/).
      Dropping them from the new workflow would let those artifact
      classes drift even while the run-evidence chain stayed green.
      Keeping all six validator calls inside the universal-gates job
      preserves the "every typed artifact has a blocking schema gate"
      discipline DEC-CDCP-015 inherits from the broader portfolio
      contract.
rationale: |
  This DEC amends DEC-EVL-009. DEC-EVL-009 landed the producer-side
  portable URI grammar and the two-pass sandbox SHA emission pattern;
  it did not name how CI enforces the resulting run-evidence chain.
  athena-site DEC-CDCP-015 fills that gap with a portfolio-wide CI
  enforcement contract: every product repo's CI must gate on schema
  cache freshness, typed event payload validation, Run/Event
  cross-checks, packet generation from a canonical sample, packet
  validation, and replay smoke. Without this enforcement, the
  Round-6 portable URI work is verifiable only by the operator who
  remembers to run the validators locally — the difference between
  "we have artifacts" and "main cannot accept unverifiable work".

  Three pieces compose the workflow shape. First, the universal-gates
  job runs all checks that depend only on this repo's working tree:
  schema cache freshness, voice lint, BOM check, spec check, the six
  typed-artifact validators (decisions, roles, tools, policies,
  skills, dreams), the typed-event-payload validator (which already
  carries the Round 3 Run/Event cross-checks per DEC-EVL-007), and
  pytest under uv. These run in one job with cached pip + uv sync so
  the universal contract checks complete fast.

  Second, the packet-and-replay job pulls in the sibling consumer repo
  via a second `actions/checkout@v4` at a sibling path under the
  workspace, pip-installs it as editable, and runs the packet-gen +
  packet-validate + replay-smoke chain against the canonical sample. The
  `--portfolio-root` flag on the packet-gen call points at the
  workspace root so the sibling consumer's `repo://` URI resolver
  can map producer refs to local files. Replay smoke extracts the
  recorded sandbox SHA via a `jq` + sed pipeline, runs
  `git checkout <sha>` against the full-history clone (`fetch-depth: 0`),
  and invokes `scripts/replay_run.py --run-id <canonical-sample>`.
  Replay exits 0 only if `replay_equivalent: true` on all three signals
  (`prompt_snapshot_hash`, `tool_schemas_snapshot_hash`,
  `gate_results_summary`).

  Third, both jobs run on both `pull_request` (no branch filter) and
  `push: branches: [main]` triggers so the chain blocks both the
  pre-merge PR check and any direct push to main. No gate carries
  `continue-on-error: true`. No step uses `--no-verify` or a bypass
  flag. The redundant `gates.yml` workflow stays in place as a second
  signal on the universal gates path.

  Reversibility: the workflow file can be relaxed via a follow-up DEC
  amendment. Reverting the `continue-on-error` ban or downgrading a
  gate to informational requires a new DEC that names the gate, the
  business reason, and the rollback window. The workflow file itself
  is one YAML file; dropping a job or a step is a one-line change.
  The matching specs/0004-evals-and-thresholds requirements
  R-EVL-024..027 can be dropped from the spec ledger alongside the
  workflow change.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: decision
    ref: decisions/DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/athena-site/blob/main/decisions/DEC-CDCP-015-ci-enforces-run-evidence-chain.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/athena-site/blob/main/decisions/DEC-CDCP-014-portable-repo-uri-grammar.md
  - kind: doc
    ref: .github/workflows/run-evidence-gates.yml
  - kind: doc
    ref: .github/workflows/gates.yml
  - kind: doc
    ref: scripts/validate_run_evidence.py
  - kind: doc
    ref: scripts/replay_run.py
  - kind: doc
    ref: ops/run-records/run-643dff8f3b9c.json
  - kind: doc
    ref: ops/event-ledger/run-643dff8f3b9c.jsonl
rollback: |
  Delete `.github/workflows/run-evidence-gates.yml`. The pre-existing
  `.github/workflows/gates.yml` workflow continues to enforce the
  universal contract gates 1-6 plus the validate_run_evidence step,
  so the universal contract chain stays green without the new
  workflow file. Drop R-EVL-024..027 from
  `specs/0004-evals-and-thresholds/requirements.md` and the matching
  traceability rows in `specs/0004-evals-and-thresholds/traceability.md`.
  Delete this DEC. The canonical sample at
  `ops/run-records/run-643dff8f3b9c.json` and its ledger are NOT
  touched by rollback because they are the contract target of the
  replay-smoke gate; they remain valid producer-side artifacts under
  DEC-EVL-009.
owner: control.coordinator
---

## decision

The supplier-risk-rag-agent repo ships
`.github/workflows/run-evidence-gates.yml` enforcing the run-evidence
gate chain defined in athena-site DEC-CDCP-015 on every PR and every
push to main. Two jobs: universal-gates (schema cache freshness, voice
lint, BOM check, spec check, six typed-artifact validators,
typed-event-payload validation with Run/Event cross-checks, pytest)
and packet-and-replay (packet generation from the canonical sample,
packet validation, replay smoke against the recorded sandbox SHA).
Every contract gate is blocking. No `continue-on-error: true` on any
contract step. No bypass via `--no-verify`. The pre-existing
`gates.yml` workflow stays in place as a redundant signal on gates
1-7.

## alternatives

- Option A (extend the existing `gates.yml` in place): rejected
  because adding the sibling-consumer-repo checkout and the
  sandbox-SHA-strict `git checkout` would couple two concerns into
  one job and slow the universal gates path; the redundant
  universal-gates job inside the new workflow is cheap and gives a
  second blocking signal.
- Option B (nightly cron for packet-gen + replay-smoke): rejected
  because DEC-CDCP-015 names the chain as a block-merge contract and
  a nightly cron only catches drift after the offending commit lands.
- Option C (mark new gates as informational with
  `continue-on-error: true`): rejected because DEC-CDCP-015 explicitly
  forbids `continue-on-error` on contract gates; informational mode
  looks like enforcement but does not block the merge.
- Option D (drop the sibling validators for roles, tools, policies,
  skills, dreams): rejected because each gates a specific typed
  artifact directory shipped under this repo and dropping them would
  let those artifact classes drift even while the run-evidence chain
  stayed green.

## rationale

This DEC amends DEC-EVL-009. DEC-EVL-009 landed the producer-side
portable URI grammar and the two-pass sandbox SHA emission pattern;
it did not name how CI enforces the resulting run-evidence chain.
athena-site DEC-CDCP-015 fills that gap with the portfolio-wide CI
enforcement contract.

The workflow shape composes three pieces. The universal-gates job
runs every check that depends only on this repo's working tree under
one Python 3.11 runner with cached pip + uv sync. The packet-and-replay
job pulls in the sibling consumer repo via a second checkout, pip
installs it as editable, runs packet generation with
`--portfolio-root` pointed at the workspace root so `repo://` URIs
resolve, validates the generated packet against the consumer-side
schema, extracts the recorded sandbox SHA via `jq` + sed, runs
`git checkout <sha>` against the full-history clone, and invokes
`scripts/replay_run.py`. The replay command exits 0 only if all three
replay-equivalence signals match. Both jobs trigger on `pull_request`
(no branch filter) and `push: branches: [main]`.

The redundant `gates.yml` workflow stays in place. Running the
universal gates twice in two workflows is cheap (cached pip on the
runner image) and protects against a future regression where the new
workflow file is edited or removed without an accompanying spec
update.

## evidence

- `.github/workflows/run-evidence-gates.yml` carries the two-job
  workflow with the full contract chain.
- `.github/workflows/gates.yml` carries the pre-existing universal
  gates path as a redundant signal.
- `athena-site/decisions/DEC-CDCP-015-ci-enforces-run-evidence-chain.md`
  defines the portfolio-wide contract this DEC implements.
- `decisions/DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration.md`
  defines the producer-side URI grammar and two-pass sandbox SHA
  emission that the replay-smoke gate verifies.
- `ops/run-records/run-643dff8f3b9c.json` plus
  `ops/event-ledger/run-643dff8f3b9c.jsonl` are the canonical sample
  the packet-gen + replay-smoke gates target.
- `scripts/validate_run_evidence.py` and `scripts/replay_run.py` are
  the producer-side scripts the workflow runs.
- `specs/0004-evals-and-thresholds/requirements.md` carries
  R-EVL-024..027 added under this DEC.

## rollback

Delete `.github/workflows/run-evidence-gates.yml`. The pre-existing
`.github/workflows/gates.yml` workflow continues to enforce the
universal contract gates 1-6 plus the validate_run_evidence step.
Drop R-EVL-024..027 from
`specs/0004-evals-and-thresholds/requirements.md` and the matching
traceability rows in `specs/0004-evals-and-thresholds/traceability.md`.
Delete this DEC. The canonical sample and its ledger are not
touched.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-024` The repo ships `.github/workflows/run-evidence-gates.yml`
  triggering on `pull_request` (no branch filter) and
  `push: branches: [main]`, running on `ubuntu-latest` under Python
  3.11, carrying a universal-gates job that runs schema cache
  freshness, voice lint, BOM check, spec check, the six
  typed-artifact validators, typed-event-payload validation, and
  pytest under uv.
- `R-EVL-025` The same workflow file carries a packet-and-replay job
  that checks out the sibling consumer repo at a sibling path under
  the workspace, pip-installs it as editable, runs
  `python -m trace_to_eval evidence from-cdcp-events
  ops/event-ledger/run-643dff8f3b9c.jsonl --out /tmp/packet.json
  --portfolio-root <workspace>`, then runs
  `python -m trace_to_eval evidence validate /tmp/packet.json`. Both
  steps exit 0 on a green run.
- `R-EVL-026` The packet-and-replay job extracts the recorded
  sandbox SHA from `Run.sandbox_image_ref` via `jq` + a sed regex
  matching `^repo://[^@]+@([a-f0-9]{40})/.*`, runs
  `git checkout <sandbox-sha>` against a full-history clone
  (`fetch-depth: 0`), and runs
  `python scripts/replay_run.py --run-id run-643dff8f3b9c`. The
  replay step exits 0 only if `replay_equivalent: true` on all three
  signals.
- `R-EVL-027` No contract gate carries `continue-on-error: true`. No
  step bypasses pre-commit hooks via `--no-verify` or equivalent.
  Every gate listed in DEC-CDCP-015 blocks the merge.
