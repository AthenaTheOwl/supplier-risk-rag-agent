# research: evals-and-thresholds

Research checked 2026-05-24.

- The four-suite split (retrieval, citation faithfulness, end-to-end
  questions, refusal) predates CDCP. Each suite was added against a
  specific failure class observed during development: missing
  chunks, hallucinated citations, dropped required terms, and
  paraphrased refusals.
- Thresholds were picked against the sample corpus. Recall@5 sits
  at 1.000 today against the 20-case retrieval suite; the 0.70 floor
  leaves headroom for larger corpora to drop without breaking the
  gate. Faithfulness at 0.95 is the failure mode that reverted the
  cross-encoder experiment (faithfulness dropped 1.000 -> 0.933,
  below the threshold).
- Refusal precision at 0.85 leaves room for one or two borderline
  in-scope queries to slip through; tighter would over-refuse on
  edge cases that share vocabulary with supplier-risk filings.
- The runner emits `--json` for ablation runs so experiments can
  store baseline vs variant artifacts. The reverted cross-encoder
  experiment uses this path.

## Why now

- The eval gate is the single strongest discipline in the repo. It
  was named in a paragraph in `DECISIONS.md`; no per-requirement DEC
  existed. Spec 0004 backfills the IDs.
- The thresholds carry real weight: they reverted a learned reranker
  experiment without human review. That kind of automated reversion
  earns a structured DEC.

## Alternatives considered

- Single eval gate (one composite score): rejected. A composite
  score hides which failure mode regressed; the four-suite split
  makes the root cause obvious.
- No gate (review-only): rejected. The cross-encoder experiment
  would have shipped under review-only and broken citation
  faithfulness in production.
- Post-merge eval only (nightly): rejected. Bad prompts would reach
  main before the gate ran; the prompt-or-model-change policy in
  `.agents/policies/` requires a pre-merge eval pass.

## Open questions

- Does the faithfulness threshold need to rise to 1.00 (zero-defect)
  when the corpus grows? The current 0.95 leaves room for one
  edge-case failure in a 20-case suite; on a larger suite the
  threshold may want to tighten.
- Does a fifth suite (claim-level LLM-as-judge faithfulness) earn a
  spot? See `experiments/01-cross-encoder-rerank/notes.md` follow-up
  04. Open until the design lands.
