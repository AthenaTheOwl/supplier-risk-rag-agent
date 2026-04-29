# Decisions

## Anthropic model ID

The repo defaults to `claude-sonnet-4-6`, the active Claude Sonnet 4.6 API ID in
Anthropic's model overview. The older Sonnet 4 snapshot
`claude-sonnet-4-20250514` is deprecated and scheduled for retirement on June
15, 2026, so it is documented only as a migration note.

https://docs.anthropic.com/en/docs/about-claude/models/overview
https://platform.claude.com/docs/en/about-claude/model-deprecations

## BYOK first

Streamlit reads API keys from password inputs and keeps them in
`st.session_state`. It only falls back to local environment variables when
`STREAMLIT_LOCAL=1`, which keeps deployed Streamlit Cloud behavior strictly
bring-your-own-key.

## Deterministic CI and evals

CI must pass without vendor keys. Retrieval, citation faithfulness, refusal, and
regression suites run over the checked-in sample corpus with local deterministic
evaluators. Live LLM calls are optional and only run when a caller supplies keys.

## Sample manifest repaired

The sample manifest was corrected against the SEC company tickers feed to avoid
duplicate or wrong CIK mappings. In particular, TSM uses `0001046179`, KLA uses
`0000319201`, Lam Research uses `0000707549`, ASML uses `0000937966`, and
Applied Materials uses `0000006951`.

## Local-only repository state

The parent agent will handle remote creation and push. This worker initializes
and commits only a local git repo after tests and evals pass.
