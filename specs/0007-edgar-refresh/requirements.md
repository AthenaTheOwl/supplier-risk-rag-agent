# requirements: EDGAR refresh

## Scope

Spec 0007 covers the bounded production-shape ingestion path for
refreshing a configured CIK list from EDGAR into generated corpus
artifacts. It does not cover investor portfolio rollups, alerting, or
live EDGAR pulls during Streamlit queries.

## Requirements

### R-ING-001: EDGAR refresh produces generated corpus artifacts without changing demo defaults

WHEN an operator runs the refresh CLI or the monthly refresh workflow,
THE SYSTEM SHALL fetch the configured CIK list from EDGAR, write chunks
in the existing corpus JSONL shape, and preserve the checked-in sample
corpus as the default demo and CI path.

Acceptance:
- `python -m src.ingest.run_ingest --refresh-edgar` reads
  `data/sample_manifest.json` by default and writes generated output
  under `data/generated/edgar_corpus/`.
- `--dry-run` fetches company submissions metadata, reports selected
  filings, and skips filing document downloads plus filesystem writes.
- The generated chunk file loads through `load_jsonl_corpus` without a
  separate parser.
- The refresh manifest records planned filings, written filings, chunk
  counts, source manifest, company metadata, and filing URLs.
- `.github/workflows/edgar-refresh.yml` runs monthly, requires a
  configured `SEC_USER_AGENT` repository variable, stays below the SEC
  request-rate limit, and uploads generated corpus files as artifacts
  instead of committing them.
- Tests for filing selection, corpus replacement, refresh manifest
  totals, and dry-run behavior do not require live network access.
