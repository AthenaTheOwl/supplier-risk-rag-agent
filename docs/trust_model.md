# Trust Model

## BYOK guarantee

The Streamlit app is bring-your-own-key. Visitors paste API keys into password
inputs in the sidebar. Those values are held in `st.session_state` for the
browser session and are passed explicitly to clients when live calls are
requested.

The app does not set environment variables from user input. It does not use
`st.secrets`. `.streamlit/secrets.toml` is gitignored and should not exist in
the repo.

## Local environment fallback

Local `.env` fallback is allowed only when `STREAMLIT_LOCAL=1`. This path exists
for developer convenience and is not relied on for deployed Streamlit behavior.

## Logging and telemetry

No API keys are printed, logged, stored, or sent to telemetry by this codebase.
The repo does not configure analytics or tracing. Vendor SDK calls receive keys
only through explicit `Keys` objects.

## CI behavior

CI evals and tests require no real API keys. They run against the checked-in
sample corpus using deterministic local retrieval and evaluators.
