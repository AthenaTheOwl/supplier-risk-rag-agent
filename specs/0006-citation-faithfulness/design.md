# design: citation-faithfulness

## Shape

```mermaid
flowchart LR
  Q["query"] --> RANK["HybridRanker.search"]
  RANK --> CHUNKS["retrieved_chunks (top-k)"]
  CHUNKS --> ANS["agent.answerer composes answer + citations"]
  ANS --> CITES["Citation list"]
  CITES --> VER["verify_citations(citations, retrieved_chunks)"]
  VER -- "pass" --> RESP["agent response with verified citations"]
  VER -- "fail" --> ERR["CitationVerificationError"]
  ERR --> REFUSE["refusal or retry path"]
  RESP --> EVAL["citation_faithfulness eval (>= 0.95)"]
```

## Modules

### `src/retrieval/citations.py`

Defines `Citation`, `CitationVerificationError`,
`citation_from_chunk`, `_to_chunk`, and `verify_citations`. The
verifier is a pure function: it takes citations and chunks and
returns the verified citations or raises.

### `src/agent/answerer.py`

Calls `verify_citations` after composing an answer. A verification
failure means the answer cannot ship; the answerer treats it as a
refusal trigger.

### `src/agent/portfolio_rollup.py`

Parses pasted investor holdings, resolves known ticker/CIK values
against the loaded filing corpus, searches per holding and per risk
category, then verifies each cited span with `verify_citations`
before it enters a portfolio risk card. Cards without verified spans
are marked `insufficient_evidence`; a portfolio with no matched
holding or no supported card returns a refused rollup.

### `app.py`

Adds an `Investor rollup` tab beside the single-question path. The
tab uses the same cached ranker, does not call an LLM or paid service,
and exports the verified rollup as markdown or JSON.

### `eval_suites/citation_faithfulness.yaml` + `src/evals/runner.py`

The eval suite runs 15 queries and computes the fraction of
answered cases where every cited span verifies. The threshold is
0.95 (one failure out of 15 is the absolute floor; two failures
fail the gate).

## Failure modes

- The LLM produces a paraphrased citation that does not appear
  verbatim in any retrieved chunk: `verify_citations` raises;
  faithfulness drops; the eval gate catches it.
- The LLM cites a chunk id that was not in `retrieved_chunks`
  (hallucinated source): `verify_citations` raises with "points to
  a chunk that was not retrieved."
- The cited span offsets are out of bounds: `verify_citations`
  raises with "invalid offsets."
- The reranker reorders results and the answerer picks a span from
  a chunk no longer in the top-k: this was the failure mode the
  cross-encoder experiment hit (faithfulness 1.000 -> 0.933).
