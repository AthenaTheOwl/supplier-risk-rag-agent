# research: EDGAR refresh

- SEC EDGAR fair-access guidance asks automated clients to declare a
  User-Agent, download only what they need, and stay below the current
  request-rate limit of 10 requests/second:
  https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm.
- The existing repo already had `SECClient` with a custom User-Agent,
  sub-10 requests/second limiter, raw HTML cache, and targeted 403/429
  errors. The refresh work wires that client into corpus generation
  instead of adding a second network stack.
- The existing retrieval code already reads JSONL through
  `load_jsonl_corpus`, so generated EDGAR output should preserve the
  sample corpus record shape instead of creating a separate storage
  format.
- `data/generated/`, `data/raw/`, and `data/chroma/` are already
  gitignored. The refresh workflow can upload artifacts without
  changing the repo's checked-in data posture.
