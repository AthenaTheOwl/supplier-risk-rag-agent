# specs

The repo uses a six-file spec pattern:

- `requirements.md`
- `design.md`
- `tasks.md`
- `acceptance.md`
- `research.md`
- `traceability.md`

Active specs:

- `0001-cognitive-delivery-control-plane/requirements.md`
- `0001-cognitive-delivery-control-plane/design.md`
- `0001-cognitive-delivery-control-plane/tasks.md`
- `0001-cognitive-delivery-control-plane/acceptance.md`
- `0001-cognitive-delivery-control-plane/research.md`
- `0001-cognitive-delivery-control-plane/traceability.md`

Allowed R-* prefixes (one per planned subsystem spec):

- `CDCP` — 0001 cognitive delivery control plane
- `ING` — ingestion (SEC client, chunker, manifest)
- `RET` — retrieval (BM25, embedder, hybrid ranker, reranker)
- `AGT` — agent (planner, answerer, refusal, citations)
- `EVL` — evals (recall, citation faithfulness, abstention, refusal)
- `UI` — Streamlit app surface
- `OPS` — ops, deployment, BYOK

Development loop:

1. Add or update requirement IDs.
2. Design interfaces and failure modes before code.
3. Add fixtures, evals, or golden cases before implementation.
4. Implement the narrowest traceable slice.
5. Run gates and record evidence.
6. Update traceability and status.
