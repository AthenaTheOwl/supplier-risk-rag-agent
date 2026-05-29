---
id: dream-2026-W22-backlog-001
target_kind: backlog_item
mode: architecture_drift_detection
human_review_required: true
status: candidate
evidence:
  - kind: decision
    ref: decisions/DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration.md
  - kind: doc
    ref: scripts/validate_run_evidence.py
  - kind: doc
    ref: scripts/replay_run.py
  - kind: doc
    ref: src/evals/run_evidence.py
  - kind: doc
    ref: ops/run-records/run-643dff8f3b9c.json
---

## title

Retire legacy `<abs-path>@<sha>` acceptance once all canonical samples are regenerated under `repo://` URIs

## rationale

DEC-EVL-009 shipped the portable `repo://` URI grammar and kept
the legacy `<abs-path>@<sha>` shape readable as a migration-round
tolerance. The tolerance lives in three sites: the `resolve_uri`
helper in `scripts/validate_run_evidence.py`, the SHA extractor
in `scripts/replay_run.py`, and the implicit fallback path in
`src/evals/run_evidence.py`. The canonical sample
`run-643dff8f3b9c` is already regenerated under the new grammar.
The W22 rollout did not surface any old sample that still ships
the legacy shape.

The legacy branch is now a scaffold that widens the validator
surface without buying coverage. A stale sample under the old
shape would slip past the schema gate while failing the
cross-repo packet-gen step downstream (the sibling consumer's
resolver only accepts URIs). Deleting the legacy branch
collapses the validator surface and forces every producer to
re-emit under the URI grammar before its sample passes CI.

The proposed backlog item:

1. Audit `ops/run-records/` and `ops/event-ledger/` for any
   record still carrying the legacy shape. (Today: zero.)
2. Drop the `<abs-path>@<sha>` fallback branch from
   `resolve_uri` in `scripts/validate_run_evidence.py`.
3. Drop the legacy parse branch from `scripts/replay_run.py`
   `_enforce_head`.
4. Add a `R-EVL-028` requirement under spec 0004 naming the
   URI grammar as the only accepted shape.
5. Land a new DEC (DEC-EVL-011) amending DEC-EVL-009 to record
   the migration as complete.

## cost

Small. Three single-file edits, one new DEC, one R-EVL row in
the spec ledger, and the regression test refresh.

## risk

If any other portfolio repo emits a sample against this repo's
validator under the legacy shape during the cutover, that
sample will fail the gate. Mitigation: coordinate the legacy
retirement with athena-site DEC-CDCP-014 progress and confirm
no producer repo still emits the legacy shape in its W22 or W23
window.

## timeline

Next sprint (2026-W23 or W24). The cutover is mechanical once
the audit confirms no legacy samples exist; the DEC + spec row
takes one commit.

## promotion path

The operator audits the run-record corpus, opens DEC-EVL-011 as
a draft, runs the four edits against a feature branch, confirms
the full CI chain stays green on the canonical sample, then
merges. No prompt or eval-suite change required.

## risks if promoted blindly

- Dropping the legacy fallback before the audit completes
  could turn a stale-but-valid sample into a CI failure.
  Mitigation: the audit step is gating.
- The athena-site cross-repo consumer schema already pins URIs
  as the only accepted shape per DEC-CDCP-014. The producer-side
  cutover follows the consumer-side contract; there is no
  protocol negotiation gap to manage.
