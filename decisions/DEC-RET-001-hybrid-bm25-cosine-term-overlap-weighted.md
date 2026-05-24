---
id: DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted
spec: specs/0002-retrieval/
requirement: R-RET-001
date: 2026-05-24
status: approved
reversible: true
decision: |
  Ship a deterministic weighted-score hybrid ranker as the production
  default: 60% normalized BM25 + 25% cosine similarity over local
  hashing embeddings + 15% query/chunk term-overlap ratio. Reject
  learned cross-encoder reranking as the default. Keep the reranker
  code in tree as an opt-in path for future experiments on larger
  corpora.
alternatives:
  - label: pure vector retrieval (cosine only over learned embeddings)
    rejected_because: |
      The sample corpus is full of short, jargon-heavy SEC excerpts
      where exact-term hits matter (CIK numbers, accession ids, named
      products). BM25 handles those better than cosine on its own,
      and a pure-vector path also forces a network round trip for
      embedding queries unless an in-process embedder is used.
  - label: pure BM25
    rejected_because: |
      BM25 alone misses paraphrase-style matches. Vector similarity
      (even at 25% weight) catches near-synonyms the term-frequency
      score skips. The overlap ratio adds a cheap third signal that
      sharpens the head of the ranking on multi-term queries.
  - label: cross-encoder rerank as production default
    rejected_because: |
      Tested in experiments/01-cross-encoder-rerank. Recall@5 was
      already saturated at 1.000 on the sample corpus; the reranker
      had no retrieval headroom to claim. Worse, the reranker
      reordered candidates in ways that promoted topically-related
      but non-exact chunks, breaking the downstream span verifier:
      citation faithfulness regressed 1.000 -> 0.933, below the 0.95
      gate. Latency also climbed with no eval payoff. The reranker
      stays in tree as opt-in; it is not the default.
  - label: learn the weights from data
    rejected_because: |
      The 60/25/15 split was tuned by hand against the 20-case
      retrieval_quality suite and has held recall@5 at 1.000 across
      six commits. Learned weights add a training step and a model
      artifact for no measurable gain at current corpus size. A
      future spec may revisit if the corpus grows past saturation.
rationale: |
  The repo runs CI evals on every push, so the ranker must be
  deterministic; the same query against the same corpus has to return
  the same ordering on every run. The weighted-score hybrid is pure
  Python over BM25, a hashing embedder, and a set-intersection count.
  No network, no model artifact, no nondeterminism.

  The downstream citation verifier (see DEC-CIT-001) checks that the
  cited span appears verbatim in a retrieved chunk. The hybrid score
  is correlated with "chunk contains the exact span the answerer
  will cite" because BM25 rewards term matches. A learned reranker
  optimizes for "topically related" which is a different and weaker
  target for this downstream consumer. Experiment 01 measured this
  directly: faithfulness dropped two-thirds of a point and answer
  quality dropped four points when the reranker took over reordering.

  Keeping the reranker code in tree (opt-in via `--reranker` on the
  eval runner and a constructor argument on `HybridRanker`) means the
  experiment can be re-run on a larger live-ingested corpus without
  re-implementing the integration. The default stays deterministic.
evidence:
  - kind: spec
    ref: specs/0002-retrieval/
  - kind: doc
    ref: src/retrieval/ranker.py
  - kind: doc
    ref: src/retrieval/embedder.py
  - kind: doc
    ref: src/retrieval/reranker.py
  - kind: doc
    ref: experiments/01-cross-encoder-rerank/notes.md
  - kind: run
    ref: experiments/01-cross-encoder-rerank/baseline.json
  - kind: run
    ref: experiments/01-cross-encoder-rerank/variant.json
  - kind: benchmark
    ref: eval_suites/retrieval_quality.yaml (recall@5 >= 0.7 gate)
  - kind: benchmark
    ref: eval_suites/citation_faithfulness.yaml (faithfulness >= 0.95 gate)
rollback: |
  Single-file revert. The ranker lives entirely in
  `src/retrieval/ranker.py`; switching weights or making the reranker
  the default is a constructor-argument change. To roll back to
  pure-vector or pure-BM25, edit the `combined` line in
  `HybridRanker.search`. To enable the reranker as default, pass
  `reranker=...` from the caller (today the only caller is the eval
  runner and the Streamlit app's `load_agent`). Re-run
  `uv run python -m src.evals.runner --suite all` after any change;
  the four-suite gate will catch regressions.
owner: engineering.implementation
---

## decision

Ship a deterministic weighted-score hybrid ranker as the production
default: 60% normalized BM25, 25% cosine similarity over local
hashing embeddings, 15% query/chunk term-overlap ratio. Reject
learned cross-encoder reranking as the default; keep the reranker
code in tree as an opt-in path.

## alternatives

- Pure vector retrieval — misses exact-term hits on jargon-heavy SEC
  excerpts and forces a network round trip without an in-process
  embedder.
- Pure BM25 — misses paraphrase matches the cosine signal catches at
  25% weight.
- Cross-encoder rerank as default — tested in experiment 01.
  Reordered candidates in ways that broke verbatim-span verification;
  faithfulness regressed 1.000 to 0.933, below the 0.95 gate.
- Learn the weights — adds a training step and a model artifact for
  no measurable gain at current corpus size.

## rationale

CI runs the eval suites on every push, so the ranker must be
deterministic. The weighted-score hybrid is pure Python with no
network and no nondeterminism. The hybrid score also correlates with
the downstream verifier's target (the cited span appears verbatim in
a retrieved chunk) better than a learned relevance score does. The
reverted experiment under `experiments/01-cross-encoder-rerank/`
measured both effects directly.

## evidence

- `src/retrieval/ranker.py` — the weighted-score implementation.
- `src/retrieval/embedder.py` — the deterministic hashing embedder.
- `src/retrieval/reranker.py` — the opt-in cross-encoder path.
- `experiments/01-cross-encoder-rerank/notes.md` — the reverted
  experiment.
- `experiments/01-cross-encoder-rerank/baseline.json` and
  `variant.json` — the measured deltas.
- `eval_suites/retrieval_quality.yaml` — the recall@5 ≥ 0.7 gate.
- `eval_suites/citation_faithfulness.yaml` — the faithfulness ≥ 0.95
  gate that caught the reranker regression.

## rollback

Single-file revert. The combination formula lives in
`HybridRanker.search`; changing weights or making the reranker the
default is contained to that file plus the caller that constructs
the ranker. Re-run the four-suite eval gate after any change.
