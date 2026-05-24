---
id: DEC-RET-004-opt-in-reranker-via-constructor-and-runner-flag
spec: specs/0002-retrieval/
requirement: R-RET-004
date: 2026-05-24
status: approved
reversible: true
decision: |
  Keep the cross-encoder reranker code in tree
  (`src/retrieval/reranker.py`) but wire it as opt-in only. The
  `HybridRanker.__init__` accepts a `reranker` argument and a
  `candidate_pool` size, both with safe defaults (`None` and 50)
  so the production path stays reranker-free. The eval runner
  exposes a `--reranker <model_name>` flag that constructs a
  `CrossEncoderReranker` for experiment runs; the default invocation
  does not pass the flag. Heavy dependencies
  (`sentence-transformers`, `torch`) live in the `experiments`
  uv group, not in the production dependency set.
alternatives:
  - label: delete the reranker code entirely
    rejected_because: |
      The reverted experiment (`experiments/01-cross-encoder-rerank`)
      documents a real failure mode the reranker hit on the small
      sample corpus (recall@5 already saturated; reranker reordered
      candidates in ways that broke verbatim-span verification, see
      DEC-RET-001). Deleting the wiring means re-implementing the
      integration to retest on a larger live-EDGAR corpus. The
      opt-in path keeps the integration ready without changing
      production behavior.
  - label: ship the reranker on by default with a feature flag
    rejected_because: |
      DEC-RET-001 measured a faithfulness regression (1.000 to
      0.933, below the 0.95 gate) when the reranker took over
      reordering on the current corpus. An on-by-default flag
      inverts the safe state; a single missed flag in a caller
      would re-introduce the regression. Default-off via
      constructor argument is the safer posture.
  - label: ship the reranker only behind an environment variable
    rejected_because: |
      Env-var-driven retrieval behavior makes the eval suite
      results depend on shell state, which violates the
      determinism property R-RET-002 holds. Constructor argument
      plus an explicit `--reranker` flag on the runner keeps the
      opt-in path explicit at the call site.
  - label: a separate `RerankingHybridRanker` subclass
    rejected_because: |
      Adds a parallel class hierarchy and a second code path
      callers have to know about. The single class plus a
      constructor argument keeps the surface area small; the
      reranker is composition, not inheritance.
rationale: |
  DEC-RET-001 named the production default: deterministic
  weighted-score hybrid, no reranker. This decision covers the
  shape of the opt-in mechanism. Keeping the reranker code in tree
  matters because the failure mode it hit (no recall headroom on a
  saturated 20-case corpus, verbatim-span verifier coupled to
  exact retrieval order) is corpus-dependent; the larger
  live-EDGAR corpus that `build_chroma_collection` supports
  (see DEC-RET-005) may show different behavior. The follow-up
  experiment (01b in the notes) re-runs the same setup against a
  larger corpus; the wiring is ready for that test without a
  code change.

  Heavy dependencies stay in the `experiments` uv group so the
  deployed Streamlit build and CI image do not pay the
  `sentence-transformers` plus `torch` cost. The reranker module
  imports `sentence_transformers` lazily inside the `_ensure_loaded`
  method, so importing `src.retrieval.reranker` itself has no
  network or memory cost; only constructing and calling the
  reranker pays.

  The eval runner's `--reranker` flag is the documented opt-in
  surface. The flag stays unset in CI, so the four-suite gate
  measures the deterministic baseline. Experiment runs pass the
  flag explicitly, which makes the opt-in choice auditable at the
  command line.
evidence:
  - kind: spec
    ref: specs/0002-retrieval/requirements.md (R-RET-004)
  - kind: doc
    ref: src/retrieval/reranker.py (CrossEncoderReranker + lazy
      `_ensure_loaded`)
  - kind: doc
    ref: src/retrieval/ranker.py (HybridRanker.__init__ reranker +
      candidate_pool arguments; search() pool path)
  - kind: doc
    ref: experiments/01-cross-encoder-rerank/notes.md (the reverted
      experiment that documented why opt-in)
  - kind: run
    ref: experiments/01-cross-encoder-rerank/variant.json
      (faithfulness regression that drove the default-off choice)
  - kind: decision
    ref: DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md
      (the production default this decision wraps)
  - kind: postmortem
    ref: experiments/01-cross-encoder-rerank/notes.md
      ("Follow-up candidates" 01b — re-run on larger corpus)
rollback: |
  Two reversible paths. To remove the opt-in surface entirely,
  delete `src/retrieval/reranker.py` and drop the `reranker` and
  `candidate_pool` arguments from `HybridRanker.__init__`. The
  experiment folder under `experiments/01-cross-encoder-rerank/`
  retains the historical record. To make the reranker the default
  instead, change the `reranker or None` line in
  `HybridRanker.__init__` to construct a `CrossEncoderReranker`
  unconditionally and re-run
  `python -m src.evals.runner --suite all`; the 0.95
  faithfulness gate flags the regression and blocks the switch
  until the experiment is rerun on a corpus where the regression
  no longer reproduces.
owner: science.proof-gate-runner
---

## decision

Keep the cross-encoder reranker code in tree but wire it as
opt-in only. `HybridRanker.__init__` accepts `reranker` and
`candidate_pool` arguments with safe defaults
(`reranker=None`, `candidate_pool=50`). The eval runner exposes a
`--reranker <model_name>` flag for experiment runs; the default
invocation does not pass the flag. Heavy dependencies live in the
`experiments` uv group.

## alternatives

- Delete the reranker code entirely — discards the integration
  that the follow-up 01b experiment needs and forces re-wiring.
- Ship reranker on by default with a feature flag — inverts the
  safe state given the documented faithfulness regression from
  experiment 01.
- Env-var-driven activation — couples retrieval behavior to shell
  state, breaking the determinism property R-RET-002 holds.
- Separate `RerankingHybridRanker` subclass — parallel hierarchy
  for what is a composition relationship.

## rationale

DEC-RET-001 names the production default; this decision covers
the shape of the opt-in mechanism. The failure mode the reranker
hit (no recall headroom on a saturated 20-case corpus, verbatim
verifier coupled to exact retrieval order) is corpus-dependent.
The wiring is ready for follow-up 01b against a larger live-EDGAR
corpus without a code change. The lazy import in
`_ensure_loaded` means the reranker module costs nothing at
import time; only construction and call pay the
`sentence-transformers` plus `torch` price. The runner flag makes
the opt-in choice auditable at the command line.

## evidence

- `src/retrieval/reranker.py` — the `CrossEncoderReranker` and
  the lazy `_ensure_loaded` path.
- `src/retrieval/ranker.py` — the `reranker` and
  `candidate_pool` constructor arguments and the search() pool
  path.
- `experiments/01-cross-encoder-rerank/notes.md` — the reverted
  experiment and the rationale for opt-in.
- `experiments/01-cross-encoder-rerank/variant.json` — the
  faithfulness regression that drove default-off.
- `DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md` — the
  production default this decision wraps.

## rollback

To remove the opt-in surface entirely, delete
`src/retrieval/reranker.py` and drop the `reranker` and
`candidate_pool` arguments from `HybridRanker.__init__`. To make
the reranker the default instead, change the constructor line to
build a `CrossEncoderReranker` unconditionally and re-run the
four-suite gate; the 0.95 faithfulness gate blocks the switch
until a future corpus no longer shows the regression.
