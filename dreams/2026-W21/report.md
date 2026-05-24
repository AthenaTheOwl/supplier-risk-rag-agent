# dream 2026-W21 — supplier-risk-rag-agent

First production run of the `learning.dream-orchestrator` role on
this repo. Lookback window: 2026-05-18 to 2026-05-24 (seven days).

## Modes run (v1 — three of eight)

- `memory_consolidation`
- `skill_extraction`
- `golden_test_generation` (the schema name for what this run
  calls "eval generation")

The other five modes do not run in v1. They will run when the
preconditions in the [skipped modes](#skipped-modes) section land.

## What the week showed

The week landed two architectural waves and reverted one
experiment.

**Wave 1: CDCP install (5274a4d).** Specs, decisions, dreams,
ops, .agents, and scripts/ all landed in a single pass. Six core
roles, six policies, sixteen tools, three state machines.
`spec_check`, `voice_lint`, `validate_decisions`,
`validate_roles`, `validate_tools`, `validate_policies` all
green at install.

**Wave 2: five architectural DECs plus five spec scaffolds
(bca8d80).** Backfill of `DEC-RET-001`, `DEC-LLM-001`,
`DEC-EVL-001`, `DEC-DEP-001`, `DEC-CIT-001` paired with specs
0002-0006. Sixteen R-* requirements deferred into the spec-check
allowlist for follow-up backfill passes.

**Wave 3: R-RET-002..005 backfill (bcf19c7, today).** Four DECs
landed against the retrieval subsystem; allowlist count dropped
from sixteen to twelve.

**The reverted experiment (58797c6).** The cross-encoder
reranker was tested against the four-suite gate and reverted.
Recall@5 was already saturated at 1.000 on the 20-case
retrieval_quality suite; the reranker had no headroom to claim
and reordered candidates in ways that broke verbatim-span
verification (faithfulness 1.000 to 0.933, below the 0.95 gate).
The experiment shipped to `experiments/01-cross-encoder-rerank/`
as a documented negative result.

## Candidates produced

Five candidates across the three modes:

| File | Mode | Kind |
|---|---|---|
| [`memory-001-experiment-and-revert-discipline.md`](candidates/memory-001-experiment-and-revert-discipline.md) | memory_consolidation | memory_update |
| [`memory-002-deterministic-beats-learned-at-small-scale.md`](candidates/memory-002-deterministic-beats-learned-at-small-scale.md) | memory_consolidation | memory_update |
| [`skill-001-run-experiment-with-revert-on-no-lift.md`](candidates/skill-001-run-experiment-with-revert-on-no-lift.md) | skill_extraction | skill_patch |
| [`eval-001-pin-hybrid-ranker-weights-60-25-15.md`](candidates/eval-001-pin-hybrid-ranker-weights-60-25-15.md) | golden_test_generation | test_generation |
| [`eval-002-decision-schema-offline-cache-fallback.md`](candidates/eval-002-decision-schema-offline-cache-fallback.md) | golden_test_generation | test_generation |

Every candidate carries `human_review_required: true` per
`dream-candidates-require-human-approval.yaml`. The orchestrator
does not promote any candidate; humans apply, reject, or file
each one.

## Skipped modes

Five modes do not run in v1. Reopen preconditions below.

- `failure_clustering` — no test failures, no gate failures, no
  postmortems landed during the lookback window. Reopen when at
  least one failure cluster appears in `ops/event-log/`.
- `adversarial_simulation` — the citation span verifier and the
  refusal classifier are the natural targets, but a productive
  adversarial pass needs a generation budget and a safe sandbox
  the orchestrator does not yet have wired. Reopen when the
  `adversarial-test-generation` skill graduates and the
  generation budget is named.
- `counterfactual` — counterfactual mode is what produced the
  `01-cross-encoder-rerank` revert decision. The next
  counterfactual candidate is the `01b` follow-up against a
  larger live-EDGAR corpus; that needs a full ingestion run
  (`run_ingest --full-fetch`) which is a developer-local step.
  Reopen when an `01b` baseline lands in `experiments/`.
- `prompt_patch_generation` — no prompt drift signal yet. The
  default Claude model is current (`claude-sonnet-4-6`) and the
  `eval-suite-required-before-prompt-change` policy blocks
  prompt edits without paired evals. Reopen when the prompt
  suite shows quality drift across consecutive runs.
- `architecture_drift_detection` — runs structurally across the
  spec ledger versus the file tree. After today's R-RET-002..005
  backfill the allowlist drops to twelve deferred IDs across
  specs 0003, 0004, 0005, 0006. The drift signal is already
  visible in `decisions/.spec-check-allowlist.yaml`; the next
  backfill commit will close more entries. Reopen when the
  allowlist still carries deferred IDs after the next two
  backfill passes (signal of stuck work, not work in progress).

## Evidence sources

- `git log --since="2026-05-18" --pretty='%h %s'` (commits during
  the lookback window).
- `experiments/01-cross-encoder-rerank/notes.md` plus
  `baseline.json` and `variant.json` (the reverted experiment).
- `decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md`
  through `DEC-RET-005-chroma-persistence-developer-local-only.md`
  (the architectural and backfill decisions).
- `decisions/.spec-check-allowlist.yaml` (the deferred-backfill
  signal).
- `eval_suites/retrieval_quality.yaml`,
  `eval_suites/citation_faithfulness.yaml`,
  `eval_suites/supplier_risk_questions.yaml`,
  `eval_suites/refusal_cases.yaml` (the four-suite gate).
- `reports/baseline_eval_report.html` (the most recent eval
  baseline).
- `scripts/validate_decisions.py` (the offline-cache fallback
  pattern that eval-002 pins).
- `src/retrieval/ranker.py` (the hybrid ranker weights eval-001
  pins).

## Next pass

The 2026-W22 dream pass should re-run the three v1 modes plus
turn on `architecture_drift_detection` as a fourth mode. The
allowlist signal earned its own reopen path this week and is
load-bearing for the spec_check gate; a structured drift report
gives reviewers a single artifact to scan.

## Promotion record

All five candidates were promoted on 2026-05-24 in a single human
review pass. The promotion landed under one commit per portfolio
convention; each candidate file now carries `status: promoted` and
`promotion_date: 2026-05-24` in its front-matter.

| Candidate | Mode | Landing artifact |
|---|---|---|
| memory-001-experiment-and-revert-discipline | memory_consolidation | `.agents/AGENTS.md` `## Lessons promoted from weekly dreams` |
| memory-002-deterministic-beats-learned-at-small-scale | memory_consolidation | `.agents/AGENTS.md` `## Lessons promoted from weekly dreams` |
| skill-001-run-experiment-with-revert-on-no-lift | skill_extraction | `.agents/skills/run-experiment-with-revert/SKILL.md` |
| eval-001-pin-hybrid-ranker-weights-60-25-15 | golden_test_generation | `tests/test_ranker_weights.py` |
| eval-002-decision-schema-offline-cache-fallback | golden_test_generation | `tests/test_validate_decisions_offline.py` (plus an env-var override on `scripts/validate_decisions.py`) |

The skill graduated at v0.1.0 with `passing_skill_eval` plus
`human_approval` in the promotion policy. The four cross-repo eval
suites are listed as the skill's eval set; the skill's
`passing_skill_eval` gate is therefore satisfied today by the same
four-suite gate the rest of the repo runs on push.

The skill ships as the second reusable skill in the portfolio after
ai-field-brief's `install-cdcp-governance`. The next candidate the
2026-W22 dream pass might surface is a cross-metric tradeoff skill
(see the `## Honest deferrals` section in the new SKILL.md).
