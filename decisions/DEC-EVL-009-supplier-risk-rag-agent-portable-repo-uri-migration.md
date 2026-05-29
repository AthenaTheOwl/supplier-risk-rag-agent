---
id: DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-020
amends: DEC-EVL-008-eval-replay-command
date: 2026-05-29
status: approved
reversible: true
decision: |
  The eval-suite emitter SHALL produce portable repo:// and
  artifact:// URIs per the cross-repo grammar defined in
  athena-site DEC-CDCP-014. Concretely: `Run.sandbox_image_ref`
  uses `repo://supplier-risk-rag-agent@<sha>/`,
  `Run.inputs[].ref` uses
  `repo://supplier-risk-rag-agent@<sha>/<rel-path>`, and
  `Run.workspace_id` is the bare repo identity token
  `supplier-risk-rag-agent`. The validator at
  `scripts/validate_run_evidence.py` and the replay command at
  `scripts/replay_run.py` accept both URI shapes AND legacy
  local paths during the migration round.

  This DEC also fixes the systemic sandbox_image_ref off-by-one
  caught by every Round-5 agent across the portfolio. The
  emitter records a `PENDING` placeholder in place of the SHA;
  `scripts/finalize_sandbox_ref.py` rewrites the placeholder to
  the resolved SHA in a follow-up step. The chosen variant is
  Option A (two-pass emit) from the Round-6 spec: emit writes
  PENDING, post-commit finalize rewrites the SHA against
  `git rev-parse HEAD` once the data-bearing commit lands. The
  recorded SHA pins the commit that physically contains the
  sample data files. Replay's HEAD-strict pre-flight treats the
  PENDING sentinel as "current HEAD is the implicit pin" so an
  operator can verify a freshly regenerated sample without an
  intervening finalize step.

  `replay_run.py` parses the SHA out of the new URI grammar via
  the same regex the validator uses; the legacy split on the
  last `@` stays in place as a fallback for samples emitted
  before the migration.
alternatives:
  - label: Option B — post-commit emission with --sandbox-sha flag
    rejected_because: |
      Option B would commit the data files first, then call the
      emitter a second time with the just-resolved SHA passed via
      a flag, so the recorded SHA equals the parent of the
      finalization commit. The emitter is currently called from
      `src/evals/runner.py` as part of the per-suite loop; a
      post-commit re-emission would require a second pass through
      the runner or a parallel "rewrite-only" entrypoint. The
      two-pass variant (Option A) ships one new tiny script
      (`scripts/finalize_sandbox_ref.py`) instead of restructuring
      the runner's emission pipeline, which keeps the change
      surface small. Option B is the right answer once a richer
      regeneration pipeline lands (probably Round 8); for Round 6
      Option A is the smaller patch with the same recorded-SHA
      semantics.
  - label: Option C — single-pass with deferred post-edit
    rejected_because: |
      Option C reads the just-written Run record JSON, edits
      `sandbox_image_ref` to point at `git rev-parse HEAD` once
      everything is staged, then writes the file back in place.
      The recorded SHA still pins the parent of the staging
      commit, not the commit that contains the JSON — the
      original off-by-one. Option C is a stylistic re-shuffle of
      the broken single-pass shape; it does not move the recorded
      SHA forward by one commit. Rejected because it does not
      fix the bug the task names.
  - label: emit absolute paths plus a separate manifest for cross-repo refs
    rejected_because: |
      Keeping `sandbox_image_ref` as a Windows absolute path while
      threading a parallel manifest of portable refs would carry
      the producer's local layout into every Run record and force
      consumers to read two artifacts to resolve one ref. The
      cross-repo schema treats refs as opaque strings; threading
      a manifest sideways breaks the typed-ref contract the
      consumer side already extends in athena-site DEC-CDCP-014.
      Producing the URI in the same field every consumer reads
      keeps the resolver path consistent with the grammar the
      sibling consumer repo expects.
  - label: relax HEAD-strict to accept PENDING as "no pin"
    rejected_because: |
      Treating PENDING as "no pin at all" would let an operator
      replay a not-yet-finalized sample against any drifted HEAD
      and trip the same apples-to-oranges failure mode the Round-5
      HEAD-strict check exists to prevent. Treating PENDING as
      "current HEAD is the implicit pin" preserves the
      pin-to-a-commit discipline while letting a freshly
      regenerated sample replay without an extra finalize step.
      The strict equality branch fires as usual once finalize
      lands a real SHA.
