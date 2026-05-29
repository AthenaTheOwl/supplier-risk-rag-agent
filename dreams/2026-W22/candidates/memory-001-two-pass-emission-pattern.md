---
id: dream-2026-W22-memory-001
target_kind: memory_update
target: .agents/AGENTS.md
mode: memory_consolidation
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
    ref: scripts/replay_run.py
---

## proposal

Add a paragraph under `.agents/AGENTS.md` `## Lessons promoted
from weekly dreams` that names the two-pass emission pattern
as the right shape for any artifact whose recorded SHA must
pin the commit containing the artifact itself (not the
parent). Suggested text:

> Any emitter that records a `<sha>` pinning the commit that
> physically contains its output uses the two-pass pattern: emit
> writes a `PENDING` placeholder, the data commit lands, a
> follow-up `finalize_*` script rewrites the placeholder to the
> resolved SHA. Single-pass emit pins the parent of the data
> commit and is the off-by-one shape four agents caught
> independently during the v2 run-evidence rollout. Replay paths
> treat `PENDING` as "current HEAD is the implicit pin" so a
> freshly regenerated artifact stays verifiable without an
> intervening finalize step.

## why it earns its keep

The off-by-one was caught four times across the portfolio under
the Round-5 single-pass emit shape. Each catch was independent
because the pattern was not named anywhere a future agent would
read before writing a new emitter. The next time someone writes
a Run-record-shaped artifact (a different sample family, a new
emitter for a sibling subsystem, a tooling-output recorder),
they will re-derive the bug unless the pattern is anchored where
behavioral guidance lives.

This memory update closes that loop. It names the pattern, the
failure mode it prevents, and the PENDING-replay shape that
keeps the operator workflow short. The text references DEC-EVL-009
for the full rationale and points at `scripts/finalize_sandbox_ref.py`
as the reference implementation.

## evidence

- `DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration.md`
  names the four-agent-catch-pattern and the Option A vs Option
  B + Option C tradeoff.
- `scripts/finalize_sandbox_ref.py` is the reference implementation.
- `src/evals/run_evidence.py` carries the PENDING placeholder
  emission site.
- `scripts/replay_run.py` carries the PENDING-aware `_enforce_head`
  branch the proposed paragraph references.

## promotion path

A reviewer adds the paragraph to `.agents/AGENTS.md` under
`## Lessons promoted from weekly dreams`, runs
`python scripts/voice_lint.py`, confirms the lint stays clean,
and commits. The patch is one paragraph; the change surface
is two lines of context plus the paragraph body.

## risks if promoted blindly

- The pattern is specific to "recorded SHA pins the commit that
  physically contains the output". A generic "always two-pass
  emit" instruction would apply two-pass discipline to artifacts
  that do not need it (a debug log, a stats CSV, a perf trace).
  The proposal scopes the lesson to the recorded-SHA case.
- Codifying the pattern early risks pinning the script name
  (`finalize_sandbox_ref.py`) where a different emitter family
  would want a different script. The proposal references the
  current script as a reference implementation, not as the only
  acceptable shape; a sibling emitter ships its own
  `finalize_<artifact>.py`.
