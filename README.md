# No. 13 - supplier-risk-rag-agent

A supplier-risk RAG agent with receipts. SEC filing excerpts in, cited answers out.
Retrieval quality, citation faithfulness, abstention behavior, and regression evals
are wired into CI.

Demo: Streamlit URL to be added after deployment.

## Bring your own key

The deployed demo runs on your API keys, not mine. Paste your Anthropic key into
the sidebar when you want live Claude answer wording. The key lives only in your
browser session and is never logged or stored. An OpenAI key is optional and is
only needed for live embedding or ingestion experiments.

Local `.env` fallback is disabled unless `STREAMLIT_LOCAL=1`.

## What it does

Answers supplier-risk questions like:

- "Which suppliers disclosed customer-concentration risk?"
- "What export-control exposure was cited in 2024 filings?"
- "Which firms mentioned advanced packaging capacity constraints?"

Every claim has a verified citation. Unsupported or out-of-scope claims are
refused.

## Stack

Python 3.11, Anthropic SDK, OpenAI embeddings, Chroma, Streamlit, uv, pytest,
and deterministic local evals.

The default Anthropic model is `claude-sonnet-4-20250514`. Anthropic's official
docs identify it as a Claude Sonnet 4 API model name; current deprecation docs
list it as deprecated with retirement planned for June 15, 2026. This repo still
pins it because the Worker 4 brief explicitly forbids `claude-sonnet-4-6`.

https://docs.anthropic.com/en/docs/about-claude/models/overview
https://platform.claude.com/docs/en/about-claude/model-deprecations

## Local dev

```powershell
python -m uv sync --all-groups
Copy-Item .env.example .env
$env:STREAMLIT_LOCAL = "1"
python -m uv run streamlit run app.py
```

Plain `uv` also works when it is on PATH. On this machine, `python -m uv` is the
reliable form.

## Evals

```powershell
python -m uv run python -m src.evals.runner --suite all --report reports/local_run.html
```

CI evals do not need real API keys. They run against the checked-in sample
corpus with deterministic local retrieval, citation validation, refusal checks,
and a regression-quality proxy. Live LLM calls are optional for demo use.

## Ingestion

The checked-in sample corpus is enough for local demos and CI. Full EDGAR
metadata fetches are gated behind `--full-fetch` and use a custom SEC
`User-Agent`.

```powershell
python -m uv run python -m src.ingest.run_ingest
python -m uv run python -m src.ingest.run_ingest --full-fetch
```
