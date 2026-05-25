---
id: DEC-ING-001-edgar-refresh-generated-corpus-artifacts
spec: specs/0007-edgar-refresh/
requirement: R-ING-001
date: 2026-05-25
status: approved
reversible: true
decision: |
  Add a CLI and monthly GitHub Actions refresh path that fetches a
  configured CIK list from EDGAR into ignored generated corpus JSONL
  artifacts plus a refresh manifest. The checked-in sample corpus
  remains the default Streamlit and CI corpus, and investor portfolio
  rollup stays out of this scope.
alternatives:
  - label: live EDGAR pull on every Streamlit query
    rejected_because: |
      Query-time network access would add latency, make the demo depend
      on SEC availability, and blur the citation-faithfulness eval
      boundary. The current product promise is deterministic retrieval
      over a known corpus; refresh should happen as corpus management,
      not during answer generation.
  - label: commit the refreshed EDGAR corpus to git each month
    rejected_because: |
      Full filing-derived corpora can be large and noisy. Monthly
      corpus churn would make the repo harder to review and could bury
      code changes in generated data diffs. The existing gitignore
      pattern already reserves data/generated/ for local or workflow
      artifacts.
  - label: build investor rollup while adding refresh
    rejected_because: |
      Investor rollup requires portfolio input modeling, aggregation
      semantics, and separate evals. Combining it with ingestion would
      make it harder to prove that citation faithfulness and refusal
      behavior stayed intact.
rationale: |
  The app needed a production-shaped path beyond the checked-in sample
  corpus, but the safest bounded step is a corpus refresh job. Writing
  generated JSONL in the same shape as sample_corpus means retrieval can
  consume the output through the existing loader, while a manifest gives
  operators enough evidence to inspect what changed.

  Dry-run support provides a low-cost planning mode that touches only
  company submissions metadata, so the selected filings can be reviewed
  without downloading raw filing documents or rewriting corpus files.
  The monthly workflow requires an explicit SEC_USER_AGENT repository
  variable because SEC fair-access guidance asks automated clients to
  declare a User-Agent/contact and stay under the 10 requests/second
  limit.
evidence:
  - kind: spec
    ref: specs/0007-edgar-refresh/requirements.md (R-ING-001)
  - kind: doc
    ref: src/ingest/edgar_refresh.py
  - kind: doc
    ref: src/ingest/run_ingest.py
  - kind: doc
    ref: .github/workflows/edgar-refresh.yml
  - kind: doc
    ref: README.md (EDGAR refresh)
  - kind: doc
    ref: https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm
rollback: |
  Remove .github/workflows/edgar-refresh.yml, delete
  src/ingest/edgar_refresh.py, and revert the run_ingest.py CLI
  changes plus the EDGAR refresh docs/spec files. Generated output
  under data/generated/edgar_corpus/ is ignored and can be deleted
  locally without touching git. Re-run pytest and the four-suite eval
  gate to confirm the sample-corpus demo path still passes.
owner: engineering.implementation
---

## decision

Add a CLI and monthly GitHub Actions refresh path that fetches a
configured CIK list from EDGAR into ignored generated corpus JSONL
artifacts plus a refresh manifest. The checked-in sample corpus remains
the default Streamlit and CI corpus, and investor portfolio rollup stays
out of this scope.

## alternatives

- Live EDGAR pull on every Streamlit query - rejected because it would
  add latency, make the demo depend on SEC availability, and blur the
  deterministic eval boundary.
- Commit the refreshed EDGAR corpus to git each month - rejected because
  generated filing data can be large and noisy, and monthly churn would
  make code review harder.
- Build investor rollup while adding refresh - rejected because rollup
  needs its own input model, aggregation semantics, and eval proof.

## rationale

The app needed a production-shaped path beyond the checked-in sample
corpus, but the safest bounded step is a corpus refresh job. Writing
generated JSONL in the same shape as `sample_corpus` means retrieval can
consume the output through the existing loader, while a manifest gives
operators enough evidence to inspect what changed.

Dry-run support provides a low-cost planning mode that touches only
company submissions metadata. The monthly workflow requires an explicit
`SEC_USER_AGENT` repository variable because SEC fair-access guidance
asks automated clients to declare a User-Agent/contact and stay under
the 10 requests/second limit.

## evidence

- `src/ingest/edgar_refresh.py` - refresh seam, filing selection, JSONL
  writer, and refresh manifest.
- `src/ingest/run_ingest.py` - `--refresh-edgar`, `--dry-run`, and
  generated output CLI wiring.
- `.github/workflows/edgar-refresh.yml` - monthly workflow and artifact
  upload.
- `README.md` - operator-facing command and SEC User-Agent setup.
- `tests/test_edgar_refresh.py` - offline coverage for selection,
  generated corpus replacement, manifest totals, and dry-run behavior.

## rollback

Remove `.github/workflows/edgar-refresh.yml`, delete
`src/ingest/edgar_refresh.py`, and revert the `run_ingest.py` CLI
changes plus the EDGAR refresh docs/spec files. Generated output under
`data/generated/edgar_corpus/` is ignored and can be deleted locally
without touching git. Re-run pytest and the four-suite eval gate to
confirm the sample-corpus demo path still passes.
