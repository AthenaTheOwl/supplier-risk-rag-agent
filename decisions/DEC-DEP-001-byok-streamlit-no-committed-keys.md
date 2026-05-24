---
id: DEC-DEP-001-byok-streamlit-no-committed-keys
spec: specs/0005-deploy-and-secrets/
requirement: R-DEP-001
date: 2026-05-24
status: approved
reversible: true
decision: |
  Run the deployed Streamlit demo as bring-your-own-key. Visitors
  paste Anthropic and (optional) OpenAI keys into password inputs in
  the sidebar; keys live in `st.session_state` only; the repo
  commits no platform-paid keys, does not read `st.secrets`, and
  does not set environment variables from user input. Local dev gets
  a `.env` fallback gated behind `STREAMLIT_LOCAL=1` so deployed
  behavior never silently ingests environment keys.
alternatives:
  - label: platform-paid keys (Streamlit secrets or hosted Anthropic key)
    rejected_because: |
      Linear hosting cost in visitor traffic. The author would be on
      the hook for whatever traffic the deployed demo attracts.
      Visitors also cannot audit `st.secrets`; the trust story is
      strictly weaker.
  - label: no public demo (local-only)
    rejected_because: |
      The deployed demo is the load-bearing artifact for showing the
      eval discipline to outside reviewers. Removing it would mean
      hiring managers cannot click through to a live cited answer.
  - label: paid-tier-only public demo
    rejected_because: |
      Premature. BYOK keeps the demo free without committing the
      author to bill payment. A paywall adds infrastructure (auth,
      billing, rate limiting) for no measured demand to gate.
  - label: read `st.secrets` for fallback keys
    rejected_because: |
      Visitors cannot audit `st.secrets` and the platform's secrets
      store is itself a trust boundary. The BYOK sidebar is auditable
      in two lines of `app.py`. Mixing in an `st.secrets` fallback
      would muddy the contract documented in `docs/trust_model.md`.
rationale: |
  Two problems get solved at once. First: hosted demo cost. The
  author does not pay vendor charges for visitor queries; the
  visitor brings their own key. Second: a secrets-handling story
  visitors can verify. The sidebar code is short, the trust model
  document names the four rules (BYOK guarantee, local env fallback,
  logging policy, CI behavior), and `.streamlit/secrets.toml` is
  gitignored and absent from the repo.

  The fallback behavior carries weight. A visitor with no key still
  gets a real cited answer from the deterministic retrieval path;
  `render_answer` catches `MissingKeyError` and explicitly tells the
  user "Showing deterministic retrieval preview without a live LLM
  call." A failed live call also falls back. The demo is useful
  before the visitor commits a key.

  Local dev keeps a convenient path: set `STREAMLIT_LOCAL=1`, paste
  keys into `.env`, run the same code that runs in deploy. The env
  var gate means deploys cannot silently load `.env`; they would
  need an operator to set the variable on the hosting platform,
  which is a visible action.
evidence:
  - kind: spec
    ref: specs/0005-deploy-and-secrets/
  - kind: doc
    ref: app.py (sidebar_keys + render_answer fallback path)
  - kind: doc
    ref: docs/trust_model.md
  - kind: doc
    ref: .env.example
  - kind: doc
    ref: .gitignore (.env and .streamlit/secrets.toml ignore lines)
  - kind: doc
    ref: README.md (BYOK section)
  - kind: doc
    ref: src/config.py (STREAMLIT_LOCAL env check)
rollback: |
  Add an `ANTHROPIC_API_KEY` secret to the Streamlit platform, edit
  `src/config.py` to read `st.secrets` when present, gate the
  deployed demo behind a paywall or auth wall, and update
  `docs/trust_model.md` to reflect the new contract. The `app.py`
  sidebar can stay (as an override path) or be removed; the trust
  model document carries the visible contract either way. The CI
  evals are unaffected; they run on the sample corpus with no
  vendor keys.
owner: engineering.implementation
---

## decision

Run the deployed Streamlit demo as bring-your-own-key. Visitors
paste keys into the sidebar; keys live in `st.session_state` only;
no platform-paid keys, no `st.secrets`, no committed key material.
Local dev keeps a `.env` fallback gated behind `STREAMLIT_LOCAL=1`.

## alternatives

- Platform-paid keys — linear hosting cost in visitor traffic and a
  weaker auditability story.
- No public demo — removes the load-bearing artifact reviewers click
  through to.
- Paid-tier-only — premature; adds auth/billing/rate-limiting for no
  measured demand.
- Read `st.secrets` for fallback — muddies the trust contract
  visitors cannot audit.

## rationale

BYOK solves the demo-cost problem and the trust-handling problem in
one move. The sidebar code is short, the trust model document is
explicit, and the deterministic retrieval fallback means a
key-less visitor still gets a cited answer. The `STREAMLIT_LOCAL`
env gate keeps local dev convenient without silently importing
`.env` in deploys.

## evidence

- `app.py` — the sidebar and the missing-key fallback.
- `docs/trust_model.md` — the four documented rules.
- `.env.example` — the sole env file shipped.
- `.gitignore` — the `.env` and `.streamlit/secrets.toml` ignore
  lines.
- `README.md` — the public BYOK section.
- `src/config.py` — the `STREAMLIT_LOCAL` env check.

## rollback

Add an `ANTHROPIC_API_KEY` Streamlit secret, edit `src/config.py` to
read `st.secrets`, gate the deployed demo behind a paywall, and
update `docs/trust_model.md`. CI evals are unaffected. The BYOK
sidebar can stay as an override or be removed.
