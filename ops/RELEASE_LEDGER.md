# RELEASE_LEDGER

Every commit on main that represents shippable scope lands here with
date, SHA, title, scope, and proof refs. Backfilled entries cover
the six pre-CDCP commits.

## Format

Each entry has the shape:

```
## YYYY-MM-DD — <sha> <title>

- scope: <one or two sentences>
- proof:
  - <gate or test name> — <where the proof lives>
```

## Entries

## 2026-04-29 — 70f3253 Initial supplier risk RAG agent

- scope: full repo skeleton — `src/ingest/` (SEC client, chunker,
  manifest), `src/retrieval/` (hashing embedder, BM25, hybrid
  ranker, citation verifier), `src/agent/` (planner, answerer,
  refusal, tools, prompts), `src/evals/` (recall, citation
  faithfulness, abstention, refusal, runner), Streamlit `app.py`,
  pytest suite, sample EDGAR corpus, BYOK defaults.
- proof:
  - pytest — `tests/test_chunker.py`, `test_citations.py`,
    `test_config.py`, `test_manifest.py`, `test_ranker.py`,
    `test_refusal.py` pass
  - eval runner — `src/evals/runner.py --suite all` runs the four
    deterministic suites against the sample corpus

## 2026-04-29 — e4e8600 Use active Claude Sonnet model ID

- scope: default Anthropic model switched to `claude-sonnet-4-6`;
  legacy `claude-sonnet-4-20250514` snapshot documented as a
  migration note (retirement planned 2026-06-15).
- proof:
  - manual smoke — Anthropic SDK accepts the new model id
  - README — updated model paragraph with retirement link

## 2026-05-01 — 4aed25d voice-pass README: lowercase headers, tighten model paragraph, contractions

- scope: README editorial pass — lowercase section headers,
  tightened model copy, contractions throughout for plainer voice.
- proof:
  - manual read — README renders cleanly on GitHub
  - voice pass — no banned phrases in the rewritten copy

## 2026-05-02 — e1a21ad ci: enable dependabot for pip and github-actions

- scope: `.github/dependabot.yml` (implicit from commit message;
  configures weekly updates for pip and GitHub Actions ecosystems).
- proof:
  - dependabot — first scheduled run produces PRs against
    `pyproject.toml` and `.github/workflows/`

## 2026-05-02 — ce97330 document deployed Streamlit demo URL

- scope: README points at `https://supplier-risk-rag-agent.streamlit.app`
  as the live demo; BYOK pattern documented for the deployed
  surface.
- proof:
  - manual smoke — Streamlit Cloud renders the app; sidebar accepts
    BYOK Anthropic key
  - README — demo URL block reads clean

## 2026-05-03 — 58797c6 exp 01: cross-encoder reranker, reverted

- scope: `experiments/01-cross-encoder-rerank/` self-contained
  ablation — added cross-encoder reranker on top of the hybrid
  ranker, ran baseline and variant against the same eval suites,
  measured Faithfulness regression 1.000 → 0.933, decided to
  revert. `notes.md` records the decision; `src/retrieval/`
  unchanged in main.
- proof:
  - eval runner — `baseline.json` and `variant.json` checked in
  - pytest — green on main (the reranker code lives only in
    the experiment folder, not in `src/`)
  - voice pass — `notes.md` reads clean

## 2026-05-24 — <pending> spec 0001: install full CDCP (base + operating model)

- scope: installs the CDCP governance scaffold — `specs/0001-*/`
  ledger, `decisions/` directory with allowlist and bootstrap DEC,
  `dreams/README.md`, `.agents/AGENTS.md` plus six role contracts,
  tool registry, six policy files, three state machines, four
  workflow declarations, `ops/RELEASE_LEDGER.md` (this file),
  `ops/RESET_LEDGER.md`, `ops/event-log/`, schema cache, and six
  python gate scripts. The deployed Streamlit app is untouched.
- proof:
  - spec_check — one active spec, ten R-CDCP-* requirements,
    bootstrap exemption applied
  - voice_lint — governance copy reads clean
  - validate_decisions — one DEC validated
  - validate_roles — six roles validated
  - validate_tools — tool registry validated
  - validate_policies — six policies validated
  - pytest + evals — untouched; existing gates remain green

