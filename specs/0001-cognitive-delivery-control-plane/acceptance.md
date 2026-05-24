# acceptance: cognitive-delivery-control-plane

## Gates

- `python scripts/voice_lint.py` exits 0 across the governance copy
  (specs, decisions, dreams, agents, ops markdown).
- `python scripts/spec_check.py` exits 0 with one active spec
  (`0001-cognitive-delivery-control-plane`).
- `python scripts/validate_decisions.py` exits 0 with one DEC file
  validated (`DEC-CDCP-001-install-cdcp-governance`).
- `python scripts/validate_roles.py` exits 0 with six role files
  validated.
- `python scripts/validate_tools.py` exits 0 with the tool registry
  validated.
- `python scripts/validate_policies.py` exits 0 with six policy files
  validated.
- The existing `tests.yml` (pytest with 70% coverage gate) and
  `evals.yml` (deterministic eval runner) workflows remain green;
  this spec does not touch the code paths those gates cover.

## Done means

Spec 0001 is done when:

1. The CDCP scaffold (`specs/0001-*/`, `decisions/`, `dreams/`,
   `.agents/`, `ops/`) lands as files under
   `e:\claude_code\random-apps\supplier-risk-rag-agent`.
2. `scripts/validate_decisions.py` walks the one DEC file and exits
   0.
3. `scripts/spec_check.py` walks every R-* and confirms every one is
   covered by a DEC, allowlisted, or covered by the bootstrap
   exemption for R-CDCP-*.
4. `scripts/validate_roles.py`, `validate_tools.py`, and
   `validate_policies.py` walk the operating-model files and exit 0.
5. The new CI gates workflow runs the six python gates.
6. The root README points readers at the governance artifacts.

## Explicit non-acceptance

- No edits to `app.py`, `src/agent/prompts/`, or `src/retrieval/`.
  The deployed Streamlit app stays untouched.
- No backfill DECs for retrieval, agent, ingestion, or eval
  requirements in this pass — those R-* IDs land when each subsystem
  earns its own spec (`0002-ingestion`, `0003-retrieval`, etc.) and
  the DECs land alongside.
- No first dream output; the README documents the format and the
  gate for that artifact lands when the first weekly dream lands.
- No new top-level pyproject dependencies. `jsonschema` and `pyyaml`
  are loaded lazily by the gate scripts; the scripts print a clear
  install hint and exit 1 if either is missing.
- The 44-role full operating-model catalog from athena-site is
  deferred. This spec installs the six core roles needed for
  single-change flow; the rest land as the repo grows.
