# Experiment 01 — Cross-encoder reranker

**Date:** 2026-05-03
**Variant:** `cross-encoder/ms-marco-MiniLM-L-6-v2` reranking the top-50 hybrid candidates down to top-5.
**Decision:** **Do not ship.** Reverted. Variant fails the citation faithfulness gate.

## Hypothesis (pre-registered in `config.yaml`)

A learned cross-encoder on top of the deterministic hybrid retriever should:
- improve Recall@5 modestly by surfacing near-misses the weighted score buried;
- improve MRR more than Recall@5;
- be neutral or slightly worse on citation faithfulness;
- be neutral on refusal precision.

## Result

| Suite | Metric | Baseline | Variant | Δ | Gate |
|---|---|---:|---:|---:|---|
| retrieval_quality | recall_at_5 | 1.000 | 1.000 | 0.000 | ✅ pass |
| retrieval_quality | mrr | 1.000 | 1.000 | 0.000 | — |
| citation_faithfulness | faithfulness | 1.000 | 0.933 | **−0.067** | ❌ **fail** (0.95 threshold) |
| citation_faithfulness | answered_rate | 1.000 | 0.933 | −0.067 | — |
| supplier_risk_questions | answer_quality | 0.920 | 0.880 | −0.040 | ✅ pass |
| refusal_cases | refusal_precision | 1.000 | 1.000 | 0.000 | ✅ pass |

The variant failed `citation_faithfulness`. CI gates would block this from merging into the production ranker.

## Interpretation

Three things are true at once.

**The corpus is saturated for Recall@5.** Both baseline and variant return 1.000 across all 20 retrieval_quality cases. There was no retrieval headroom for the reranker to claim. MRR is also 1.000 in both — meaning the deterministic hybrid was already putting the right chunk at position 1 every time. On this small sample corpus, the reranker had no work to do that wasn't already done.

**The reranker reordered results in ways that broke the answerer's downstream verification.** The hybrid score is highly correlated with "this chunk contains the exact span the answerer will cite." The cross-encoder's relevance score is correlated with "this chunk is topically related to the query" — a different and weaker target. When the reranker promotes a topically-relevant-but-non-exact chunk above the hybrid's top hit, the answerer's deterministic span-extraction picks a citation that fails post-hoc verification (the cited span doesn't appear verbatim in the chunk metadata the eval expects). One case in 15 broke this way (1.000 → 0.933).

**The regression suite shows one extra failure (0.92 → 0.88, one case in 25).** Likely the same query mode as the faithfulness drop. The reranker substituted a plausible chunk for the "right" chunk; the regression eval's `expected accessions in citations` check fails.

This is exactly the failure mode ChatGPT's RAG thread named — *"reranker fails on numeric tables"* — generalized: rerankers can hurt when there's no recall headroom and when downstream consumers depend on retrieval order matching exact-text expectations.

## Decision

**Reverted.** The production pipeline keeps the deterministic hybrid ranker as default. The reranker code is kept in `src/retrieval/reranker.py` and is opt-in via `--reranker` on the eval runner, so future experiments on different corpora can re-test without re-implementing.

## Caveats

This result is contingent on the small sample corpus (~20 chunks). On a real EDGAR ingestion of hundreds or thousands of filing chunks, Recall@5 would no longer be saturated, and the reranker would have meaningful work to do that the hybrid score can't capture (semantic similarity beyond term overlap). The right way to re-run this experiment is:

1. Run live EDGAR ingestion (`run_ingest --full-fetch` against ~50 CIKs)
2. Author a new retrieval_quality eval suite with ground-truth accessions for the larger corpus
3. Re-run baseline vs variant
4. The reranker probably wins under those conditions

That's a future experiment (call it 01b), not this one.

## Reproduce

```powershell
# Dependencies for the experiments group (sentence-transformers + torch)
python -m uv sync --group experiments

# Baseline — deterministic hybrid only
python -m uv run python -m src.evals.runner --suite all `
  --json experiments/01-cross-encoder-rerank/baseline.json

# Variant — hybrid retrieves top-50, cross-encoder reranks to top-5
python -m uv run python -m src.evals.runner --suite all `
  --reranker cross-encoder/ms-marco-MiniLM-L-6-v2 `
  --json experiments/01-cross-encoder-rerank/variant.json
```

## What this experiment is also worth

Beyond the negative result on this corpus:

- It established the `experiments/` discipline. Future variants slot into this pattern with no ceremony.
- It validated the `--reranker` and `--json` flags through the eval runner. Subsequent experiments inherit them.
- It produced a real "what we tried, what we learned, why we didn't ship" artifact. That's a stronger portfolio signal than a contrived win, and it's the kind of writing hiring managers look for when they want to see eval discipline applied to AI work.

## Follow-up candidates (not committed)

- **01b** — same reranker, larger live-ingested corpus (post `--full-fetch`)
- **02** — multi-hop planner (replace the naive keyword expander in `src/agent/planner.py`)
- **03** — semantic chunking instead of fixed 180-word sliding windows
- **04** — claim-level faithfulness scoring (LLM-as-judge over citation spans, not just exact-match verification)
