# traceability: deploy-and-secrets

| Requirement | Design surface | Planned proof | Owner role |
|---|---|---|---|
| R-DEP-001 | `app.py` `sidebar_keys()` + `docs/trust_model.md` + `.env.example` + `.gitignore` for `.env` and `.streamlit/secrets.toml` | `DEC-DEP-001-byok-streamlit-no-committed-keys.md` + the deployed demo URL serving `app.py` with no committed keys | `engineering.implementation` |
| R-DEP-002 | `app.py` `render_answer` `MissingKeyError` catch + the local cited-answer path | a demo run with no key returns the deterministic retrieval preview message; allowlisted under `deferred:` until DEC-DEP-002 lands | `engineering.implementation` |
| R-DEP-003 | `src/config.py` `STREAMLIT_LOCAL` env check + `README.md` local dev section | a local dev run with `STREAMLIT_LOCAL=1` loads `.env`; unset, it does not; allowlisted under `deferred:` until DEC-DEP-003 lands | `engineering.implementation` |
