# .agents/CATALOG.md

Index of every role, tool, policy, state machine, and workflow
registered under `.agents/`. The `validate_*.py` scripts in
`scripts/` walk these files and validate each against the cross-repo
schema set from athena-site.

## Roles (6)

| ID | Guild | Mission |
|---|---|---|
| `control.coordinator` | control | Route a change through the workflow without overstepping into any step. |
| `product.spec-writer` | product | Write the six-file spec ledger and one DEC per R-* before any code lands. |
| `engineering.implementation` | engineering | Land the narrowest traceable code slice; never touch prompts without paired eval results. |
| `engineering.code-reviewer` | engineering | Read the diff against the spec and the DEC; never edit code. |
| `science.proof-gate-runner` | science | Own the four eval suites and the six python governance gates; refuse merges that regress any axis. |
| `learning.dream-orchestrator` | learning | Run the weekly offline-cognition pass; emit human-gated promotion candidates. |

Each role folder under `.agents/roles/<id>/` carries:

- `role.yaml` — schema-validated contract.
- `instructions.md` — narrative guidance.
- `tools.yaml` — allowed-tool subset (cross-checks role.yaml).
- `output.schema.json` — shape of the role's output artifact.
- `gates.yaml` — gates the role's run must pass.

## Tools (16)

Registered in `.agents/tools.yaml`. Categories:

- **repo**: `repo.read`, `repo.apply_patch`, `dream.read_recent_commits`
- **shell**: `tests.run`, `gates.run_voice_lint`, `gates.run_spec_check`, `gates.run_validate_decisions`, `gates.run_validate_roles`, `gates.run_validate_tools`, `gates.run_validate_policies`, `streamlit.local_run`
- **eval**: `eval.run_recall_at_5`, `eval.run_citation_faithfulness`, `eval.run_abstention`, `eval.run_refusal`
- **skill**: `dream.write_candidate`

The high-risk write tool `repo.apply_patch` carries the forbidden
path list (`.env`, `secrets/**`, `src/agent/prompts/**`,
`data/raw/**`, `.streamlit/secrets.toml`).

## Policies (6)

Registered in `.agents/policies/`. Sorted by priority (higher wins):

| ID | Priority | Decision |
|---|---|---|
| `eval-suite-required-before-prompt-change` | 110 | require_approval |
| `coordinator-routing-only` | 100 | deny |
| `reviewer-cannot-edit-code` | 100 | deny |
| `dream-candidates-require-human-approval` | 90 | require_approval |
| `implementation-can-edit-code` | 80 | allow |
| `default-deny` | 0 | deny |

The default-deny baseline sits at priority 0; every other policy is
an explicit grant or require_approval at higher priority.

## State machines (3)

Registered in `.agents/state-machines/`:

- `spec-lifecycle.yaml` — drafted → approved → in_implementation → complete → superseded.
- `run-lifecycle.yaml` — queued → in_progress → awaiting_gate → awaiting_approval → completed (or failed / escalated).
- `release-lifecycle.yaml` — candidate → shipped → rolled_back.

## Workflows (4)

Registered in `.agents/workflows/`:

- `single-change.yaml` — intake → spec → architecture → implementation → code_review → tests → proof_gates → human_approval → release.
- `weekly-dream.yaml` — pull_history → run_modes → write_report → write_output_json → human_review.
- `incident-response.yaml` — contain → diagnose → decide → record_reset (conditional) → postmortem.
- `prompt-or-model-change.yaml` — baseline_capture → change_lands → variant_eval → compare_deltas → record_decision → merge_or_revert. Repo-specific; encodes the faithfulness-floor rule and the precedent set by the cross-encoder reranker experiment.

## Gates

| Script | What it checks |
|---|---|
| `scripts/voice_lint.py` | Voice rules over governance copy (specs, decisions, dreams, agents, ops). |
| `scripts/spec_check.py` | Six-file spec ledger, R-* prefix set, traceability, DEC coverage. |
| `scripts/validate_decisions.py` | DEC files parse against the cross-repo decision schema. |
| `scripts/validate_roles.py` | Role YAML parses against the cross-repo role schema. |
| `scripts/validate_tools.py` | Tool registry parses against the cross-repo tool schema. |
| `scripts/validate_policies.py` | Policy YAML parses against the cross-repo policy schema. |

The existing `tests.yml` (pytest with 70% coverage gate) and
`evals.yml` (deterministic eval runner) workflows continue to run
alongside the new gates job.

## Deferred work

- The full 44-role operating-model catalog from athena-site is
  deferred. Six core roles cover the single-change flow this repo
  runs today; later specs land additional roles as the surfaces
  earn them.
- Enforcement of the `eval-suite-required-before-prompt-change`
  coupling in CI (today the policy file encodes the rule and the
  workflow YAML documents the steps; a future commit wires the
  enforcement into a CI check that fails when a prompt path lands
  without a paired eval report).
- A `validate_dreams.py` gate lands when the first
  `dreams/YYYY-WNN/output.json` file lands.
- A `validate_skills.py` gate lands when the second skill
  graduates.
