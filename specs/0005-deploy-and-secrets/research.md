# research: deploy-and-secrets

Research checked 2026-05-24.

- The BYOK pattern predates CDCP. The deployed Streamlit demo runs
  on visitor-supplied keys; no platform-paid keys are wired in. The
  decision was driven by hosting cost (linear in visitor traffic)
  and by a secrets-handling story visitors can audit by reading the
  sidebar code and `docs/trust_model.md`.
- `app.py` writes keys to `st.session_state` only. The keys never
  reach env vars, never reach `st.secrets`, and never get logged.
- The `STREAMLIT_LOCAL` opt-in keeps local dev convenient (paste
  once into `.env`) without changing deployed behavior.
- The deterministic retrieval fallback (when keys are missing or
  the live call fails) means the demo still shows real citations
  even without a vendor key.

## Why now

- The BYOK pattern is one of the most-visible decisions in the
  repo. Visitors interact with it on the first page load. The flat
  `DECISIONS.md` named the rule; spec 0005 backfills the R-* IDs so
  the rule has structured DEC coverage.
- The trust model document already exists. R-DEP-001 names the
  contract that document depends on.

## Alternatives considered

- Platform-paid keys (Streamlit secrets, hosted Anthropic key):
  rejected. Linear hosting cost in visitor traffic, plus a weaker
  secrets-handling story for visitors evaluating the demo.
- No public demo (local-only): rejected. The public demo is the
  load-bearing artifact for showing eval discipline to outside
  reviewers.
- Paid-tier-only public demo: rejected as premature. The BYOK
  fallback already makes the public demo free without committing the
  author to bill payment.
- Reading `st.secrets` in deployed mode: rejected. Visitors cannot
  audit `st.secrets`; the BYOK sidebar is auditable in two lines of
  `app.py`.

## Open questions

- If a future workspace adds a rate-limited platform key for users
  who do not have their own, how is it gated? Open. The current
  decision keeps the BYOK-only path; any future addition lands under
  a new DEC.
- Does the deployed Streamlit demo need a documented privacy-policy
  page beyond `docs/trust_model.md`? Open. The trust model lives in
  the repo today; a deployed copy of the same content may earn a
  dedicated page.
