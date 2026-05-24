---
id: dream-2026-W21-memory-002
target_kind: memory_update
target: .agents/AGENTS.md
mode: memory_consolidation
human_review_required: true
status: promoted
promotion_date: 2026-05-24
evidence:
  - experiments/01-cross-encoder-rerank/notes.md
  - experiments/01-cross-encoder-rerank/variant.json
  - decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md
  - decisions/DEC-RET-002-deterministic-hashing-embedder-default.md
  - eval_suites/retrieval_quality.yaml
---

## proposal

Add a one-line entry under `.agents/AGENTS.md` `## Domain
decisions` that records the small-scale preference for
deterministic retrieval over learned reranking. Suggested text:

> A deterministic retriever beats a learned reranker at small
> corpus scale unless evals justify the cost. The 20-case
> `retrieval_quality` suite saturates recall@5 at 1.000 under
> the BM25 + hashing-cosine + overlap hybrid; the
> `01-cross-encoder-rerank` experiment confirmed the reranker
> had no headroom to claim and broke the
> `citation_faithfulness` 0.95 gate by reordering chunks.

## why it earns its keep

This is the subtler version of memory-001 but earns its own slot
because it is a domain claim about the retrieval subsystem, not a
process claim about experiments. A future agent picking up
spec 0002 (retrieval) should read this before reaching for a
learned model. The recall headroom argument is the load-bearing
half: when the corpus grows past saturation, the claim flips, and
that flip is what the follow-up `01b` experiment is designed to
measure.

## evidence

- `experiments/01-cross-encoder-rerank/notes.md` — the saturated
  baseline section spells out the headroom argument.
- `experiments/01-cross-encoder-rerank/variant.json` — the
  measured faithfulness regression that drove the revert.
- `DEC-RET-001` — the production default that documents the
  rejection of cross-encoder rerank.
- `DEC-RET-002` — the deterministic hashing embedder default
  that paired with DEC-RET-001 to keep the path keyless.
- `eval_suites/retrieval_quality.yaml` — the 20-case suite that
  saturates at recall@5 = 1.000 under the hybrid.

## promotion path

A human reviewer applies the line to `.agents/AGENTS.md` under
`## Domain decisions`. The diff is one bullet point. Voice lint
runs against the modified file; the lint stays clean.

## risks if promoted blindly

- The claim is corpus-size-dependent. The line should be paired
  with the explicit "at small corpus scale" qualifier; without
  the qualifier the rule reads as a generic anti-reranker stance,
  which it is not.
- Promoting the rule before the `01b` follow-up experiment runs
  on a larger corpus risks pinning the claim before the
  scale-flip data lands. The line as written carries the
  qualifier, so the risk is bounded; reopen if the `01b`
  experiment results invert the conclusion.
