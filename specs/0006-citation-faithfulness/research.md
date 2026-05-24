# research: citation-faithfulness

Research checked 2026-05-24.

- Hallucinated citations are the most-cited failure mode in
  supplier-risk briefs. A paraphrased citation that looks plausible
  but does not appear verbatim in any retrieved chunk is the exact
  pattern reviewers catch first.
- The post-hoc verifier under `src/retrieval/citations.py` is the
  cheapest deterministic guardrail against that pattern. It runs
  after the LLM call and adds only a substring-search per citation,
  not another LLM call.
- The `citation_faithfulness` eval suite (≥ 0.95) sits on top of
  the verifier. The reverted cross-encoder experiment dropped
  faithfulness from 1.000 to 0.933 by reordering chunks so the
  answerer's chosen span no longer matched the retrieved chunk
  set; the gate caught it.
- The verifier handles both `DocumentChunk` and SearchResult-like
  inputs so the answerer does not need to unwrap retrieval results
  before verification.

## Why now

- The verifier predates CDCP and predates the eval suite that
  depends on it. It is one of the most load-bearing pieces of code
  in the repo. Spec 0006 backfills the R-* IDs so the verifier has
  structured DEC coverage.
- The reverted cross-encoder experiment is direct evidence the
  verifier's strictness is doing real work. Naming R-CIT-001
  explicitly makes that visible to future reviewers.

## Alternatives considered

- Trust the model (no verifier): rejected. Hallucinated citations
  are the dominant failure mode; trusting the model means shipping
  the failure mode.
- Train a citation classifier: rejected. The substring check is
  zero-training-cost and deterministic; a classifier adds
  maintenance burden without solving a failure the verifier misses.
- No verification (eval-time only): rejected. The eval would catch
  regressions but the deployed app would still emit unverified
  citations between releases. The verifier closes that gap at
  request time.
- LLM-as-judge faithfulness scoring: deferred. A future experiment
  (04 in `experiments/01-cross-encoder-rerank/notes.md`) may add a
  claim-level scorer on top of the substring verifier; the verifier
  stays as the first line.

## Open questions

- Does the verifier need a fuzzy-match mode (whitespace
  normalization, unicode normalization) for citations near chunk
  boundaries? Open. Today the match is strict; the answerer is
  responsible for picking spans that match.
- If latency becomes blocking on a future model, does the verifier
  earn a config flag to skip on opt-in? The rollback path in
  `DEC-CIT-001-*.md` names the pattern; the flag itself is deferred.
