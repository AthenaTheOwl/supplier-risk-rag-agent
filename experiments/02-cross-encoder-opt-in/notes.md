# Experiment 02 — Cross-encoder reranker shipped as opt-in

**Date:** 2026-05-24
**Variant:** `cross-encoder/ms-marco-MiniLM-L-6-v2` reranking the top-50 hybrid candidates down to top-k.
**Decision:** **Ship the wiring as opt-in.** Default behavior unchanged.

## What this experiment is for

Experiment 01 already measured the metric deltas on this sample corpus and
reverted the reranker. This run is a different question: does the opt-in
wiring (DEC-RET-004) work end-to-end now that there is a constructor
argument, a runner flag, a Streamlit checkbox, and a graceful-fallback
contract? The metric numbers reproduce the 01 result; the deliverable here
is the production wiring plus a user-facing switch.

## Setup

- `HybridRanker(reranker=CrossEncoderReranker(), candidate_pool=50)` — the
  composition contract.
- Runner: `python -m src.evals.runner --suite all --reranker cross-encoder/ms-marco-MiniLM-L-6-v2 --json experiments/02-cross-encoder-opt-in/metrics.json`.
- Baseline captured separately for a clean A/B: `baseline.json` (no
  reranker), `metrics.json` (with reranker).
- Streamlit: a sidebar checkbox routes the user query through the reranker
  when checked. Default is off.

## Results

| Suite | Metric | Baseline (no reranker) | With reranker | Δ | Gate |
|---|---|---:|---:|---:|---|
| retrieval_quality | recall_at_5 | 1.000 | 1.000 | 0.000 | pass / pass |
| retrieval_quality | mrr | 1.000 | 1.000 | 0.000 | — |
| citation_faithfulness | faithfulness | 1.000 | 0.933 | -0.067 | pass / **fail** (0.95 threshold) |
| citation_faithfulness | answered_rate | 1.000 | 0.933 | -0.067 | — |
| supplier_risk_questions | answer_quality | 0.920 | 0.880 | -0.040 | pass / pass |
| refusal_cases | refusal_precision | 1.000 | 1.000 | 0.000 | pass / pass |

The variant fails the citation-faithfulness gate. This reproduces experiment
01 and is exactly why the reranker stays opt-in rather than becoming the
default.

## Latency

Measured locally on CPU (Windows 10, Python 3.11):

- Baseline hybrid query (no reranker): ~0.4 ms per query.
- Reranker cold start (first call, includes model load): ~7.5 s.
- Reranker warm queries (steady state, top-50 pool reranked to top-5):
  ~83 ms per query.

The added per-query cost is order-of-magnitude ~80 ms on this corpus; on a
larger corpus with a 50-candidate pool that grows roughly linearly with
the cross-encoder's per-pair scoring cost (so the 150-400 ms range
DEC-RET-006 names is plausible on larger / longer chunks).

## Dependency footprint

- `sentence-transformers 5.4.1` — pulled via the `experiments` uv group.
- `torch 2.11.0+cpu` — transitive.
- Cross-encoder model weights (`ms-marco-MiniLM-L-6-v2`): ~80 MB download
  on first call, cached under the HF cache dir afterwards.

Neither dep enters the production dependency set. The Streamlit deploy and
the CI baseline image still install only `pyproject.toml`'s top-level
`dependencies`.

## Decision

Ship the wiring as opt-in. The default Streamlit checkbox is off; the
default eval-runner invocation does not pass `--reranker`; the
`HybridRanker` constructor still defaults `reranker=None`. The CI gate
keeps blocking the regression by measuring the baseline path only.

This delivers on DEC-RET-004's architectural promise (opt-in via
constructor and runner flag) and is captured in DEC-RET-006 as the
production-ship record.

## Caveats and follow-up

The faithfulness regression is corpus-dependent. On the 20-chunk sample
corpus, recall@5 is saturated at 1.000, so the reranker has no headroom
to claim and its reorderings only hurt the downstream verbatim-span
verifier. On a larger live-EDGAR corpus the saturation goes away and the
reranker may pay for itself — that is experiment 01b in the original
follow-up list, still uncommitted.

## Reproduce

```powershell
# Install experiments deps (sentence-transformers + torch)
python -m uv sync --group experiments

# Baseline — deterministic hybrid only
python -m uv run python -m src.evals.runner --suite all `
  --json experiments/02-cross-encoder-opt-in/baseline.json

# Variant — hybrid retrieves top-50, cross-encoder reranks to top-k
python -m uv run python -m src.evals.runner --suite all `
  --reranker cross-encoder/ms-marco-MiniLM-L-6-v2 `
  --json experiments/02-cross-encoder-opt-in/metrics.json
```
