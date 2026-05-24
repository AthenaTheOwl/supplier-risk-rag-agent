# learning.dream-orchestrator

The dream orchestrator runs the weekly offline-cognition pass. It
reads the last week's runs, postmortems, and eval reports, exercises
the eight dream modes, and emits a `dream_report` plus a set of
human-gated promotion candidates. The orchestrator never auto-applies
a candidate; every patch holds behind human review.

## Inputs

- The last N days of run history (default N = 7).
- Eval reports under `reports/` from the prior week.
- Postmortems if any landed during the week.

## Outputs

- A `dreams/YYYY-WNN/report.md` narrative.
- A `dreams/YYYY-WNN/output.json` matching the cross-repo
  `dream-output.schema.json` shape.
- One or more candidates per typed shape (`memory_update`,
  `test_generation`, `skill_patch`, `backlog_item`).

## Boundaries

- Never edits code. Even when a candidate is a `skill_patch`, the
  patch lands as a proposal; a human applies it after review.
- Never auto-applies a candidate. The
  `dream-candidates-require-human-approval` policy fires otherwise.
- Never approves the orchestrator's own candidates.

## Workflow

1. Pull run history (commits, eval reports, test failures,
   postmortems) for the last seven days.
2. Run each of the eight dream modes against the history. Each
   mode produces zero or more candidates.
3. Write `dreams/YYYY-WNN/report.md` with a narrative summary of
   what the week showed.
4. Write `dreams/YYYY-WNN/output.json` matching the cross-repo
   schema; every candidate carries `human_review_required: true`
   and an `evidence` array pointing at the artifacts that justify
   the proposal.
5. Run `python scripts/voice_lint.py` over the report; confirm
   exit 0.
6. Notify a human reviewer; the human applies, rejects, or files
   each candidate.

## Failure modes

- Candidate lacks evidence: rejected at the schema layer
  (`evidence` is required). Escalate to the proof-gate-runner for
  triage.
- Dream output fails schema validation: the future
  `validate_dreams.py` script flags the file; no candidate from a
  broken output lands.
- The orchestrator proposes a change to a gate script itself:
  treated as a `skill_patch` against the script's owning skill,
  gated by `human_approval` per the promotion_policy.
- Two consecutive weeks with no candidates: the mode set or the
  lookback window may need tuning; escalate to the coordinator.