rationale: |
  This DEC amends DEC-EVL-008. DEC-EVL-008 named the
  equivalence-replay contract; it did not name how a Run record
  pins a producing commit beyond a local `<abs-path>@<sha>` shape.
  Round 6 makes the pin portable.

  Two facts force the change. First, athena-site DEC-CDCP-014
  defined a cross-repo URI grammar so a consumer in another
  portfolio repo can resolve a reference without baking in the
  producer's local layout. The grammar is two scheme prefixes:
  `repo://<repo-name>@<sha>/<rel-path>` for file refs at a pinned
  commit, `artifact://<repo-name>/<artifact-id>` for logical
  artifact refs. Consumers MUST accept both URI forms plus legacy
  local paths; producers SHOULD emit URIs going forward. Round 6
  is the migration round across the portfolio's producer repos.

  Second, four Round-5 agents independently caught the
  sandbox_image_ref off-by-one: the emitter called
  `git rev-parse HEAD` at emit-time, which is the parent of the
  commit that LATER physically writes the sample to disk. The
  recorded SHA therefore pinned the wrong commit. Replay
  HEAD-strict was unsatisfiable on first-emit unless the
  operator manually rebased or re-emitted. The two-pass emission
  pattern (Option A) fixes the root cause: emit writes PENDING,
  the data commit lands, `finalize_sandbox_ref.py` rewrites the
  placeholder to the resolved SHA. The finalized record's SHA
  pins the commit that physically contains the sample data, not
  the commit's parent.

  The PENDING-aware replay path keeps the discipline workable.
  Without it, a freshly regenerated sample would require an
  intervening finalize step before replay could pass; with it,
  replay against PENDING auto-resolves to current HEAD and the
  same hash + gate-rollup comparison runs against the same code
  state. Once finalize lands a real SHA the HEAD-strict equality
  branch fires as before, naming the recorded SHA and the
  current HEAD in the divergence message.

  Reversibility: the change can be rolled back per-field. The
  URI emission can be toggled by reverting the four production
  sites in `src/evals/runner.py` + `src/evals/run_evidence.py`.
  The off-by-one fix can be reverted by deleting
  `scripts/finalize_sandbox_ref.py` and dropping the PENDING
  branch in `_enforce_head`. The validator and replay both keep
  accepting the legacy `<abs-path>@<sha>` shape during the
  migration so an old sample stays readable until it is
  regenerated.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: decision
    ref: decisions/DEC-EVL-008-eval-replay-command.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/athena-site/blob/main/decisions/DEC-CDCP-014-portable-repo-uri-grammar.md
  - kind: doc
    ref: src/evals/run_evidence.py
  - kind: doc
    ref: src/evals/runner.py
  - kind: doc
    ref: scripts/validate_run_evidence.py
  - kind: doc
    ref: scripts/replay_run.py
  - kind: doc
    ref: scripts/finalize_sandbox_ref.py
  - kind: doc
    ref: tests/test_run_evidence.py
  - kind: doc
    ref: tests/test_replay_run.py
  - kind: doc
    ref: ops/run-records/run-643dff8f3b9c.json
  - kind: doc
    ref: ops/event-ledger/run-643dff8f3b9c.jsonl
rollback: |
  Revert the four production sites in `src/evals/run_evidence.py`
  + `src/evals/runner.py` so the emitter returns to the legacy
  `<abs-path>@<sha>` shape on `sandbox_image_ref`,
  `inputs[].ref`, and `workspace_id`. Drop
  `scripts/finalize_sandbox_ref.py` and the PENDING branch in
  `scripts/replay_run.py`'s `_enforce_head`. Drop the
  `resolve_uri` helper in `scripts/validate_run_evidence.py`
  plus the matching unit tests. Regenerate the sample at the
  rollback commit so the recorded SHA returns to the local-path
  shape. Drop R-EVL-020..023 from
  `specs/0004-evals-and-thresholds/requirements.md` plus the
  matching traceability rows. Delete this DEC. The validator and
  replay both already accept the legacy form during this
  migration round, so no separate data migration is needed.
owner: control.coordinator
---

## decision

The eval-suite emitter produces portable repo:// and artifact://
URIs per athena-site DEC-CDCP-014. `Run.sandbox_image_ref`,
`Run.inputs[].ref`, and `Run.workspace_id` move off the
producer's local absolute path onto the cross-repo grammar. The
validator and replay command accept both URI shapes and the
legacy local path during the migration round.

The sandbox_image_ref off-by-one is fixed via two-pass emit
(Option A): emit writes a `PENDING` placeholder,
`scripts/finalize_sandbox_ref.py` rewrites the placeholder to
the resolved SHA once the data-bearing commit lands. Replay's
HEAD-strict pre-flight treats PENDING as "current HEAD is the
implicit pin" so a freshly regenerated sample stays verifiable
without an intervening finalize step.

## alternatives

- Option B (post-commit emission with --sandbox-sha flag):
  rejected because the runner emission path would need a second
  pass or a parallel rewrite-only entrypoint; the two-pass
  variant ships one tiny script instead.
