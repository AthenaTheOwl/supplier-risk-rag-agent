# traceability: deploy-and-secrets

| Requirement | Design surface | Decision | Planned proof | Owner role |
|---|---|---|---|---|
| R-DEP-001 | `app.py` `sidebar_keys()` + `docs/trust_model.md` + `.env.example` + `.gitignore` for `.env` and `.streamlit/secrets.toml` | `DEC-DEP-001-byok-streamlit-no-committed-keys.md` | the deployed demo URL serving `app.py` with no committed keys | `owner_role: engineering.implementation` |
| R-DEP-002 | `app.py` `render_answer` `MissingKeyError` catch + the local cited-answer path | `DEC-DEP-002-missing-key-falls-back-to-deterministic-retrieval.md` | a demo run with no key returns the deterministic retrieval preview message | `owner_role: engineering.implementation` |
| R-DEP-003 | `src/config.py` `STREAMLIT_LOCAL` env check + `README.md` local dev section | `DEC-DEP-003-streamlit-local-env-gate-for-dotenv-loading.md` | a local dev run with `STREAMLIT_LOCAL=1` loads `.env`; unset, it does not | `owner_role: engineering.implementation` |
