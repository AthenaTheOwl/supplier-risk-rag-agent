# .agents/AGENTS.md

The single contract a coding agent (Claude, Codex, or other) reads
before acting on this repo. Specs name what we build. Decisions name
why. This file names how the agent behaves while building.

## Coding style

- Python 3.11. The repo uses `uv` as the package manager; install
  with `python -m uv sync --all-groups` from PowerShell or
  `uv sync --all-groups` where `uv` is on PATH.
- Ruff for lint, mypy for type checking, pytest for tests. The
  `pyproject.toml` pins the toolchain.
- Edit existing files. Use the `Edit` tool over `Write` when the
  file already exists; `Write` rewrites the whole file and risks
  losing context. Reserve `Write` for new files.
- The deployed Streamlit demo runs BYOK: keys live in
  `st.session_state`, never on disk. Local-env fallback is gated by
  `STREAMLIT_LOCAL=1`. Do not commit secrets, never read from
  `.env` in CI.
- Retrieval is deterministic by default. The hashing embedder and
  the BM25 + lexical-overlap hybrid ranker run in CI without API
  keys; the OpenAI embedder is opt-in for live experiments.
- Citations are verified spans. Every claim points at a chunk the
  retriever returned, and the span offsets match the cited text.
  The verifier in `src/retrieval/citations.py` is the single source
  of truth.

## Domain decisions

- Code ships under MIT. The Streamlit demo at
  `https://supplier-risk-rag-agent.streamlit.app` runs against the
  checked-in sample corpus by default; live EDGAR fetches need a
  custom SEC `User-Agent` and run only behind `--full-fetch`.
- The default Anthropic model is `claude-sonnet-4-6`. The
  `claude-sonnet-4-20250514` snapshot is deprecated (retirement
  planned 2026-06-15) and documented only as a migration note.
- The sample manifest CIK mappings were corrected against the SEC
  company tickers feed: TSM `0001046179`, KLA `0000319201`, Lam
  Research `0000707549`, ASML `0000937966`, Applied Materials
  `0000006951`. The values are load-bearing for the sample corpus.
- The eval suites (retrieval recall@5, citation faithfulness,
  abstention precision, refusal correctness) run on every push.
  CI must pass without vendor keys; live LLM calls are optional.
- Voice rules in `scripts/voice_lint.py` are not optional for
  governance copy under the documented globs. Banlist is hard-FAIL.

## Workflow conventions

- Push to main directly. The repo's CI runs the gates on push; a
  failed gate fails the check.
- Six python gates run on every push:
  `spec_check`, `voice_lint`, `validate_decisions`,
  `validate_roles`, `validate_tools`, `validate_policies`. Plus the
  existing `tests.yml` (pytest with 70% coverage gate) and
  `evals.yml` (`uv run python -m src.evals.runner --suite all`).
- Every shipped R-* requirement gets at least one DEC-* file
  before the commit reaches main. `spec_check` flags an orphan
  R-* and fails unless the requirement is listed in
  `decisions/.spec-check-allowlist.yaml` as deferred backfill, or
  carries the `R-CDCP-*` prefix (covered by `DEC-CDCP-001`).
- Dream-job outputs are human-gated. A dream candidate (memory
  update, generated test, skill patch, backlog item) carries
  `human_review_required: true` per the cross-repo schema default.
  No CI job auto-applies a dream candidate. The policy
  `.agents/policies/dream-candidates-require-human-approval.yaml`
  encodes the rule.
- Prompt or model changes hit a hard gate. Edits to
  `src/agent/prompts/` or to the default model id in
  `src/config.py` route through the
  `prompt-or-model-change.yaml` workflow and require a paired
  eval-result update under `reports/` or in the experiment folder
  before the change lands. The policy
  `.agents/policies/eval-suite-required-before-prompt-change.yaml`
  encodes the rule.
- A force-push, history rewrite, or rollback gets an entry in
  `ops/RESET_LEDGER.md` in the same push that performs the rewrite.
- A release gets an entry in `ops/RELEASE_LEDGER.md` with date,
  SHA, title, scope, and proof refs.

## Cross-repo links

