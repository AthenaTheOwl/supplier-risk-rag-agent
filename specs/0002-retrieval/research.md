# research: retrieval

Research checked 2026-05-24.

- The hybrid weighted score (0.60 BM25 + 0.25 cosine + 0.15 overlap)
  predates the CDCP install. The weights were chosen against the
  sample corpus to keep recall@5 at 1.000 across the 20-case
  retrieval_quality eval and have stayed stable across six commits.
- The deterministic `HashingEmbedder` was picked over a learned
  embedder so CI evals can run without network access and without an
  OpenAI key. An OpenAI-backed embedder remains injectable via the
  `EmbedderLike` protocol.
- The optional cross-encoder reranker was tested in
  `experiments/01-cross-encoder-rerank/`. Recall@5 was already
  saturated; the reranker's reordering broke citation faithfulness
  (1.000 -> 0.933) by promoting topically-related but
  exact-span-mismatched chunks. The experiment was reverted; the
  reranker code stayed for future re-tests on larger corpora.
- Chroma persistence was added for developer-local full-corpus runs.
  The default in-memory ranker is still the deployed and CI path; the
  Chroma helper is a developer escape hatch, not a production
  pathway.

## Why now

- The retrieval choices have been load-bearing since the first
  release. The flat `DECISIONS.md` named the hybrid pattern in a
  paragraph; no per-requirement DEC existed. Spec 0002 backfills the
  R-* IDs so each retrieval choice can carry a DEC reference.
- The reranker experiment closing as a reverted result is a strong
  signal that the deterministic ranker is the right default. Naming
  R-RET-001 explicitly makes that default visible to future
  reviewers.

## Alternatives considered

- Pure vector retrieval: rejected. The sample corpus has many
  short, jargon-heavy chunks where BM25 outperforms cosine.
- Pure BM25: rejected. Vector similarity catches paraphrase-style
  matches the BM25 score misses on its own.
- Cross-encoder rerank as default: rejected per the reverted
  experiment. See `experiments/01-cross-encoder-rerank/notes.md`.

## Open questions

- When the corpus grows past saturation (post `--full-fetch` on real
  EDGAR), does the cross-encoder reranker become net-positive? The
  rerun is planned as experiment 01b; it is not part of this spec.
- Should the weighted-score weights move from constants to a config
  file? Today the weights are constants in `ranker.py`; a future
  spec may move them into a tuning config if a new corpus warrants
  different weights.
