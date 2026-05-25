# tasks: EDGAR refresh

- [x] Add a testable EDGAR refresh module with a client protocol seam.
- [x] Wire `run_ingest --refresh-edgar` and keep `--full-fetch` as an
  alias.
- [x] Write generated JSONL chunks in the same shape as
  `data/sample_corpus/chunks.jsonl`.
- [x] Write a refresh manifest with filing and chunk totals.
- [x] Add monthly GitHub Actions workflow with explicit SEC
  User-Agent configuration.
- [x] Add offline tests for filing selection, corpus replacement,
  manifest totals, and dry-run behavior.
- [x] Document CLI, dry-run behavior, generated artifact location, and
  workflow setup.
