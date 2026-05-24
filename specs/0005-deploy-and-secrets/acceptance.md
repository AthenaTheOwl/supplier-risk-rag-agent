# acceptance: deploy-and-secrets

## Gates

- `python scripts/voice_lint.py` exits 0 across the new spec files.
- `python scripts/spec_check.py` exits 0 with R-DEP-001 resolved by
  `DEC-DEP-001-byok-streamlit-no-committed-keys.md` and R-DEP-002..003
  listed under `deferred:` in the allowlist.
- `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean.

## Done means

Spec 0005 is done when:

1. The six ledger files land under `specs/0005-deploy-and-secrets/`.
2. `DEC-DEP-001-*.md` lands under `decisions/`.
3. R-DEP-002 and R-DEP-003 land under `deferred:` in the allowlist.
4. `app.py`, `src/config.py`, `docs/trust_model.md`, `.env.example`,
   and the `.gitignore` ignore lines are unchanged by this spec.

## Explicit non-acceptance

- No edits to `app.py` or `src/config.py`. The BYOK code is the
  evidence; this spec records the why.
- No `st.secrets` introduction. No platform-paid keys. No paywall.
- No change to the `STREAMLIT_LOCAL` opt-in for local `.env`
  loading.
