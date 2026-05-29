---
id: dream-2026-W22-skill-001
target_kind: skill_patch
skill_id: regenerate-and-finalize-run-evidence
mode: skill_extraction
human_review_required: true
status: candidate
evidence:
  - kind: decision
    ref: decisions/DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration.md
  - kind: doc
    ref: scripts/finalize_sandbox_ref.py
  - kind: doc
    ref: src/evals/run_evidence.py
  - kind: doc
    ref: src/evals/runner.py
  - kind: doc
    ref: scripts/replay_run.py
  - kind: doc
    ref: ops/run-records/run-643dff8f3b9c.json
---

## proposal

Graduate the regenerate-and-finalize workflow as a new skill at
`.agents/skills/regenerate-and-finalize-run-evidence/SKILL.md`.
The skill records the canonical workflow for re-emitting the
sample under the v2 grammar and finalizing the sandbox SHA:

1. Run the eval runner against the canonical sample input set
   with the URI emitter active. Output lands at
   `ops/run-records/run-<id>.json` plus
   `ops/event-ledger/run-<id>.jsonl` with `sandbox_image_ref`
   carrying the PENDING placeholder.
2. Stage and commit the regenerated artifacts. The data-bearing
   commit lands.
3. Run `python scripts/finalize_sandbox_ref.py` against the
   just-committed Run record. The script rewrites the PENDING
   placeholder to the SHA of the data-bearing commit and stages
   the edit.
4. Amend or follow-up commit the finalize edit so the recorded
   SHA pins the right commit.
5. Run the full validator chain (`validate_run_evidence`,
   `replay_run.py`, `pytest tests/test_replay_determinism.py`)
   and confirm green.

The skill body pins:

- when to invoke (any time the canonical sample needs
  regeneration: schema bump, gate-set change, new event type);
- which scripts run, in which order, with which arguments;
- the failure modes (forgetting step 3 leaves a PENDING-shaped
  sample; running step 3 before step 2 finalizes against the
  parent of the data commit and reproduces the original
  off-by-one);
- the promotion rule (`human_approval` until a second emitter
  family adopts the same pattern, then `passing_skill_eval`).

## why it earns its keep

The workflow already ran four times during the W22 rollout
(Round 5 sample, Round 6 sample, Round 6 finalize, Round 6
regenerate-and-finalize). The pattern is load-bearing for any
future schema change or canonical-sample refresh; without a
named skill, the next operator re-derives the step order from
DEC-EVL-009 + the script docstrings.

The skill also gives the `learning.dream-orchestrator` a
structured artifact to reference in future `failure_clustering`
mode runs. If a future failure cluster around stale
`sandbox_image_ref` values surfaces, the orchestrator can point
at "this skill names the right step order" as the proposed fix.

## evidence

- `DEC-EVL-009` defines the two-pass emission semantics and
  names the four production sites where the URI emission landed.
- `scripts/finalize_sandbox_ref.py` is the canonical
  implementation; its docstring carries the operator-facing
  workflow that the SKILL.md formalizes.
- `src/evals/runner.py` is the runner entrypoint the skill
  workflow invokes in step 1.
- `scripts/replay_run.py` is the verification step the skill
  workflow invokes in step 5.
- `ops/run-records/run-643dff8f3b9c.json` is the canonical
  output of the workflow; the regenerated W22 sample carries
  the finalized SHA and the URI grammar.

## cost

Small. One new skill folder, one SKILL.md, one role-token
reference under `.agents/AGENTS.md` `## skills` index. The
workflow itself is already implemented; the skill names it.

## risk

The skill pins a five-step order. If a future schema change
makes step 3 unnecessary (an emitter that records the
data-bearing commit SHA in a single pass), the skill would
either need an update or would mislead the operator into
running an obsolete finalize call. Mitigation: the SKILL.md
references DEC-EVL-009 as the source of truth on emission
semantics; if DEC-EVL-011 ships a single-pass emitter, the
skill ships an amended version in the same commit.

## timeline

Next sprint (2026-W23 or W24). The workflow is stable, the
operator surface is small, and the skill folder shape is
already established by the W21 graduation of
`run-experiment-with-revert`.

## promotion path

The operator creates the skill folder, copies the file shape
from `.agents/skills/run-experiment-with-revert/`, writes
SKILL.md against the cross-repo `skill.schema.json`, adds a
row to the `.agents/AGENTS.md` skills index, runs
`python scripts/validate_skills.py`, and confirms green. The
first version ships at v0.1.0 with
`promotion_policy.requires: [human_approval]`. A second
emitter family adopting the same pattern graduates the skill
to v0.2.0 with `passing_skill_eval` against the chaos suite
(candidate backlog-002) added.

## risks if promoted blindly

- The skill formalizes a workflow that has one operator-facing
  data point (one emitter, one canonical sample). Codifying the
  step order risks pinning a shape that a future emitter family
  would want to extend. Ship v0.1.0 with `human_approval` and
  hold the `passing_skill_eval` gate until a second emitter
  uses the same shape.
- The skill scope overlaps with DEC-EVL-009 on
  semantics-vs-procedure. The DEC is the source of truth on the
  why; the skill is the source of truth on the how. The SKILL.md
  should reference the DEC in its `## sources` section.
