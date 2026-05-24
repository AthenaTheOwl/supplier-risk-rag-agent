# specs

The repo uses a six-file spec pattern:

- `requirements.md`
- `design.md`
- `tasks.md`
- `acceptance.md`
- `research.md`
- `traceability.md`

Active specs:

- `0001-cognitive-delivery-control-plane/` — CDCP scaffold install
  (R-CDCP-001..010).
- `0002-retrieval/` — hybrid BM25 + vector + overlap ranker, Chroma
  persistence helper, opt-in reranker (R-RET-001..005).
- `0003-llm-provider/` — Anthropic-default provider abstraction with
  OpenAI as switchable alternate via `LLM_PROVIDER` (R-LLM-001..003).
- `0004-evals-and-thresholds/` — four named eval suites with
  pre-merge gate thresholds (R-EVL-001..005).
- `0005-deploy-and-secrets/` — BYOK Streamlit deploy, no committed
  keys, `STREAMLIT_LOCAL=1` local fallback (R-DEP-001..003).
- `0006-citation-faithfulness/` — post-hoc verbatim-span verifier
  feeding the citation_faithfulness ≥ 0.95 gate (R-CIT-001..003).

Each spec folder carries the same six files:
`requirements.md`, `design.md`, `tasks.md`, `acceptance.md`,
`research.md`, `traceability.md`.

Allowed R-* prefixes (one per planned subsystem spec):

- `CDCP` — 0001 cognitive delivery control plane
- `ING` — ingestion (SEC client, chunker, manifest)
- `RET` — 0002 retrieval (BM25, embedder, hybrid ranker, reranker)
- `AGT` — agent (planner, answerer, refusal, citations)
- `LLM` — 0003 LLM provider abstraction
- `EVL` — 0004 evals (recall, citation faithfulness, abstention, refusal)
- `DEP` — 0005 deploy, BYOK, and secrets handling
- `CIT` — 0006 citation verifier
- `UI` — Streamlit app surface
- `OPS` — ops, deployment, BYOK

Development loop:

1. Add or update requirement IDs.
2. Design interfaces and failure modes before code.
3. Add fixtures, evals, or golden cases before implementation.
4. Implement the narrowest traceable slice.
5. Run gates and record evidence.
6. Update traceability and status.
