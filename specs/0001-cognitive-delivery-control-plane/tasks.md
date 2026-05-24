# tasks: cognitive-delivery-control-plane

## Spec ledger

- [x] `specs/0001-cognitive-delivery-control-plane/requirements.md`
  with R-CDCP-001..010.
- [x] `specs/0001-cognitive-delivery-control-plane/design.md`.
- [x] `specs/0001-cognitive-delivery-control-plane/tasks.md` (this
  file).
- [x] `specs/0001-cognitive-delivery-control-plane/acceptance.md`.
- [x] `specs/0001-cognitive-delivery-control-plane/research.md`.
- [x] `specs/0001-cognitive-delivery-control-plane/traceability.md`.
- [x] `specs/README.md` lists the new spec folder.

## Decisions directory

- [x] `decisions/README.md` documents the format and the
  add-a-decision flow.
- [x] `decisions/DEC-CDCP-001-install-cdcp-governance.md`.
- [x] `decisions/.spec-check-allowlist.yaml` lists deferred-backfill
  R-* IDs (empty `deferred` block; the only R-* IDs in the repo today
  are R-CDCP-* covered by the bootstrap DEC).

## Agent contract

- [x] `.agents/AGENTS.md` with coding style, domain decisions,
  workflow conventions, and cross-repo links.
- [x] `.agents/skills/run-supplier-risk-query/SKILL.md` v0.1.0
  graduating the existing RAG query pattern under `src/agent/`.

## Operating model

- [x] `.agents/roles/control.coordinator/{role.yaml, instructions.md,
  tools.yaml, output.schema.json, gates.yaml}`.
- [x] `.agents/roles/product.spec-writer/...`.
- [x] `.agents/roles/engineering.implementation/...`.
- [x] `.agents/roles/engineering.code-reviewer/...`.
- [x] `.agents/roles/science.proof-gate-runner/...`.
- [x] `.agents/roles/learning.dream-orchestrator/...`.
- [x] `.agents/tools.yaml` with the supplier-risk RAG tool registry.
- [x] `.agents/policies/default-deny.yaml`.
- [x] `.agents/policies/coordinator-routing-only.yaml`.
- [x] `.agents/policies/implementation-can-edit-code.yaml`.
- [x] `.agents/policies/reviewer-cannot-edit-code.yaml`.
- [x] `.agents/policies/dream-candidates-require-human-approval.yaml`.
- [x] `.agents/policies/eval-suite-required-before-prompt-change.yaml`.
- [x] `.agents/state-machines/spec-lifecycle.yaml`.
- [x] `.agents/state-machines/run-lifecycle.yaml`.
- [x] `.agents/state-machines/release-lifecycle.yaml`.
- [x] `.agents/workflows/single-change.yaml`.
- [x] `.agents/workflows/weekly-dream.yaml`.
- [x] `.agents/workflows/incident-response.yaml`.
- [x] `.agents/workflows/prompt-or-model-change.yaml`.
- [x] `.agents/CATALOG.md` indexing the six roles and the tool +
  policy registrations.

## Dreams

- [x] `dreams/README.md` documents the eight dream modes and the
  human-gate rule.

## Ops ledgers

- [x] `ops/RELEASE_LEDGER.md` with backfilled entries for the six
  pre-CDCP commits.
- [x] `ops/RESET_LEDGER.md` with the documented format and "No resets
  recorded." entry.
- [x] `ops/event-log/2026-05-24.jsonl` seeded with `cdcp.installed`
  and `spec.created` events.
- [x] `ops/schemas-cache/decision.schema.json`,
  `role.schema.json`, `tool.schema.json`, `policy.schema.json`.

## Scripts

- [x] `scripts/voice_lint.py`.
- [x] `scripts/spec_check.py` with R-* prefix set and DEC-coverage
  rule.
- [x] `scripts/validate_decisions.py`.
- [x] `scripts/validate_roles.py`.
- [x] `scripts/validate_tools.py`.
- [x] `scripts/validate_policies.py`.

## CI workflow

- [x] `.github/workflows/gates.yml` runs the six python gates on push
  and PR, alongside the existing `tests.yml` and `evals.yml`.

## Repo root

- [x] `README.md` carries a "Governance" section pointing at specs,
  decisions, dreams, agents, ledgers, and the athena-site charter.

## Verification

- [x] `python scripts/voice_lint.py` exits 0 across the governance
  copy.
- [x] `python scripts/spec_check.py` exits 0 with one active spec.
- [x] `python scripts/validate_decisions.py` exits 0 with one DEC
  validated.
- [x] `python scripts/validate_roles.py` exits 0 with six roles
  validated.
- [x] `python scripts/validate_tools.py` exits 0 with the tool
  registry validated.
- [x] `python scripts/validate_policies.py` exits 0 with six
  policies validated.
