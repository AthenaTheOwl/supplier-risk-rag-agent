# No. 13 - supplier-risk-rag-agent

A supplier-risk RAG agent with receipts. SEC filing excerpts in, cited answers
out. Retrieval quality, citation faithfulness, abstention behavior, and
regression evals are wired into CI.

demo: https://supplier-risk-rag-agent.streamlit.app

## bring your own key

The deployed demo runs on your API keys, not mine. Paste your Anthropic key
into the sidebar when you want live Claude answer wording. The key lives in
your browser session only — never logged, never stored. An OpenAI key is
optional, and only needed for live embedding or ingestion experiments.

Local `.env` fallback is off unless `STREAMLIT_LOCAL=1`.

## what it does

Answers supplier-risk questions like:

- "Which suppliers disclosed customer-concentration risk?"
- "What export-control exposure was cited in 2024 filings?"
- "Which firms mentioned advanced packaging capacity constraints?"

Every claim has a verified citation. Unsupported or out-of-scope claims get
refused, not paraphrased.

## stack

Python 3.11 · Anthropic SDK · OpenAI embeddings · Chroma · Streamlit · uv ·
pytest · deterministic local evals.

Default Anthropic model is `claude-sonnet-4-6`. The older `claude-sonnet-4-20250514`
snapshot is deprecated (retirement planned June 15, 2026), so it isn't the
default here. See [models overview](https://docs.anthropic.com/en/docs/about-claude/models/overview)
and [model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations).

## local dev

```powershell
python -m uv sync --all-groups
Copy-Item .env.example .env
$env:STREAMLIT_LOCAL = "1"
python -m uv run streamlit run app.py
```

Plain `uv` also works when it's on PATH. On this machine, `python -m uv` is
the reliable form.

## evals

```powershell
python -m uv run python -m src.evals.runner --suite all --report reports/local_run.html
```

CI evals don't need real API keys. They run against the checked-in sample
corpus with deterministic local retrieval, citation validation, refusal
checks, and a regression-quality proxy. Live LLM calls are optional, for
demo use.

## ingestion

The checked-in sample corpus is enough for local demos and CI. Full EDGAR
metadata fetches are gated behind `--full-fetch` and use a custom SEC
`User-Agent`.

```powershell
python -m uv run python -m src.ingest.run_ingest
python -m uv run python -m src.ingest.run_ingest --full-fetch
```
