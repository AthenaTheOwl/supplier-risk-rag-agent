# Experiments

Scratch space for retrieval/agent variants the production pipeline doesn't ship by default.

## Pattern per experiment

```
experiments/
  NN-short-name/
    config.yaml      hyperparams + variant description
    baseline.json    eval metrics with the variant OFF
    variant.json     eval metrics with the variant ON
    notes.md         hypothesis, results, decision
```

Each experiment is a self-contained ablation: one variable changed, deltas measured against the same eval suites the production pipeline uses (`retrieval_quality`, `citation_faithfulness`, `supplier_risk_questions`, `refusal_cases`).

## Running an experiment

The eval runner accepts experiment-time flags:

```powershell
# Baseline (no reranker, deterministic)
python -m uv run python -m src.evals.runner --suite all --json experiments/NN-name/baseline.json

# Variant (reranker on, model name configurable)
python -m uv run python -m src.evals.runner --suite all --reranker MODEL_NAME --json experiments/NN-name/variant.json
```

`--json` writes config + per-suite metrics to a stable JSON shape that `notes.md` can diff against `baseline.json`.

## Decision rule

An experiment ships into the production pipeline when:

- Recall@5 improves and citation faithfulness does not regress, OR
- Citation faithfulness improves and Recall@5 does not regress significantly, AND
- The cost (model size, inference latency, dependency surface) is justified by the delta.

If the delta is small or mixed, the experiment stays here as a documented dead-end. That's a real result.

## Index

- [01-cross-encoder-rerank](./01-cross-encoder-rerank/) — adds a learned cross-encoder on top of the deterministic hybrid ranker.