- Option C (single-pass with deferred post-edit):
  rejected because it pins the parent of the staging commit,
  which is the original off-by-one.
- Absolute paths plus a parallel portable-ref manifest: rejected
  because threading two artifacts to resolve one ref breaks the
  typed-ref contract the consumer side already extends.
- PENDING means "no pin at all": rejected because it would let
  an operator replay against a drifted HEAD; treating PENDING as
  "current HEAD is the implicit pin" preserves the
  pin-to-a-commit discipline.

## rationale

This DEC amends DEC-EVL-008. The Round-5 HEAD-strict replay
command pinned a commit, but the recorded SHA was emitted
against the producer's local absolute path and pointed at the
parent of the data-bearing commit. Round 6 lands the portable
URI grammar from athena-site DEC-CDCP-014 plus the two-pass
emission pattern that fixes the off-by-one.

The two pieces compose. The portable URI grammar lets a sibling
consumer repo resolve refs against a shared portfolio root
without baking in the producer's layout. The two-pass emission
records the SHA of the commit that physically contains the
sample data, not the parent. Together they make the replay
claim defensible across portfolio repos: the recorded ref
resolves to a real file, and the recorded SHA pins the right
commit.

The PENDING-aware replay path keeps the operator workflow
short. Without it, every regenerate would need a finalize step
before replay could pass; with it, replay against a PENDING
sample auto-resolves to current HEAD and runs the same
equivalence check the strict equality path runs once finalize
lands.

## evidence

- `specs/0004-evals-and-thresholds/requirements.md` carries
  R-EVL-020..023 added under this DEC.
- `athena-site/decisions/DEC-CDCP-014-portable-repo-uri-grammar.md`
  defines the cross-repo URI grammar this DEC migrates the
  emitter onto.
- `src/evals/run_evidence.py` carries the URI helpers
  (`repo_uri`, `artifact_uri`, `repo_relative`,
  `PENDING_SHA_TOKEN`) and the updated
  `derive_sandbox_image_ref` two-pass entrypoint.
- `src/evals/runner.py` calls `repo_uri` on the input ref and
  sets `workspace_id` to the bare repo name.
- `scripts/finalize_sandbox_ref.py` is the post-commit
  finalize helper.
- `scripts/validate_run_evidence.py` and
  `scripts/replay_run.py` each carry a `resolve_uri` helper
  per the consumer-side rule from DEC-CDCP-014.
- `tests/test_run_evidence.py` extends the emitter tests with
  URI helpers + the resolve_uri positive/negative branches.
- `tests/test_replay_run.py` adds a positive test for the
  PENDING auto-resolve path.
- `ops/run-records/run-643dff8f3b9c.json` plus the matching
  ledger are the regenerated Round-6 sample emitted under the
  new URI grammar with the finalized SHA in place.

## rollback

Revert the four production sites in
`src/evals/run_evidence.py` + `src/evals/runner.py` so the
emitter returns to the legacy `<abs-path>@<sha>` shape on
`sandbox_image_ref`, `inputs[].ref`, and `workspace_id`. Drop
`scripts/finalize_sandbox_ref.py` and the PENDING branch in
`scripts/replay_run.py`'s `_enforce_head`. Drop the
`resolve_uri` helper in `scripts/validate_run_evidence.py`
plus the matching unit tests. Regenerate the sample so the
recorded SHA returns to the local-path shape. Drop R-EVL-020..023
from `requirements.md` plus the matching traceability rows.
Delete this DEC. No separate data migration is needed because
the validator and replay both already accept the legacy form
during this round.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-020` The eval-suite emitter produces `repo://` URIs in
  `Run.sandbox_image_ref` and `Run.inputs[].ref`, the bare repo
  identity token in `Run.workspace_id`, and an empty path after
  the SHA on the sandbox ref per the grammar.
- `R-EVL-021` `scripts/validate_run_evidence.py` ships a
  `resolve_uri` helper that maps a `repo://` URI to a local path
  under the portfolio root, returns None for `artifact://`
  URIs, and passes legacy local paths through unchanged.
- `R-EVL-022` `scripts/replay_run.py` parses the recorded SHA
  out of either the new URI shape or the legacy
  `<abs-path>@<sha>` shape, and treats the `PENDING` placeholder
  as "current HEAD is the implicit pin" for the HEAD-strict
  pre-flight.
- `R-EVL-023` The eval-suite emitter records a `PENDING`
  placeholder for the sandbox SHA at emit-time and
  `scripts/finalize_sandbox_ref.py` rewrites the placeholder to
  the SHA of the data-bearing commit so the recorded SHA pins
  the right commit instead of the parent.