- The CDCP charter at `../athena-site/ops/control-plane.md` names
  the six artifact types and the cross-repo contracts.
- The schemas at `../athena-site/ops/schemas/` are the source of
  truth for decision, role, tool, policy, skill, dream-output, and
  artifact shapes. This repo references them by URL and keeps cache
  copies under `ops/schemas-cache/` for offline CI.
- The portfolio manifest at
  `../athena-site/ops/portfolio-manifest.yml` lists every product
  repo and which gates each repo runs.

## Where to look

| If you want to | Read |
|---|---|
| understand the what | `specs/NNNN-*/requirements.md` |
| understand the why | `decisions/DEC-*.md` |
| understand what we learned last week | `dreams/YYYY-WNN/report.md` |
| run a supplier-risk query end-to-end | `.agents/skills/run-supplier-risk-query/SKILL.md` |
| audit a release | `ops/RELEASE_LEDGER.md` |
| audit a history rewrite | `ops/RESET_LEDGER.md` |
| add a new spec | `specs/README.md` plus the six-file pattern |
| add a new decision | `decisions/README.md` |
| register a new role or tool or policy | `.agents/CATALOG.md` |

## Failure modes the agent watches for

- A new R-* requirement without a DEC: `spec_check` fails. Fix by
  adding the DEC file in the same commit, or add the ID to the
  allowlist with a tracking note.
- A DEC file out of schema shape: `validate_decisions` fails. Fix
  the front-matter against `ops/schemas-cache/decision.schema.json`.
- A role, tool, or policy out of shape: the matching `validate_*`
  script fails. Fix against the cached schema.
- A voice-lint hit in governance copy: rewrite the line. Per-line
  allowlist via `voice_lint:allow <label>` ships only when the
  rule does not apply and the agent leaves a note.
- A skill graduation without an eval: the SKILL.md may ship with
  an empty `evals` array plus a TODO; promotion past version 0.1.0
  requires `passing_skill_eval` per the promotion_policy field.
- A prompt edit without a paired eval run: the
  `eval-suite-required-before-prompt-change` policy fires and the
  change is blocked.

## Lessons promoted from weekly dreams

This section holds memory entries promoted from the
`learning.dream-orchestrator` weekly retrospective. Each entry names
the lesson, the do/don't shape, and the candidate file the lesson
was promoted from.

### Experiment-and-revert as the right pattern when no lift · promoted from 2026-W21 dream

Changes with uncertain eval lift (a new reranker, a different
chunker, a swapped embedder) land under `experiments/NN-<slug>/`
with `config.yaml`, `baseline.json`, `variant.json`, and `notes.md`.
The four-suite gate decides; the experiment ships as a documented
negative result if the variant misses any threshold. Production code
is reverted in the same pass that records the result.

- do: scope the rule to changes with uncertain eval lift, land all
  four experiment files, run the same four-suite gate on baseline
  and variant, write up the rejection note in the same commit.
- don't: skip the experiment folder for "obvious wins," collapse
  the gate set to one suite, or leave the variant code on trunk
  after a negative result.

Promoted from `dreams/2026-W21/candidates/memory-001-experiment-and-revert-discipline.md`.

### Deterministic beats learned at small scale unless evals justify · promoted from 2026-W21 dream

A deterministic retriever beats a learned reranker at small corpus
scale unless evals justify the cost. The 20-case `retrieval_quality`
suite saturates recall@5 at 1.000 under the BM25 + hashing-cosine +
overlap hybrid; the `01-cross-encoder-rerank` experiment confirmed
the reranker had no headroom to claim and broke the
`citation_faithfulness` 0.95 gate by reordering chunks.

- do: keep retrieval deterministic at current corpus size, pair
  every "let's add a learned model" proposal with a saturation
  check against the recall@5 baseline, leave the reranker code
  opt-in for the `01b` follow-up on a larger corpus.
- don't: drop the deterministic path because a learned model "feels
  better," generalize the rule past the small-corpus qualifier, or
  re-run the experiment without recording the result under
  `experiments/`.

Promoted from `dreams/2026-W21/candidates/memory-002-deterministic-beats-learned-at-small-scale.md`.
