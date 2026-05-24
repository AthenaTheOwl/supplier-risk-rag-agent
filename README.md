# supplier-risk-rag-agent

Citation-faithful RAG over SEC EDGAR filings. Ask "which suppliers
disclosed export-control exposure?" and get an answer where every
claim points at a verifiable span in a real 10-K.

**Live demo:** [supplier-risk-rag-agent.streamlit.app](https://supplier-risk-rag-agent.streamlit.app)

The deployed app is BYOK. Paste your Anthropic key (and optionally
your OpenAI key) into the sidebar; the key lives in
`st.session_state` for the browser session only — never logged,
never stored, never persisted. CI evals run without any keys, so
you can read the eval evidence in the repo without trusting the
demo with anything.

## what makes this RAG different

- **Citation faithfulness is verified post-hoc.** Every cited span
  must appear verbatim in a retrieved chunk; the verifier in
  `src/retrieval/citations.py` raises if it does not, and the
  answerer treats that error as a refusal. See
  [DEC-CIT-001](decisions/DEC-CIT-001-verbatim-span-verification-post-generation.md).
- **Four eval suites gate every push.** `retrieval_quality`
  (recall@5 >= 0.70), `citation_faithfulness` (>= 0.95),
  `supplier_risk_questions` (answer-quality >= 0.80), and
  `refusal_cases` (refusal-precision >= 0.85). Prompt and model
  changes do not ship without the gate. See
  [DEC-EVL-001](decisions/DEC-EVL-001-four-suite-eval-gate-with-thresholds.md)
  and [docs/eval-discipline.md](docs/eval-discipline.md).
- **Deterministic hybrid ranker by default.** 60% normalized BM25 +
  25% cosine over local hashing embeddings + 15% term-overlap.
  Cross-encoder reranking stays opt-in: it was tried, it broke
  citation faithfulness on the sample corpus, and it was reverted.
  See [DEC-RET-001](decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md)
  and the postmortem at
  [experiments/01-cross-encoder-rerank](experiments/01-cross-encoder-rerank/).
- **Multi-provider LLM abstraction.** Anthropic default, OpenAI
  alternate via `LLM_PROVIDER`. Keys flow through an explicit `Keys`
  object; no environment reads from the demo. See
  [DEC-LLM-001](decisions/DEC-LLM-001-provider-abstraction-default-anthropic.md)
  and [DEC-LLM-002](decisions/DEC-LLM-002-keys-flow-via-explicit-keys-object-no-env-reads.md).

## who this is for

- Procurement-curious builders who want a worked example of
  supplier-risk Q&A grounded in primary documents.
- RAG practitioners studying citation faithfulness as a gate
  separate from retrieval recall.
- Eval-discipline folks who want a repo where prompt and model
  changes have to pass four named suites before merge.

## try it locally

```powershell
python -m uv sync --all-groups
Copy-Item .env.example .env       # set ANTHROPIC_API_KEY + OPENAI_API_KEY for local dev
$env:STREAMLIT_LOCAL = "1"
python -m uv run streamlit run app.py
```

For the hosted demo, paste keys directly in the sidebar. The trust
model is documented at [docs/trust_model.md](docs/trust_model.md).

## source corpus

20 pre-chunked excerpts under `data/sample_corpus/` from filings by
AAPL, AMAT, ASML, NVDA, MU, INTC, AVGO, KLAC, LRCX, and TSM (20-F).
Topics cover export controls, customer concentration, advanced
packaging, supplier capacity, third-party foundries, and long-lead
equipment risk. Full EDGAR fetch is gated by `--full-fetch` and
applies an SEC-compliant `User-Agent` plus a rate cap.

## governance

The repo runs under the Cognitive Delivery Control Plane (CDCP).
Six artifact types live in dedicated folders:

- [`specs/`](./specs/) — six-file spec ledgers; spec 0001 installs
  the CDCP scaffold itself, specs 0002-0006 cover retrieval, LLM,
  evals, deploy, and citation faithfulness.
- [`decisions/`](./decisions/) — twenty per-requirement DEC files
  validated against the cross-repo `decision.schema.json`.
- [`dreams/`](./dreams/) — weekly offline-cognition outputs;
  human-gated promotion candidates. The 2026-W21 pass promoted one
  eval candidate.
- [`.agents/`](./.agents/) — the contract a coding agent reads
  first; six role contracts, sixteen tools, six policies, two
  skills.
- [`ops/RELEASE_LEDGER.md`](./ops/RELEASE_LEDGER.md) — one entry
  per shipped commit, with proof refs.
- [`ops/RESET_LEDGER.md`](./ops/RESET_LEDGER.md) — one entry per
  force-push or rollback.

The cross-repo CDCP charter lives at
[`athena-site/ops/control-plane.md`](https://github.com/AthenaTheOwl/athena-site/blob/main/ops/control-plane.md).

## graduated skill: run-experiment-with-revert

The
[`run-experiment-with-revert`](./.agents/skills/run-experiment-with-revert/SKILL.md)
SKILL codifies the experiment-and-revert pattern that produced
[experiments/01-cross-encoder-rerank](./experiments/01-cross-encoder-rerank/).
Pre-register hypothesis and revert criteria, run baseline against
all four suites, apply the candidate change through an opt-in
surface, run variant, compare, and either keep + DEC or revert +
postmortem. The reverted cross-encoder is the canonical worked
example.

## develop

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

27 tests at 85% coverage. Four eval suites run against the
in-memory sample corpus with no vendor keys required.

## stack

Python 3.11 - Anthropic SDK - OpenAI SDK - Chroma (local-only) -
Streamlit - uv - pytest. Default Anthropic model is
`claude-sonnet-4-6`. See
[models overview](https://docs.anthropic.com/en/docs/about-claude/models/overview).

## what's intentionally not built

- Live EDGAR pull on every query. The default path reads the
  sample corpus; `--full-fetch` is opt-in.
- Multi-tenant deployment. The hosted demo is single-tenant BYOK.
- A learned reranker by default. See experiment 01 for why.
- Real-time alerting. The agent answers queries; it does not
  watch filings.

## license

Apache-2.0. Content and eval datasets: CC BY 4.0 where derivative
of SEC filings.
