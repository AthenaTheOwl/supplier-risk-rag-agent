---
id: run-experiment-with-revert
version: 0.1.0
owner_guild: science
trigger:
  - candidate-improvement-with-uncertain-lift
  - reranker swap or chunker swap proposed against the production pipeline
  - parameter retune where the new value might regress an eval gate
instructions_file: .agents/skills/run-experiment-with-revert/SKILL.md
scripts: []
evals:
  - name: retrieval_quality
    path: eval_suites/retrieval_quality.yaml
    description: recall@5 against 20 supplier-risk cases, threshold 0.7
  - name: citation_faithfulness
    path: eval_suites/citation_faithfulness.yaml
    description: verbatim-span verification, threshold 0.95
  - name: supplier_risk_questions
    path: eval_suites/supplier_risk_questions.yaml
    description: end-to-end answer composition, threshold 0.8
  - name: refusal_cases
    path: eval_suites/refusal_cases.yaml
    description: abstention precision, threshold 0.85
promotion_policy:
  requires:
    - passing_skill_eval
    - human_approval
---

# skill: run-experiment-with-revert

The second reusable skill in the portfolio after `install-cdcp-governance`
in ai-field-brief. Codifies the experiments-and-revert workflow that
landed under `experiments/01-cross-encoder-rerank/`. The skill names
the file-layout contract, the runner-flag contract, and the
decision-rule contract that turn a "we tried it" change into a
documented gated artifact.

## Pre-conditions

The skill applies when all of the following hold:

- A working baseline ships on trunk. The four eval suites under
  `eval_suites/*.yaml` pass on `main` at their published thresholds.
- A candidate change (model swap, parameter retune, library
  substitution) might improve a metric, and the author is not yet
  sure whether the lift survives the four-suite gate.
- The cost of running the experiment plus the cost of reverting on
  a no-lift outcome is cheaper than the cost of a wrong commit on
  main. A change with a clear revert path (config flag, single-file
  edit, opt-in constructor argument) qualifies. A change that
  rewrites a public API or migrates data does not; that path runs
  through a full spec, not an experiment.

If the four-suite gate is red on trunk, fix the regression first.
An experiment against a broken baseline cannot earn a clean signal.

## Steps

1. **Scaffold the experiment folder.** Create
   `experiments/NN-<slug>/` where NN is the next integer in the
   directory listing and `<slug>` is a kebab-case name (e.g.,
   `02-bge-small-embedder`). Land four files:
   - `config.yaml` — pre-registered hypothesis section
     (`hypothesis`, `success_criteria`, `revert_criteria`), the
     model or parameter under test, and the exact eval-runner
     invocation for both baseline and variant.
   - `notes.md` — opens with the hypothesis paragraph; closes empty,
     to be filled with the deltas and the decision after the run.
   - `metrics.json` — empty (`{}`) initially; the runner writes the
     paired baseline/variant scores here on completion. The
     existing reverted experiment uses split `baseline.json` and
     `variant.json` files; either layout is acceptable as long as
     the file shape stays JSON-readable for the
     `architecture_drift_detection` dream mode.
2. **Run the baseline.** Invoke
   `uv run python -m src.evals.runner --suite all --json` against
   the current trunk. Record the four per-suite metrics in
   `metrics.json` (or `baseline.json`).
3. **Apply the candidate change.** Land the change in a branch or
   a worktree. Do not modify trunk. The change should be reachable
   through an existing opt-in surface (e.g., the `--reranker` flag
   on the eval runner, a constructor argument on a ranker, a
   `LLM_PROVIDER` env var). If a new opt-in surface is required,
   add it as part of the experiment and document the wiring in
   `notes.md`.
4. **Run the variant.** Invoke the same runner command with the
   candidate change reachable through the opt-in surface. Record
   the four per-suite metrics next to the baseline in
   `metrics.json` (or `variant.json`).
5. **Compare and decide.** Build a delta table in `notes.md`. The
   decision rule:
   - If every required gate (recall@5 ≥ 0.7, faithfulness ≥ 0.95,
     answer-quality ≥ 0.8, refusal-precision ≥ 0.85) passes on the
     variant AND at least one metric lifts above the baseline by a
     meaningful margin, keep the change and land a DEC recording
     the lift.
   - If any required gate fails on the variant, revert the change
     and write the rejection note. The opt-in surface stays in
     tree so the experiment can be re-run on a larger corpus
     without re-implementation.
   - If every gate passes but no metric lifts meaningfully, treat
     the change as a no-lift outcome: revert, document the result,
     keep the option open for a future re-run.
6. **Land the artifact.** The experiment folder ships as a single
   commit. The commit references the DEC if one landed, or names
   the four-suite delta if the variant was reverted. Either way,
   the artifact is the documented evidence the dream orchestrator
   reads on the next weekly pass.

## Verification

After the experiment lands, the trunk must satisfy:

- `uv run python -m src.evals.runner --suite all` passes on every
  suite at its published threshold.
- `experiments/NN/notes.md` (or the chosen layout) carries the
  metric comparison table AND the kept-or-reverted decision in
  plain text.
- If the variant was reverted, the diff between trunk before and
  trunk after is bounded to the experiment folder; production code
  is unchanged.
- If the variant was kept, a paired DEC under `decisions/DEC-*.md`
  records the decision, and the same commit updates the relevant
  spec's `traceability.md`.

## Honest deferrals

The skill assumes single-metric or single-suite comparisons. The
four-suite gate today is treated as a conjunction (every suite
must pass), so a variant that lifts recall@5 at the cost of
faithfulness reads as a failure under this skill. A real
cross-metric tradeoff (recall up, faithfulness down, answer-quality
flat) needs a separate skill that names the tradeoff rules and the
priority order. That skill is an open question: a candidate would
name the production priorities ("faithfulness over recall in the
supplier-risk product"), the dominance rules, and the decision
template for a Pareto-optimal variant. Until that skill graduates,
treat a cross-metric tradeoff as a halt-and-file-a-DEC outcome and
escalate to a human reviewer.

The skill also assumes the eval suites themselves are stable. If a
suite is being authored, edited, or rebalanced, run the experiment
against the new suite first to confirm the baseline reproduces;
only then run the variant.

## References

- `experiments/01-cross-encoder-rerank/` — the canonical reverted
  example. The cross-encoder ran against the four-suite gate,
  recall@5 saturated at 1.000 on the sample corpus, the reranker
  reordered candidates and broke the faithfulness gate (1.000 to
  0.933, below 0.95), and the variant was reverted in the same
  pass that recorded the result.
- `decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md`
  — the production decision derived from that run. The DEC names
  the four-suite gate as the deciding rubric and names the
  reverted reranker as the rejected alternative.
- `decisions/DEC-RET-004-opt-in-reranker-via-constructor-and-runner-flag.md`
  — the wiring decision that keeps the reranker code in tree as
  an opt-in surface, so the `01b` follow-up on a larger corpus
  does not need re-implementation.
- `eval_suites/retrieval_quality.yaml`,
  `eval_suites/citation_faithfulness.yaml`,
  `eval_suites/supplier_risk_questions.yaml`,
  `eval_suites/refusal_cases.yaml` — the four suites the skill
  runs on baseline and variant.
