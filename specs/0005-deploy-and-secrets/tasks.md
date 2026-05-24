# tasks: deploy-and-secrets

Spec 0005 is a backfill spec. The BYOK pattern, the trust model
document, and the local dev fallback already shipped. This ledger
records the requirement IDs and pairs the first one with a DEC.

## Spec ledger

- [x] `specs/0005-deploy-and-secrets/requirements.md` with R-DEP-001..003.
- [x] `specs/0005-deploy-and-secrets/design.md`.
- [x] `specs/0005-deploy-and-secrets/tasks.md` (this file).
- [x] `specs/0005-deploy-and-secrets/acceptance.md`.
- [x] `specs/0005-deploy-and-secrets/research.md`.
- [x] `specs/0005-deploy-and-secrets/traceability.md`.
- [x] `specs/README.md` lists the spec folder.

## Decision coverage

- [x] `decisions/DEC-DEP-001-byok-streamlit-no-committed-keys.md`
  resolves R-DEP-001.
- [ ] R-DEP-002 and R-DEP-003 land in
  `decisions/.spec-check-allowlist.yaml` under `deferred:` until a
  backfill pass writes their DECs.

## Code under this spec (already shipped, not changed by this spec)

- `app.py`
- `src/config.py`
- `docs/trust_model.md`
- `.env.example`
- `.gitignore` (the `.env` and `.streamlit/secrets.toml` ignore lines)

## Verification

- [x] `python scripts/spec_check.py` exits 0 with R-DEP-001 resolved
  and R-DEP-002..003 deferred.
- [x] `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean.
- [x] The deployed demo at the URL in `README.md` continues to run
  `app.py` with BYOK keys.
