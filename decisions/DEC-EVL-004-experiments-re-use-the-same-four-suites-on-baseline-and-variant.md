---
id: DEC-EVL-004-experiments-re-use-the-same-four-suites-on-baseline-and-variant
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-004
date: 2026-05-24
status: approved
reversible: true
decision: |
  Run experiments under `experiments/NN-*/` against the same four
  eval suites that gate CI, on both baseline (trunk) and variant
  (the candidate change), and record per-suite deltas. The eval
  runner accepts a `--json` flag for machine-readable output and an
  opt-in variant flag (e.g., `--reranker`) for the candidate path.
  Each experiment folder carries `baseline.json`, `variant.json`,
  and a `notes.md` with the deltas and the kept-or-reverted decision.
alternatives:
  - label: experiments use a custom one-off eval set
    rejected_because: |
      One-off evals make experiments incomparable. A reranker
      experiment that uses a custom 5-case set cannot be compared
      against a chunker experiment that uses a different custom set.
      Re-using the four production suites means every experiment
      sits on the same rubric and every revert decision uses the
      same thresholds the CI gate applies.
  - label: only the variant runs evals; trust the last CI report for baseline
    rejected_because: |
      The CI baseline drifts as the corpus and code evolve. Running
      baseline + variant in the same experiment captures the exact
      delta from a single commit, with no risk of comparing against
      a stale baseline from a prior tree shape.
  - label: experiments run against a synthetic stress corpus only
    rejected_because: |
      Stress data would tell us how the variant behaves under load
      that does not match production. The four-suite gate uses the cases
      we care about (the supplier-risk sample corpus and the queries
      the agent answers in production). A future spec may add a
      stress corpus as a fifth suite; today the four production
      suites are the right comparison surface.
rationale: |
  The reverted cross-encoder experiment documents the pattern. The
  experiment landed `config.yaml`, `baseline.json`, `variant.json`,
  and `notes.md`. The baseline.json captured the four-suite metrics
  on trunk; the variant.json captured the same metrics with the
  reranker enabled. The notes.md compared the two and recorded the
  decision (revert: faithfulness dropped 1.000 to 0.933, below the
  0.95 gate). A reviewer who picks up the experiment six months
  later can reconstruct the decision without re-running anything.

  The four-suite reuse is what makes the dream orchestrator's
  `counterfactual` mode tractable. A replay of an experiment with a
  different prompt or a different model lands as a sibling folder
  under `experiments/`; the metric comparison is mechanical because
  every experiment uses the same suites. The
  `run-experiment-with-revert` skill that graduated in the 2026-W21
  dream pass formalizes this contract.

  The `--json` and variant flags ship in `src/evals/runner.py`
  today. The reranker flag is the canonical example; future
  experiments will add more variant flags (e.g., `--chunker bge`,
  `--embedder openai`) as the candidate changes land. Each new
  flag opt-in surface ships with its own DEC.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/
  - kind: doc
    ref: src/evals/runner.py (`--json` and variant flags)
  - kind: run
    ref: experiments/01-cross-encoder-rerank/baseline.json
  - kind: run
    ref: experiments/01-cross-encoder-rerank/variant.json
  - kind: doc
    ref: experiments/01-cross-encoder-rerank/notes.md
  - kind: doc
    ref: .agents/skills/run-experiment-with-revert/SKILL.md
rollback: |
  Drop the `--json` flag and the variant flags from
  `src/evals/runner.py`. Experiments would then have to capture
  metrics by parsing console output. The cost is bounded; the
  experiment folder shape stays the same. Re-add the flags as a
  follow-up commit if console parsing turns out to be fragile.
  The four-suite gate itself does not change under this rollback.
owner: science.proof-gate-runner
---

## decision

Run experiments under `experiments/NN-*/` against the same four eval
suites that gate CI, on both baseline (trunk) and variant (the
candidate change). Record per-suite deltas. The runner accepts
`--json` and an opt-in variant flag (e.g., `--reranker`). Each
experiment folder carries `baseline.json`, `variant.json`, and a
`notes.md` with the deltas and the kept-or-reverted decision.

## alternatives

- Custom one-off eval set per experiment — experiments become
  incomparable.
- Variant-only evals; trust last CI baseline — CI baseline drifts.
- Stress corpus only — measures load we do not serve.

## rationale

The reverted cross-encoder experiment documents the pattern. The
four-suite reuse makes the dream orchestrator's `counterfactual` mode
tractable: replays land as sibling folders with mechanical metric
comparisons. The `run-experiment-with-revert` skill that graduated
in 2026-W21 formalizes the contract.

## evidence

- `src/evals/runner.py` — the `--json` and variant flags.
- `experiments/01-cross-encoder-rerank/{baseline,variant}.json` and
  `notes.md` — the canonical reverted artifact.
- `.agents/skills/run-experiment-with-revert/SKILL.md` — the skill
  that codifies the workflow.

## rollback

Drop the `--json` flag and the variant flags from the runner.
Experiments would have to parse console output. The four-suite gate
itself does not change.
