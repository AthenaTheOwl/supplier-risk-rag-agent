---
id: dream-2026-W21-skill-001
kind: skill_patch
target: .agents/skills/run-experiment-with-revert/SKILL.md
mode: skill_extraction
human_review_required: true
status: promoted
promotion_date: 2026-05-24
evidence:
  - experiments/01-cross-encoder-rerank/notes.md
  - experiments/01-cross-encoder-rerank/config.yaml
  - experiments/01-cross-encoder-rerank/baseline.json
  - experiments/01-cross-encoder-rerank/variant.json
  - decisions/DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md
  - decisions/DEC-RET-004-opt-in-reranker-via-constructor-and-runner-flag.md
---

## proposal

Graduate the experiments-and-revert workflow as a new skill at
`.agents/skills/run-experiment-with-revert-on-no-lift/SKILL.md`.
The skill records the file-layout contract
(`config.yaml`, `baseline.json`, `variant.json`, `notes.md`), the
runner-flag contract (the variant runs through the existing
`--reranker`-style opt-in arguments on the eval runner, not a
forked script), and the decision-rule contract (revert if the
variant misses any threshold from the four-suite gate).

The skill body should pin:

- when to invoke (a change with uncertain eval lift on a
  retrieval or generation path);
- which scripts run (`src/evals/runner.py --suite all` with the
  variant flag, captured as JSON to `experiments/NN/variant.json`
  and a paired `baseline.json`);
- the promotion rule (`human_approval` until a second experiment
  graduates, then `passing_skill_eval` like
  `run-supplier-risk-query` v0.2+).

## why it earns its keep

The pattern has shipped once (`01-cross-encoder-rerank`) and the
follow-up section in its notes lists three more candidates (01b,
02, 03). If even two of those land, the skill saves the second
author from re-deriving the file layout. The skill also gives the
`learning.dream-orchestrator` a structured artifact to reference
in future `counterfactual` mode runs (replay one past run with a
different prompt, model, or parameter — the experiment skill
names the file layout the counterfactual produces).

## evidence

- `experiments/01-cross-encoder-rerank/notes.md` — the format the
  skill formalizes.
- `experiments/01-cross-encoder-rerank/config.yaml` — the
  pre-registered hypothesis section that becomes the skill
  template.
- `baseline.json` and `variant.json` — the JSON shape the eval
  runner already produces under `--json`.
- `DEC-RET-001` and `DEC-RET-004` — the decisions that named the
  pattern (DEC-RET-001) and kept the wiring opt-in (DEC-RET-004)
  so a re-run does not need re-implementation.

## promotion path

A human reviewer creates the skill folder, copies the file shape
from `run-supplier-risk-query/`, and writes the SKILL.md against
the cross-repo `skill.schema.json`. The first version ships at
v0.1.0 with `promotion_policy.requires: [human_approval]`. A
second experiment under `experiments/` graduates the skill to
v0.2.0 with `passing_skill_eval` in addition. The dream
orchestrator does not auto-create the file; the human applies the
patch.

## risks if promoted blindly

- The skill formalizes a pattern with one data point. The second
  experiment may need a different file layout (a `prompts/`
  subfolder, a `metrics.csv`, an `analysis.ipynb`); the skill
  should leave room for additions and avoid locking the four
  filenames as a rigid contract.
- Graduating the skill before the file layout proves itself
  across two experiments risks codifying a one-off shape.
  Mitigation: ship v0.1.0 with `human_approval`, withhold
  `passing_skill_eval` until the second experiment lands.
- The "revert on no lift" rule is correct for the four-suite
  gate as currently shaped, but a fifth suite (or a relaxed gate)
  could change the calculus. The skill should reference the
  gate set by file path, not by hardcoded threshold list, so a
  future gate change does not silently invalidate the skill.
