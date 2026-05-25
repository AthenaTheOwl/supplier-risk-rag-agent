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

## for your role

**Domain expert (procurement / supplier-risk analyst / 10-K reader).**
The sample corpus at `data/sample_corpus/chunks.jsonl` holds 20 real
SEC filing excerpts from 10 CIKs (AAPL, AMAT, ASML, NVDA, MU, INTC,
AVGO, KLAC, LRCX, TSM) covering export controls, customer
concentration, advanced packaging, supplier capacity, and long-lead
equipment. Every cited span must verify verbatim against one of those
chunks; the contract lives in
[DEC-CIT-001](decisions/DEC-CIT-001-verbatim-span-verification-post-generation.md)
and the verifier at `src/retrieval/citations.py`.

**Science / eval-discipline reader.** Four suites gate every push.
`retrieval_quality` recall@5 >= 0.70
([retrieval_quality.yaml](eval_suites/retrieval_quality.yaml)),
`citation_faithfulness` >= 0.95
([citation_faithfulness.yaml](eval_suites/citation_faithfulness.yaml)),
`supplier_risk_questions` answer-quality >= 0.80
([supplier_risk_questions.yaml](eval_suites/supplier_risk_questions.yaml)),
`refusal_cases` >= 0.85
([refusal_cases.yaml](eval_suites/refusal_cases.yaml)). The
methodology and the experiment-and-revert pattern live in
[docs/eval-discipline.md](docs/eval-discipline.md); the canonical
reverted experiment is
[experiments/01-cross-encoder-rerank](experiments/01-cross-encoder-rerank/).

**Curious visitor.** Open
[supplier-risk-rag-agent.streamlit.app](https://supplier-risk-rag-agent.streamlit.app),
paste your own Anthropic and OpenAI keys into the sidebar (they sit
in `st.session_state` for the browser session and nowhere else), type
a question, read a citation-verified answer. No keys are required to
read the eval reports under `reports/`.

**Engineer forking the pattern.** `src/retrieval/ranker.py` is the
deterministic hybrid ranker (60% normalized BM25 + 25% cosine + 15%
term-overlap). `src/retrieval/citations.py` is the post-hoc verbatim
verifier. Six governance gates run under `scripts/` and the four eval
suites under `src/evals/`. The coding-agent contract sits at
[.agents/AGENTS.md](.agents/AGENTS.md); the BYOK keys flow is
documented at
[DEC-LLM-002](decisions/DEC-LLM-002-keys-flow-via-explicit-keys-object-no-env-reads.md).

**Regulator / auditor.** Every claim points at a verbatim span; an
unverified span gets refused, not paraphrased — see
[DEC-CIT-001](decisions/DEC-CIT-001-verbatim-span-verification-post-generation.md).
Citation shape changes stay append-only via the V2 dual-type path in
[docs/citation-shape-evolution.md](docs/citation-shape-evolution.md),
formalized as
[DEC-CIT-002 amendment](decisions/DEC-CIT-002-amendment-reversibility-mitigation.md).
Refusal contract: `eval_suites/refusal_cases.yaml`. Audit log:
`ops/event-log/`. Release log:
[ops/RELEASE_LEDGER.md](ops/RELEASE_LEDGER.md).

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

## EDGAR refresh

The checked-in demo still reads `data/sample_corpus/` by default.
Live EDGAR refresh is an opt-in corpus-management job that writes
ignored generated artifacts under `data/generated/edgar_corpus/`.
It does not commit fetched filings or change Streamlit startup
behavior.

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

Set `SEC_USER_AGENT` to a descriptive application/contact string
before live refresh. SEC fair-access guidance asks automated clients
to declare a User-Agent and stay below 10 requests/second:
https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm.
The monthly GitHub Actions workflow `.github/workflows/edgar-refresh.yml`
runs on the first day of each month, requires the repository variable
`SEC_USER_AGENT`, writes generated corpus files to the ignored
`data/generated/` path, and uploads them as a workflow artifact.
No SEC API key is required.

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
  sample corpus; scheduled or CLI-driven refresh is opt-in.
- Multi-tenant deployment. The hosted demo is single-tenant BYOK.
- A learned reranker by default. See experiment 01 for why.
- Real-time alerting. The agent answers queries; it does not
  watch filings.

## license

Apache-2.0. Content and eval datasets: CC BY 4.0 where derivative
of SEC filings.
