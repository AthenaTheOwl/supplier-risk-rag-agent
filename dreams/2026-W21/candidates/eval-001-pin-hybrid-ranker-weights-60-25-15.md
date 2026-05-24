---
id: dream-2026-W21-eval-001
target_kind: test_generation
target: tests/test_ranker_weights.py
mode: golden_test_generation
human_review_required: true
status: promoted
promotion_date: 2026-05-24
evidence:
  - decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md
  - src/retrieval/ranker.py
  - tests/test_ranker.py
  - specs/0002-retrieval/requirements.md
---

## proposal

Add a regression test at `tests/test_ranker_weights.py` that pins
the 60/25/15 weighted-score formula and the 0.03 fallback factor
named in `DEC-RET-001`. The test:

1. Constructs a `HybridRanker` over a two-chunk fixture corpus
   where the first chunk shares all query tokens (high BM25, high
   overlap) and the second chunk shares zero query tokens.
2. Mocks the embedder so the cosine score is a fixed value the
   test controls (e.g., 0.5 for chunk-1, 0.8 for chunk-2).
3. Computes the expected combined score for chunk-1 as
   `0.60 * bm25_norm + 0.25 * 0.5 + 0.15 * overlap_ratio` and
   asserts the returned `SearchResult.score` matches within
   floating-point tolerance.
4. Asserts the chunk-2 score equals `0.03 * 0.8` (the zero-overlap
   fallback).
5. Asserts the weights themselves: that swapping any of the three
   coefficients in `HybridRanker.search` causes the test to fail.

The existing `tests/test_ranker.py` covers behavioral correctness
(the right chunk appears in the top-5); this test pins the
arithmetic so a future "let's tune the weights" PR cannot land
silently without updating both the test and `DEC-RET-001`.

## why it earns its keep

`DEC-RET-001` names the weights as load-bearing for retrieval
quality and citation faithfulness. A future PR that touches
`HybridRanker.search` could change the arithmetic without
breaking the recall@5 gate (which is saturated at 1.000 and so
has no headroom to surface a weight regression). The test makes
the weights an explicit contract; a change to either side flags
the diff at PR time.

## evidence

- `DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md` —
  names the 60/25/15 split and the 0.03 zero-overlap factor.
- `src/retrieval/ranker.py` lines around `combined = (0.60 *
  bm25_norm) + (0.25 * vector_score) + (0.15 * overlap_ratio)` —
  the arithmetic the test pins.
- `tests/test_ranker.py` — the behavioral coverage this test
  complements (it does not replace it).
- `specs/0002-retrieval/requirements.md` R-RET-001 — the
  requirement the decision resolves.

## promotion path

A human reviewer writes the new test file under `tests/`,
runs `python -m uv run pytest tests/test_ranker_weights.py -v`
to confirm it passes against the current ranker, then runs the
full suite (`python -m uv run pytest --cov=src
--cov-fail-under=70`) to confirm no regression. The test lands
in a single commit; coverage of `src/retrieval/ranker.py` ticks
up a point or two.

## risks if promoted blindly

- The mocked embedder couples the test to the `HybridRanker`
  constructor signature (`embedder=...`). A future refactor that
  changes the embedder injection path requires updating the
  test fixture. The risk is bounded (one test file) and the
  signal (a refactor changed retrieval scoring without updating
  the test) is the failure mode we want.
- Pinning the exact weights makes a deliberate weight change a
  two-file PR (the ranker plus the test). The DEC update
  required by such a change makes it a three-file PR, which is
  the right shape; this is a feature, not a bug.
