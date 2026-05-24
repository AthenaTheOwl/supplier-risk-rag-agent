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
