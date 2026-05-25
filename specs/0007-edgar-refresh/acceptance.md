# acceptance: EDGAR refresh

Acceptance for `R-ING-001` is proven by:

- `tests/test_edgar_refresh.py` covering target filing selection,
  generated corpus JSONL replacement, refresh manifest totals, and
  dry-run behavior without live network.
- `python -m src.ingest.run_ingest --refresh-edgar --dry-run` selecting
  filings from configured EDGAR submissions metadata without downloading
  filing documents.
- `.github/workflows/edgar-refresh.yml` scheduling monthly refresh and
  uploading generated artifacts instead of committing fetched corpus
  data.
- `README.md` documenting `SEC_USER_AGENT`, dry-run behavior, output
  paths, and the no-SEC-key assumption.

Out of scope:

- Investor portfolio rollup.
- Streamlit live EDGAR pulls per query.
- Committing generated EDGAR corpora to git.
