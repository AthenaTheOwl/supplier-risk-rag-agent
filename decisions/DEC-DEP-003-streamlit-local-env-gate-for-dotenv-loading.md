---
id: DEC-DEP-003-streamlit-local-env-gate-for-dotenv-loading
spec: specs/0005-deploy-and-secrets/
requirement: R-DEP-003
date: 2026-05-24
status: approved
reversible: true
decision: |
  Gate `.env` loading on the `STREAMLIT_LOCAL=1` env var. `src/config.py`
  calls `load_dotenv(override=False)` only when `STREAMLIT_LOCAL` is
  set; otherwise the .env file on the deploy server is never read.
  Local developers who want to skip the sidebar paste step set
  `STREAMLIT_LOCAL=1` and put their keys in `.env`. Deployed Streamlit
  runs never set `STREAMLIT_LOCAL`, so the BYOK contract holds even
  if a stray `.env` lands on the deploy host.
alternatives:
  - label: always call `load_dotenv()` at startup
    rejected_because: |
      A `.env` file accidentally checked into the deploy image (or
      left over from a developer's local test) would silently inject
      keys into every visitor's request. The whole point of BYOK is
      that nothing on the deploy host knows the visitor's key; an
      always-on `load_dotenv` breaks that promise the first time a
      stray file lands.
  - label: never load .env (require manual env var exports)
    rejected_because: |
      Local development becomes painful. A developer would need to
      `export ANTHROPIC_API_KEY=...` in every terminal session or
      set up a shell profile. The `STREAMLIT_LOCAL` gate is the
      compromise: the convenience exists, but it is opt-in and
      explicit.
  - label: load .env only when a specific file (`secrets.local.env`) exists
    rejected_because: |
      Filename-based gating is implicit. A developer who copies the
      `.env.example` file to `.env` would not know the file is
      ignored until they paste a key and the app reads
      `st.session_state` instead. The env-var gate is explicit:
      `STREAMLIT_LOCAL=1` flips the behavior in one place that the
      developer sees on their command line.
rationale: |
  The deploy contract is BYOK. A visitor pastes a key into the
  Streamlit sidebar; the key lives in `st.session_state`; nothing on
  the deploy host holds it. A leftover `.env` on the deploy host
  would silently break this contract; the `STREAMLIT_LOCAL` gate is
  the defense against that failure mode.

  The gate is symmetric: a local developer who wants to skip the
  sidebar paste sets `STREAMLIT_LOCAL=1` and puts keys in `.env`.
  The convenience exists, but the deploy host never sets the
  variable, so the deploy host never reads `.env`. The asymmetry
  between local dev convenience and deployed-host strictness is
  the right shape; both operators get what they need.

  The deploy host on Streamlit Cloud does not set `STREAMLIT_LOCAL`.
  The README documents the env var as the local-dev opt-in. A new
  developer reading the README sees the variable and the file
  convention together; a new deploy operator reading the
  `docs/trust_model.md` sees the no-`.env`-on-deploy-host rule.
evidence:
  - kind: spec
    ref: specs/0005-deploy-and-secrets/
  - kind: doc
    ref: src/config.py (`_load_local_env_if_allowed` gates on `STREAMLIT_LOCAL=1`)
  - kind: doc
    ref: README.md (the local-dev opt-in section)
  - kind: doc
    ref: docs/trust_model.md (BYOK rule; no env reads on deploy)
  - kind: doc
    ref: .env.example (the developer-facing template)
rollback: |
  Single-file revert. Remove the `STREAMLIT_LOCAL` guard from
  `_load_local_env_if_allowed` and always call `load_dotenv`. Update
  `docs/trust_model.md` and the README to drop the env-var
  reference. The cost of rollback is high (BYOK contract regression);
  the cost of carrying the gate is one `if` block in `src/config.py`.
  Re-run the four-suite eval gate after any change.
owner: engineering.implementation
---

## decision

Gate `.env` loading on the `STREAMLIT_LOCAL=1` env var.
`src/config.py` calls `load_dotenv(override=False)` only when
`STREAMLIT_LOCAL` is set. Local developers who want to skip the
sidebar paste set `STREAMLIT_LOCAL=1` and put keys in `.env`.
Deployed runs never set the variable, so the BYOK contract holds
even if a stray `.env` lands on the deploy host.

## alternatives

- Always call `load_dotenv()` — a stray `.env` on deploy silently
  breaks BYOK.
- Never load `.env` — local development becomes painful.
- Filename-based gating (`secrets.local.env`) — implicit; the
  env-var gate is explicit.

## rationale

The deploy contract is BYOK. A leftover `.env` on the deploy host
would silently break it; the `STREAMLIT_LOCAL` gate is the defense.
The asymmetry between local-dev convenience and deployed-host
strictness is the right shape. The deploy host on Streamlit Cloud
does not set the variable.

## evidence

- `src/config.py` — the `_load_local_env_if_allowed` gate.
- `README.md` — the local-dev opt-in section.
- `docs/trust_model.md` — the no-env-on-deploy rule.
- `.env.example` — the developer-facing template.

## rollback

Single-file revert. Remove the gate and always call `load_dotenv`.
Update the trust model and README to drop the env-var reference.
The cost of rollback is high (BYOK regression); the cost of carrying
the gate is one `if` block.
