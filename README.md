# Supplier risk RAG agent

Twenty filing excerpts from ten CIKs. Ask about export controls and every answer has to point at a verbatim span; otherwise it refuses. The polite word is citation faithfulness. The useful word is receipts.

**Live demo:** [supplier-risk-rag-agent.streamlit.app](https://supplier-risk-rag-agent.streamlit.app)

The deployed app is BYOK. Paste your Anthropic key, and optionally your OpenAI key, into the sidebar. The key lives in `st.session_state` for the browser session only; it is never logged, stored, or persisted. CI evals run without keys.

## What makes this RAG worth reading

- Citation faithfulness is verified after generation. Every cited span must appear verbatim in a retrieved chunk; `src/retrieval/citations.py` raises if it does not.
- Four eval suites gate every push: retrieval quality, citation faithfulness, supplier-risk questions, and refusal cases.
- The default ranker is deterministic: 60% normalized BM25, 25% cosine over local hashing embeddings, and 15% term overlap.
- Cross-encoder reranking remains opt-in because the sample experiment broke citation faithfulness and was reverted.
- Anthropic is the default provider and OpenAI is the alternate via `LLM_PROVIDER`. Demo keys flow through an explicit `Keys` object, not environment reads.

## First thing to try

Open the demo, paste a key into the sidebar, and ask:

```text
Which suppliers disclosed export-control exposure?
```

Then inspect the citations. If a span cannot be verified against the retrieved text, the answer should refuse instead of sounding confident.

## Try it locally

```powershell
python -m uv sync --all-groups
Copy-Item .env.example .env       # set ANTHROPIC_API_KEY + OPENAI_API_KEY for local dev
$env:STREAMLIT_LOCAL = "1"
python -m uv run streamlit run app.py
```

For the hosted demo, paste keys directly in the sidebar. The trust model is documented at [docs/trust_model.md](docs/trust_model.md).

## Source corpus

The checked-in sample corpus holds 20 pre-chunked excerpts under `data/sample_corpus/`. They cover export controls, customer concentration, advanced packaging, supplier capacity, third-party foundries, and long-lead equipment risk.

Full EDGAR fetch is opt-in and applies a SEC-compliant `User-Agent` plus a rate cap.

## EDGAR refresh

The checked-in demo reads `data/sample_corpus/` by default. Live EDGAR refresh is a corpus-management job that writes ignored generated artifacts under `data/generated/edgar_corpus/`.

```powershell
# Plan the filings that would be downloaded; fetches submissions
# metadata only and does not write output files.
python -m uv run python -m src.ingest.run_ingest --refresh-edgar --dry-run

# Build a generated JSONL corpus in the same shape as sample_corpus.
python -m uv run python -m src.ingest.run_ingest --refresh-edgar `
  --manifest data/sample_manifest.json `
  --output data/generated/edgar_corpus/chunks.jsonl `
  --refresh-manifest data/generated/edgar_corpus/manifest.json
```

Set `SEC_USER_AGENT` to a descriptive application/contact string before live refresh. SEC fair-access guidance asks automated clients to declare a User-Agent and stay below 10 requests/second: https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm.

## Evidence gates

```powershell
python -m uv run pytest --cov=src --cov-fail-under=70
python -m uv run python -m src.evals.runner --suite all
python scripts/spec_check.py
python scripts/voice_lint.py
python scripts/validate_decisions.py
python scripts/validate_roles.py
python scripts/validate_tools.py
python scripts/validate_policies.py
```

The four eval suites run against the in-memory sample corpus with no vendor keys required.

## Live demo

Deploy with Streamlit Cloud using:

```text
streamlit_app.py
```

Local run:

```powershell
python -m uv run streamlit run streamlit_app.py
```

## Governance

The repo runs under the Cognitive Delivery Control Plane. Specs, decisions, agent contracts, release ledgers, reset ledgers, and validation scripts live in the open because citation discipline is easier to trust when the receipts are next to the app.

Key records:

- [DEC-CIT-001](decisions/DEC-CIT-001-verbatim-span-verification-post-generation.md) - verbatim span verification.
- [DEC-EVL-001](decisions/DEC-EVL-001-four-suite-eval-gate-with-thresholds.md) - four-suite eval gate.
- [DEC-RET-001](decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md) - deterministic hybrid ranker.
- [DEC-LLM-002](decisions/DEC-LLM-002-keys-flow-via-explicit-keys-object-no-env-reads.md) - explicit key flow.

## Connects to

- `chip-supply-chain-map` for graph-level supply-chain exposure.
- `LLM-evaluation-framework` for reusable eval patterns.
- `ai-supply-chain-copilot-prd` for the exception-workbench product wrapper.

## Stack

Python 3.11, Anthropic SDK, OpenAI SDK, Chroma local-only, Streamlit, uv, pytest. Default Anthropic model is `claude-sonnet-4-6`.

## What's intentionally absent

- Live EDGAR pull on every query.
- Multi-tenant deployment.
- A learned reranker by default.
- Real-time filing alerts.

## License

Apache-2.0. Content and eval datasets: CC BY 4.0 where derivative of SEC filings.
