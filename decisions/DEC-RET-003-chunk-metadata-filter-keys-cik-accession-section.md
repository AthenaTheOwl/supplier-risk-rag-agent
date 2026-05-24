---
id: DEC-RET-003-chunk-metadata-filter-keys-cik-accession-section
spec: specs/0002-retrieval/
requirement: R-RET-003
date: 2026-05-24
status: approved
reversible: true
decision: |
  Pin the per-chunk metadata schema to four named filter keys —
  `cik`, `accession`, `section`, and a free-form `metadata` dict —
  and pre-pass the filter dict in `HybridRanker._matches_filters`
  before BM25 and cosine scoring. Scalar values match by equality;
  list, tuple, and set values match by membership. The weighted
  score formula stays unchanged for the surviving chunks.
alternatives:
  - label: post-filter after ranking
    rejected_because: |
      Costs BM25 and cosine work on chunks the caller has already
      excluded. With a small sample corpus the difference is
      microseconds, but the larger live-EDGAR runs the helper at
      `build_chroma_collection` supports would feel the wasted
      work. Pre-filtering keeps the scoring loop tight.
  - label: free-form filter callable
    rejected_because: |
      A `Callable[[DocumentChunk], bool]` is more flexible but
      makes the caller responsible for naming the filter
      semantics. The four named keys (`cik`, `accession`,
      `section`, plus `metadata` lookups) are the actual filter
      dimensions the agent uses today, and they map directly to
      the SEC filing taxonomy the corpus is built on.
  - label: query-string filter syntax
    rejected_because: |
      A `cik:0001045810 AND section:risk_factors` mini-language is
      familiar from Lucene, but the parser plus the operator
      semantics is more surface area than the agent needs. A dict
      with three load-bearing keys and a free-form bag covers
      every observed filter case without a parser.
  - label: filter only on `metadata` and drop the named fields
    rejected_because: |
      `cik`, `accession`, and `section` are first-class fields on
      `DocumentChunk` because the SEC ingestion path produces them
      structurally. Pushing them into the `metadata` dict would
      lose the type information and force every caller to know
      where each field lives.
rationale: |
  The agent's planner and the deployed Streamlit app both want to
  narrow retrieval to a specific company (filter by `cik`),
  filing (filter by `accession`), or section (filter by
  `section`), and the experiment runner sometimes filters by a
  free-form metadata key. The four-key scheme covers every
  observed call site without ceremony.

  Pre-pass filtering matters when the candidate pool grows. The
  current sample corpus is small enough that pre- versus
  post-filter performance is indistinguishable, but
  `build_chroma_collection` (see DEC-RET-005) targets larger
  developer-local runs where the chunk count is in the thousands.
  Filtering before BM25 and cosine work keeps that path cheap.

  Membership matching on list/tuple/set values is the right
  default for the dominant filter pattern ("filings from this
  set of CIKs") without adding query-language surface area. The
  scalar-equality fallback handles the single-value case
  symmetrically.
evidence:
  - kind: spec
    ref: specs/0002-retrieval/requirements.md (R-RET-003)
  - kind: doc
    ref: src/retrieval/ranker.py (HybridRanker._matches_filters)
  - kind: doc
    ref: "src/retrieval/index.py (DocumentChunk: cik, accession,
      section, metadata fields)"
  - kind: doc
    ref: src/agent/planner.py (a caller that passes filter dicts)
  - kind: benchmark
    ref: eval_suites/retrieval_quality.yaml (the filter path runs
      under the recall@5 gate via the planner)
rollback: |
  Single-file revert. Remove the `filters` argument from
  `HybridRanker.search` and the `_matches_filters` helper. Callers
  that pass filter dicts (the planner and a handful of test
  cases) revert to post-filtering on the returned `SearchResult`
  list. Re-run `python -m src.evals.runner --suite all` after the
  change; the suites that filter by CIK still pass under
  post-filtering at the current corpus size.
owner: engineering.implementation
---

## decision

Pin the per-chunk metadata filter schema to four keys — `cik`,
`accession`, `section`, and a free-form `metadata` dict — and
pre-pass the filter dict in `HybridRanker._matches_filters`
before BM25 and cosine scoring. Scalar values match by equality;
list, tuple, and set values match by membership.

## alternatives

- Post-filter after ranking — wastes BM25 and cosine work on
  chunks the caller has already excluded; matters on the larger
  Chroma path.
- Free-form filter callable — flexible but pushes filter naming
  to the caller; the four named keys map to the SEC filing
  taxonomy the corpus is built on.
- Query-string mini-language — adds a parser and operator
  semantics for no benefit over a dict at current scope.
- Filter only on `metadata` — loses the first-class type info on
  `cik`, `accession`, and `section`.

## rationale

The planner and the Streamlit app filter by company, filing, or
section, and the experiment runner sometimes filters by a
free-form metadata key. The four-key scheme covers every
observed call site without ceremony. Pre-pass filtering matters
on the larger Chroma path enabled by DEC-RET-005, where the
candidate pool is in the thousands. Membership matching on
list/tuple/set covers the dominant "set of CIKs" pattern without
a parser.

## evidence

- `src/retrieval/ranker.py` — the `_matches_filters` helper.
- `src/retrieval/index.py` — the `DocumentChunk` fields and the
  `chroma_metadata` projection.
- `src/agent/planner.py` — a caller that builds filter dicts.
- `eval_suites/retrieval_quality.yaml` — the filter path runs
  under the recall@5 gate through the planner.

## rollback

Single-file revert. Remove the `filters` argument from
`HybridRanker.search` and the `_matches_filters` helper. Callers
that pass filter dicts revert to post-filtering on the returned
`SearchResult` list. Re-run the four-suite gate after the change.
