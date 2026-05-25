# traceability: EDGAR refresh

| Requirement | Design surface | Decision | Planned proof | Owner role |
|---|---|---|---|---|
| R-ING-001 | `src/ingest/edgar_refresh.py`, `src/ingest/run_ingest.py`, `.github/workflows/edgar-refresh.yml`, `README.md` | [`DEC-ING-001`](../../decisions/DEC-ING-001-edgar-refresh-generated-corpus-artifacts.md) | `tests/test_edgar_refresh.py`, `python scripts/spec_check.py`, `python -m src.evals.runner --suite all` | `owner_role: engineering.implementation` |