## 2026-10-18 — bbca7acd9cc8ec33fd491cb759fdf701d4637dad citation filing identity

- scope: Require a citation's CIK, accession, and section to match its retrieved
  chunk before accepting span evidence. Add separate negative cases for each
  identity field and document the evidence boundary.
- proof:
  - pytest — full fresh-default suite and three identity mismatch regressions
  - evals — all offline suites pass; prompts, models, and ranking are unchanged
  - GitHub CI — seven checks pass on the scoped source commit above in PR #12

## 2026-10-19 — 4b25326fe85c11078970a1bde23ae0a8569a168b bounded live evidence ordering

- scope: Replace unrestricted live answer prose with a complete permutation of
  verified citation labels. Render source spans locally and show distinct accepted,
  rejected, and failed live states. Resolve keys for the selected provider and keep
  dotenv loading behind the existing local-mode gate. Provider, model, and retrieval
  defaults are unchanged.
- proof:
  - pytest — 141 passed, 1 skipped; 88.73% coverage
  - tests/test_live_evidence_order.py — forged claims, invalid labels and output,
    missing evidence, valid complete ordering, safe provider failure, and refusal
  - tests/test_config.py — provider-aware fake keys and local dotenv boundary
  - tests/test_app_generation_status.py — visible accepted, rejected, and failed modes
  - reports/live-evidence-order-baseline.json and reports/live-evidence-order-variant.json
    — all five deterministic suite scores unchanged; synthetic provider checks only
  - native governance gates and changed-file Ruff — pass on the scoped source commit
- limits: The paired reports contain no live provider requests. OpenAI live API
  behavior is untested; its local credential resolver uses fake-key regressions.

## 2026-10-19 — 98aa0e160fea824658a638d2aa3f6df750790d97 refresh answer behavior across deployments

- scope: Cache the expensive retrieval ranker and construct the current answer
  agent for each run. Streamlit previously kept the pre-deployment agent object
  after the new UI loaded, causing missing generation metadata and retaining old
  answer behavior.
- proof:
  - tests/test_app_agent_cache.py — class-change regression fails before the repair;
    the repaired factory returns the current agent and reuses the same ranker
  - pytest — 142 passed, 1 skipped; 88.73% coverage
  - native governance gates and changed-file Ruff — pass
- limits: This regression simulates a hot deployment without a provider request.
  Hosted credentialed acceptance is recorded separately by the release operator.

## 2026-10-19 — bbca7acd9cc8ec33fd491cb759fdf701d4637dad citation filing identity: paired eval correction

- scope: The entry above landed without the paired eval report that the
  eval-suite-required-before-prompt-change policy requires for `src/retrieval/`.
  The report is now recorded retroactively. The entry and the shipped code are unchanged.
- proof:
  - reports/citation-filing-identity-baseline.json and
    reports/citation-filing-identity-variant.json — five offline suites at 30ee792
    and 1f66c83; runner metrics byte-identical at 30ee792, bbca7ac, 1f66c83 and b84572d

## 2026-10-19 — fefb66a001ded126e15e1fe052b46546c3f170b3 accept one fenced JSON live order

- scope: Strip one ```json or ``` fence that wraps the whole live reply before the
  existing citation_labels permutation checks. Prose around the fence, a second
  fence, multiple objects, and malformed JSON are still rejected.
- proof:
  - tests/test_live_evidence_order.py — fenced and padded replies accepted;
    prose-wrapped and malformed fenced replies rejected
  - reports/live-fence-cli-env-baseline.json and reports/live-fence-cli-env-variant.json
    — five offline suite scores unchanged; synthetic provider cases only
- limits: No live provider request was made.

## 2026-10-19 — 6146401c7e56844b5afca58be1edecb24f17d16a eval runner reads .env model settings

- scope: Add `get_cli_model_config`, which loads `.env` like `get_cli_keys`, and use
  it in `src/evals/runner.py`. `get_model_config` keeps the `STREAMLIT_LOCAL=1`
  gate for the Streamlit app.
- proof:
  - tests/test_config.py — Streamlit path ignores `.env` without the gate; the CLI
    helper reads it; the runner records the `.env` provider in its Run record
  - pytest — 162 passed; 89.09% coverage
