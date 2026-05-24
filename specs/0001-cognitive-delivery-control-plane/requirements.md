# requirements: cognitive-delivery-control-plane

## Scope

Spec 0001 installs the Cognitive Delivery Control Plane (CDCP)
governance scaffold in supplier-risk-rag-agent. The repo already runs
deterministic CI evals and pytest. This spec adds the parallel records
that name the why (decisions), the what-we-reuse (skills), and the
what-we-learned (dreams), plus the executable gates that fail builds
when any of those records drift out of shape. It also adds the
operating-model layer: role contracts, a tool registry, policy files,
state machines, and workflows under `.agents/`.

The CDCP shape itself lives in `../athena-site/ops/control-plane.md`.
This repo references those contracts and does not duplicate them.

## Requirements

### R-CDCP-001: every shipped requirement carries a decision record

WHEN a requirement `R-*-NNN` lands in any `specs/NNNN-*/requirements.md`,
THE SYSTEM SHALL hold at least one `decisions/DEC-*.md` file whose
front-matter `requirement:` field names that ID before the commit
reaches main.

Acceptance:
- `scripts/spec_check.py` walks every defined R-* ID and confirms one or
  more DEC files reference it via the front-matter `requirement:` key.
- An allowlist file at `decisions/.spec-check-allowlist.yaml` lists
  R-* IDs whose backfill DECs land in a later pass; the gate skips
  the allowlisted IDs and prints them as deferred work.
- R-CDCP-* IDs covered by `DEC-CDCP-001-install-cdcp-governance.md`
  count as resolved through that single DEC.

### R-CDCP-002: decision files conform to the cross-repo schema

WHEN a `decisions/DEC-*.md` file lands, THE SYSTEM SHALL match the
`decision.schema.json` contract sourced from
`https://raw.githubusercontent.com/AthenaTheOwl/athena-site/main/ops/schemas/decision.schema.json`.

Acceptance:
- `scripts/validate_decisions.py` reads every `decisions/DEC-*.md`,
  parses the YAML front-matter, and validates against the cross-repo
  schema.
- The script keeps a local cache copy at
  `ops/schemas-cache/decision.schema.json` so CI runs offline without
  a network fetch.
- The script exits 1 on any violation and exits 0 only when every DEC
  parses and validates clean.

### R-CDCP-003: dream-job outputs conform to the cross-repo schema

WHEN a weekly dream run writes an output JSON file to
`dreams/<week>/output.json`, THE SYSTEM SHALL match the
`dream-output.schema.json` contract from athena-site.

Acceptance:
- A future `scripts/validate_dreams.py` (lands with the first real
  dream output in a later pass) walks `dreams/**/output.json` and
  validates.
- `dreams/README.md` documents the eight dream modes and the
  human-gate rule for promotion candidates.
- The first dream output lands on a future week; this requirement
  reserves the contract.

### R-CDCP-004: every release is recorded in the release ledger

WHEN a commit reaches main and represents shippable scope, THE SYSTEM
SHALL record the release in `ops/RELEASE_LEDGER.md` with date, SHA,
title, scope (one or two sentences), and proof refs.

Acceptance:
- `ops/RELEASE_LEDGER.md` carries one entry per released commit.
- The initial backfill records the six pre-CDCP commits from `70f3253`
  through `58797c6`.
- Each entry names which gates the release passed.

### R-CDCP-005: every reset is recorded in the reset ledger

WHEN a force-push, history rewrite, or production rollback happens,
THE SYSTEM SHALL append an entry to `ops/RESET_LEDGER.md` with date,
operator, the from/to SHAs, and a one-line cause.

Acceptance:
- `ops/RESET_LEDGER.md` exists with a documented format header.
- The initial state records "No resets recorded." until the first
  reset.
- Operators do not silently rewrite history; the ledger entry lands
  in the same push that performs the rewrite.

### R-CDCP-006: coding agents read the agent contract first

WHEN a coding agent (Claude, Codex, or other) begins acting on this
repo, THE SYSTEM SHALL provide a single `.agents/AGENTS.md` file that
names coding style, domain rules, workflow conventions, and cross-repo
links.

Acceptance:
- `.agents/AGENTS.md` exists at the documented path.
- The file names the four sections: coding style, domain decisions,
  workflow conventions, cross-repo links.
- The agent contract points at the gate scripts under `scripts/`.

### R-CDCP-007: skills graduate through a packaged ledger

WHEN a recurring pattern earns reuse, THE SYSTEM SHALL extract it as
`.agents/skills/<name>/SKILL.md` with version, owner_guild, and an
evals reference (which may start empty with a TODO).

Acceptance:
- `.agents/skills/run-supplier-risk-query/SKILL.md` graduates the
  existing supplier-risk RAG query pattern from `src/agent/`.
- The SKILL.md front-matter matches the cross-repo `skill.schema.json`
  shape.
- Promotion past the initial version requires `human_approval` per
  the promotion_policy field.

### R-CDCP-008: CI gate failures block merge to main

WHEN any of `spec_check`, `voice_lint`, `validate_decisions`,
`validate_roles`, `validate_tools`, or `validate_policies` fails,
THE SYSTEM SHALL fail the CI job and block the PR from merging.

Acceptance:
- `.github/workflows/gates.yml` runs all six python gates in a
  dedicated `gates` job.
- The existing `tests.yml` and `evals.yml` workflows continue to run
  alongside.
- A failed gate causes the GitHub check to fail.

### R-CDCP-009: dream promotion candidates stay human-gated

WHEN a dream output proposes a memory update, generated test, skill
patch, or backlog item, THE SYSTEM SHALL hold the candidate behind
human review and forbid auto-merge of those patches.

Acceptance:
- Every candidate in a future dream output carries
  `human_review_required: true` per the cross-repo schema's default.
- The agent contract `.agents/AGENTS.md` repeats the rule.
- The policy `.agents/policies/dream-candidates-require-human-approval.yaml`
  encodes the rule for the policy engine.

### R-CDCP-010: cross-repo schemas remain the source of truth

WHEN this repo references a CDCP artifact contract, THE SYSTEM SHALL
point at `athena-site/ops/schemas/<name>.schema.json` and avoid
duplicating the schema body in this repo.

Acceptance:
- `scripts/validate_decisions.py`, `validate_roles.py`,
  `validate_tools.py`, and `validate_policies.py` each fetch by URL
  with a local cache fallback.
- The local cache under `ops/schemas-cache/` is documented as a cache,
  not a source.
- New schema fields land in athena-site first; this repo follows.
