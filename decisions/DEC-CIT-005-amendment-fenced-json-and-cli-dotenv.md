---
id: DEC-CIT-005-amendment-fenced-json-and-cli-dotenv
spec: specs/0006-citation-faithfulness/
requirement: R-CIT-001
amends: DEC-CIT-005-live-evidence-order-only
date: 2026-10-20
status: proposed
reversible: true
decision: |
  Amend DEC-CIT-005 on two points; the rest of DEC-CIT-005 stands.
  1. Fence: a live reply may be one JSON object bare, or wrapped as a whole
     in a single ``` or ```json fence. The answerer strips that one fence and
     then runs the unchanged citation_labels permutation checks. Prose around
     the fence, a second fence, several objects, and malformed JSON are still
     rejected. "Extra-content output" in DEC-CIT-005 means content other than
     that one wrapping fence.
  2. Dotenv gate scope: the STREAMLIT_LOCAL=1 gate applies to the Streamlit
     path (`get_keys`, `get_model_config`). Local CLI jobs read `.env` without
     the gate through `get_cli_keys`, `get_cli_model_config` (used by
     `src/evals/runner.py`) and `sec_user_agent`. The Streamlit app calls none
     of the CLI helpers. The same scope applies to the "reads `.env` only when
     `STREAMLIT_LOCAL=1`" wording in DEC-DEP-003 and specs/0005.
  The live ordering prompt is inline in `src/agent/answerer.py`. It is not
  `src/agent/prompts/answerer.md` and is not part of `prompt_snapshot_hash`,
  so a change to it still needs a paired baseline/variant report under
  `reports/`.
alternatives:
  - label: keep rejecting every fenced reply
    rejected_because: |
      Chat models often wrap JSON in a code fence. Rejecting it fails safe but
      sends those replies to the deterministic fallback, which hides the
      bounded ordering path DEC-CIT-005 approved. Stripping one whole-reply
      fence admits no generated prose.
  - label: put the eval runner behind STREAMLIT_LOCAL as well
    rejected_because: |
      Before DEC-CIT-005 the runner read `.env` model settings directly.
      Gating it silently changed which provider and model a CLI eval run
      recorded. The gate exists to protect the deployed Streamlit app, which
      never runs the CLI helpers.
  - label: edit DEC-CIT-005 in place
    rejected_because: |
      DEC-CIT-005 is approved. Repo convention records a change to an approved
      DEC as a sibling amendment (DEC-CIT-002-amendment-reversibility-mitigation).
rationale: |
  Both changes restore intent and do not widen the model's authority. The
  fence is stripped before the same complete-permutation check, so no model
  text reaches the displayed answer. The CLI dotenv read restores pre-Codex
  runner behavior while the deployed Streamlit path keeps its gate.
evidence:
  - kind: test
    ref: tests/test_live_evidence_order.py
  - kind: test
    ref: tests/test_config.py
  - kind: doc
    ref: reports/live-fence-cli-env-baseline.json
  - kind: doc
    ref: reports/live-fence-cli-env-variant.json
  - kind: doc
    ref: docs/trust_model.md
  - kind: doc
    ref: docs/failure_modes.md
rollback: |
  Remove the fence strip in `_live_citation_order` and point the runner back at
  `get_model_config`; delete this amendment. DEC-CIT-005 is unchanged by it.
owner: engineering.implementation
systems_map: |
  A safety gate written for one entry point (the deployed app) was applied to
  a shared helper and changed the behavior of an unrelated entry point (CLI
  evals); a strict parser rejected a harmless wrapper and hid the path it guards.
transferable_principle: |
  Scope a gate to the boundary it protects, and strip only wrappers that cannot
  carry content past the check that follows.
falsification_test: |
  A fenced reply with any text outside the single fence reaches live_ordered,
  or a Streamlit run with STREAMLIT_LOCAL unset reads `.env`.
adoption_ladder:
  minimum_viable: Accept one whole-reply fence; route CLI model config through get_cli_model_config.
  mid_adoption: Record fence acceptance in answer metadata alongside rejected and failed modes.
  full_adoption: Check the bounded live path in a credentialed deployment smoke.
  monitoring_signals:
    - Rejected live output frequency.
    - Provider and model recorded in CLI eval run records.
---

## Decision

Amend DEC-CIT-005. A live reply may be one JSON object, bare or wrapped as a
whole in a single ``` or ```json fence; everything else is still rejected. The
STREAMLIT_LOCAL `.env` gate covers the Streamlit path (`get_keys`,
`get_model_config`); CLI jobs read `.env` through `get_cli_keys`,
`get_cli_model_config` and `sec_user_agent`. The live ordering prompt is inline
in `src/agent/answerer.py`, outside `prompt_snapshot_hash`, so changes to it
need a paired report under `reports/`.

## Validation

`tests/test_live_evidence_order.py` covers accepted fenced and padded replies
and rejected prose-wrapped and malformed ones. `tests/test_config.py` covers the
Streamlit gate, the CLI helper, and the runner's recorded provider. The
`reports/live-fence-cli-env-*` pair shows the five offline suite scores
unchanged. No live provider request was made.
