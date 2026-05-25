---
id: DEC-CIT-004-deterministic-investor-rollup-over-verified-evidence
spec: specs/0006-citation-faithfulness/
requirement: R-CIT-004
date: 2026-05-25
status: approved
reversible: true
decision: |
  Investor portfolio rollups use a deterministic parser and category
  model over the loaded filing corpus. A risk card is supported only
  when its cited span came from a retrieved chunk and passed the same
  verbatim citation verifier used by the question-answer path; missing
  evidence is marked as insufficiency, and an unsupported portfolio is
  refused.
alternatives:
  - label: synthesize the rollup with an LLM
    rejected_because: |
      The feature needs a portfolio-level view, but it must keep the
      repo's cite-or-refuse boundary. Asking an LLM to infer category
      exposure would add claims that are harder to tie to a retrieved
      span, then push more work onto the verifier after the risky step.
  - label: import live brokerage or portfolio data
    rejected_because: |
      Live account import would add auth, privacy handling, and vendor
      setup outside the factory slice. The MVP only needs pasted
      holdings and the checked-in SEC corpus.
  - label: scan corpus text directly by keyword
    rejected_because: |
      Direct scanning would bypass the ranker output shape the verifier
      already accepts. Keeping the rollup on `HybridRanker.search`
      means every cited card can prove that its span came from retrieved
      evidence, not from an unrelated corpus walk.
rationale: |
  The rollup is a grouping layer, not a new source of truth. It parses
  ticker/CIK rows, resolves holdings against the loaded corpus, runs
  deterministic per-CIK retrieval for the five portfolio risk groups,
  and verifies each cited span before adding it to a card. The model
  can therefore aggregate exposure weights while preserving the
  existing citation contract.

  Missing evidence is a first-class output. Unknown holdings stay in
  the rollup as insufficient evidence, category cards without verified
  spans carry `status="insufficient_evidence"`, and a portfolio with
  no matched holding or no supported card refuses. That behavior keeps
  the investor view honest on the small sample corpus.
evidence:
  - kind: spec
    ref: specs/0006-citation-faithfulness/
  - kind: decision
    ref: decisions/DEC-CIT-001-verbatim-span-verification-post-generation.md
  - kind: decision
    ref: decisions/DEC-CIT-003-verifier-accepts-search-result-and-document-chunk-shapes.md
  - kind: doc
    ref: src/agent/portfolio_rollup.py
  - kind: doc
    ref: app.py
  - kind: doc
    ref: tests/test_portfolio_rollup.py
rollback: |
  Remove `src/agent/portfolio_rollup.py`, remove the `Investor rollup`
  tab and imports from `app.py`, delete `tests/test_portfolio_rollup.py`,
  and remove R-CIT-004 from the citation-faithfulness spec and
  traceability table. Re-run `python -m uv run pytest --cov=src
  --cov-fail-under=70`, `python -m uv run python -m src.evals.runner
  --suite all`, `python scripts/spec_check.py`, and
  `python scripts/validate_decisions.py` after rollback.
owner: engineering.implementation
---

## decision

Investor portfolio rollups use a deterministic parser and category
model over the loaded filing corpus. A risk card is supported only
when its cited span came from a retrieved chunk and passed the
verbatim citation verifier; missing evidence is marked as
insufficiency, and an unsupported portfolio is refused.

## alternatives

- LLM synthesis - adds claims before the verifier boundary.
- Live brokerage import - adds auth, privacy handling, and vendor
  setup outside the MVP.
- Direct keyword scan - bypasses the ranker output shape used by the
  citation verifier.

## rationale

The rollup is a grouping layer, not a new source of truth. It parses
ticker/CIK rows, resolves holdings against the loaded corpus, runs
per-CIK retrieval for the five portfolio risk groups, and verifies
each cited span before adding it to a card. Unknown holdings,
unsupported categories, and fully unsupported portfolios produce
insufficiency or refusal states instead of uncited prose.

## evidence

- `src/agent/portfolio_rollup.py` - parser, resolver, category model,
  and citation-gated card builder.
- `app.py` - `Investor rollup` tab and markdown/JSON export.
- `tests/test_portfolio_rollup.py` - parser, verified-card, and
  refused-no-match cases.
- `DEC-CIT-001` and `DEC-CIT-003` - existing verifier boundary.

## rollback

Remove the rollup module, Streamlit tab, tests, requirement, and
traceability row. Re-run the pytest, eval, spec, and decision gates.
