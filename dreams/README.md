# dreams

A weekly offline-cognition pass that reads the last N days of runs,
postmortems, eval reports, and audit traces, then proposes promotion
candidates. Dreams name what we learned. Every candidate is
human-gated; no CI job auto-applies a dream output.

## Folder shape

```
dreams/
  README.md           (this file)
  YYYY-WNN/           (one folder per ISO week, lands when the dream job ships)
    report.md         (human-readable narrative)
    output.json       (structured output matching the cross-repo schema)
```

The first weekly folder lands in a later pass; the README reserves
the shape now.

## Published

| Week | Folder | Candidates | Modes run |
|---|---|---:|---|
| 2026-W21 | [`2026-W21/`](2026-W21/) | 5 | memory_consolidation, skill_extraction, golden_test_generation |

## The eight dream modes

The cross-repo `dream-output.schema.json` defines seven mode strings;
this README documents the eight cognitive modes the dream job
exercises. Mode strings in the schema map onto the cognitive modes
listed here.

1. **memory_consolidation** — read the last week of runs and roll
   up recurring observations into a `memory_update` candidate
   against a target memory file.

2. **failure_clustering** — read the last week of failures (test
   failures, gate failures, postmortems) and cluster by root cause.
   Each cluster becomes a `backlog_item` candidate. In this repo,
   common clusters are citation-faithfulness regressions, retrieval
   recall drops on new EDGAR sections, and refusal-suite false
   positives.

3. **adversarial_simulation** — generate inputs designed to break a
   known-fragile path (a regex, a parser, a prompt). Each
   reproducible breakage becomes a `test_generation` candidate.
   Adversarial inputs here target the citation span verifier, the
   refusal classifier, and the hybrid ranker.

4. **counterfactual** — replay one past run with a different prompt,
   model, or parameter. Compare outputs. Each material delta becomes
   a `backlog_item` or `skill_patch` candidate. This is the mode
   that produced the `01-cross-encoder-rerank` decision to revert.

5. **skill_extraction** — read the last N runs for patterns that
   recur enough to deserve a name. Each pattern becomes a
   `.agents/skills/<id>/SKILL.md` proposal, surfaced as a
   `skill_patch` candidate or a backlog item to create a new skill.

6. **golden_test_generation** — for spec requirements that lack
   eval coverage, generate a golden case. Each becomes a
   `test_generation` candidate tied to a spec_id.

7. **prompt_patch_generation** — for prompts that drift in quality
   over time, propose a patch. Each becomes a `skill_patch`
   candidate against the owning skill's instructions file. Patches
   to `src/agent/prompts/` are blocked by the
   `eval-suite-required-before-prompt-change` policy until a paired
   eval result lands.

8. **architecture_drift_detection** — read the spec ledger and the
   actual file tree, flag drift (a spec promises a folder that does
   not exist, or vice-versa). Each becomes a `backlog_item`
   candidate.

## Output shape

The structured `output.json` per week matches
`https://raw.githubusercontent.com/AthenaTheOwl/athena-site/main/ops/schemas/dream-output.schema.json`.

Required top-level fields:

- `id` — `dream-YYYY-WNN`
- `week` — ISO week label
- `generated_at` — ISO 8601 timestamp
- `generated_by` — agent or pipeline identifier
- `scope` — repos scanned, lookback days, sources
- `modes` — which modes ran
- `report_path` — pointer to the markdown narrative
- `candidates` — array of typed promotion candidates

## Promotion candidates

A candidate is one of four typed shapes:

1. `memory_update` — change a memory file.
2. `test_generation` — add a test case to CI.
3. `skill_patch` — change a skill's instructions, scripts, or evals.
4. `backlog_item` — track work that does not fit the other three.

Every candidate carries `evidence` (pointers to the artifacts that
justify the proposal) and `human_review_required` (defaults to true
per the schema). No CI job auto-applies a candidate. The agent
contract `.agents/AGENTS.md` repeats the rule, and the policy
`.agents/policies/dream-candidates-require-human-approval.yaml`
encodes it for the policy engine.

## Gates

When the first dream output lands, a future
`scripts/validate_dreams.py` walks `dreams/**/output.json` and
validates against the cross-repo schema. Until then, this README
reserves the contract.

## Cadence

Weekly Friday cron (lands when the dream orchestrator role ships its
trigger), manual `/dream-then-brief` slash command, or
operator-initiated pass. The orchestrator runs first; downstream
roles consume the candidates.

## Failure modes

- Dream candidates that propose changes to gate scripts themselves:
  treated as a `skill_patch` against the script's owning skill, gated
  by `human_approval` per the promotion_policy.
- Dream output that fails schema validation: the script flags the
  file and the dream run gets re-recorded; no candidate from a
  broken file lands.
- A candidate that lacks evidence: rejected at the schema layer
  (`evidence` is required).
