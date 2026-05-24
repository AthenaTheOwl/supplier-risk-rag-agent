# requirements: deploy-and-secrets

## Scope

Spec 0005 backfills the bring-your-own-key (BYOK) deployment pattern
the Streamlit demo ships under. Visitors paste API keys into the
sidebar; the keys live in `st.session_state` only; no keys are
committed to the repo, set as Streamlit secrets, or read from
`st.secrets`. This spec records the requirements the deploy pattern
answers.

## Requirements

### R-DEP-001: the deployed demo runs BYOK with no committed keys

WHEN a visitor lands on the deployed Streamlit demo, THE SYSTEM
SHALL accept their API keys via password inputs in the sidebar and
SHALL NOT use any platform-paid keys, Streamlit secrets, or
committed key material.

Acceptance:
- `app.py` calls `sidebar_keys()` and stores the values in
  `st.session_state["anthropic_key"]` and
  `st.session_state["openai_key"]`.
- `docs/trust_model.md` documents the rule (no `st.secrets`, no env
  reads from user input).
- `.env.example` is the only env file shipped; `.env` and
  `.streamlit/secrets.toml` are gitignored.
- The deployed demo URL in `README.md` runs the same `app.py` shipped
  in this repo.

### R-DEP-002: a missing key falls back to deterministic retrieval

WHEN a visitor has not pasted a key but asks a question, THE SYSTEM
SHALL return a deterministic retrieval preview (citations from the
sample corpus) instead of failing or paraphrasing.

Acceptance:
- `render_answer` catches `MissingKeyError`, sets
  `use_live_llm = False`, and runs the local cited-answer path.
- The user-facing message names the fallback explicitly ("Showing
  deterministic retrieval preview without a live LLM call.").
- A failed live LLM call (rate limit, bad key) also falls back to
  the local cited answer with an error message.

### R-DEP-003: local dev re-uses the BYOK code path via opt-in env

WHEN a developer wants to test live LLM calls without pasting into
the sidebar each time, THE SYSTEM SHALL allow `.env` loading only
when `STREAMLIT_LOCAL=1`, so deployed behavior never silently
ingests environment keys.

Acceptance:
- `src/config.py` reads `.env` only when `STREAMLIT_LOCAL=1` is set.
- The README documents the env var as the local-dev opt-in.
- A deployed Streamlit run with `STREAMLIT_LOCAL` unset never reads
  `.env`.
