---
id: DEC-CIT-002-amendment-reversibility-mitigation
spec: specs/0006-citation-faithfulness/
requirement: R-CIT-002
date: 2026-05-24
status: approved
reversible: true
decision: |
  Amend DEC-CIT-002 with a reversibility-mitigation path. The
  original DEC marked the seven-field `Citation` shape as
  `reversible: false` because a field shrink would touch
  `app.py`, the verifier, the answerer, the eval suite, and the
  tests in one commit. The amendment names the mitigation: if a
  future shape change is ever needed, ship a `CitationV2`
  dataclass alongside the existing `Citation`, migrate consumers
  one at a time across at least one release cycle behind a
  `ModelConfig.citation_shape_version` feature flag, and only
  then deprecate V1. A direct in-place field shrink stays
  prohibited. The V2 sketch lives at
  `docs/citation-shape-evolution.md`. The amendment does not
  change the V1 shape today; it documents the forward route so
  the lock-in is bounded, not absolute.
alternatives:
  - label: in-place edit of the existing Citation shape
    rejected_because: |
      Same reason DEC-CIT-002 marked the shape reversible:false.
      A single-commit field shrink would silently break the
      citations expander in app.py, the verifier's chunk-id
      lookup, every test that constructs a Citation with the old
      shape, and any downstream serialization consumer. The
      amendment exists to forbid this path and name the
      dual-type alternative.
  - label: type-deprecation library (e.g., Deprecated, typing-extensions)
    rejected_because: |
      A library-driven deprecation flow adds a dependency for a
      problem that has not happened yet. The dual-type pattern
      is plain Python: a parallel dataclass, a feature flag on
      ModelConfig, and a conversion helper. No new dependency
      surface, no learned tooling, and the eval gate still
      catches regressions at each migration step.
  - label: no mitigation (accept reversible:false as terminal)
    rejected_because: |
      The original DEC's reversible:false flag was honest about
      today's lock-in but did not document a forward route. A
      future maintainer reading the DEC would have no path
      other than a hard cutover or an unplanned multi-commit
      migration. The amendment closes that gap without changing
      the V1 contract.
  - label: land the CitationV2 dataclass now (no consumer wired)
    rejected_because: |
      No consumer needs V2 today. Landing the dataclass
      pre-emptively adds dead code to the module and a parallel
      shape that the eval suite, the verifier, and the renderer
      all have to know how to ignore. The sketch lives in
      docs/citation-shape-evolution.md until a real consumer
      (full EDGAR ingestion, second verifier version, or a
      promotion from the metadata dict) needs the new field.
rationale: |
  The amendment is a meta-decision: it does not change the
  Citation shape today, it does not change the verifier, and it
  does not change any consumer. It captures the policy that a
  future shape change (especially a field shrink) ships through
  a dual-type migration with the four-suite eval gate at every
  step. A hard cutover is not the path.

  The dual-type pattern is reversible by construction. Step 1
  lands V2 alongside V1 with no consumer changes; if the eval
  gate or the renderer behavior surfaces a problem, V2 gets
  removed in a single commit with zero behavior change. Each
  subsequent migration step is similarly bounded: the feature
  flag on ModelConfig lets a consumer roll back to V1 without a
  code change, and the eval gate catches a regression before
  the next consumer migrates.

  The amendment also strengthens the audit story. A reader of
  DEC-CIT-002 today sees the lock-in flag but not the forward
  route. A reader of DEC-CIT-002 plus this amendment sees the
  lock-in AND the policy for how a future change is allowed to
  proceed. The lock-in is bounded by the dual-type contract,
  not absolute.
evidence:
  - kind: decision
    ref: DEC-CIT-002-citations-carry-filing-level-identifiers.md (the
      original DEC; reversible:false on the seven-field shape)
  - kind: doc
    ref: docs/citation-shape-evolution.md (the V2 sketch + migration
      path + ship and reverse conditions)
  - kind: doc
    ref: src/retrieval/citations.py (the current Citation dataclass)
  - kind: spec
    ref: specs/0006-citation-faithfulness/
  - kind: decision
    ref: DEC-EVL-001-four-suite-eval-gate-with-thresholds.md (the
      gate that runs at every migration step)
rollback: |
  Discard the V2 sketch. The amendment does not change any
  production code; reversing it is removing
  `docs/citation-shape-evolution.md` and this DEC, leaving
  DEC-CIT-002 unchanged. No eval re-run is needed because no
  production behavior changes. If a future maintainer chooses
  to pursue an in-place shrink despite this amendment, they
  would need to land a superseding DEC that names the new
  policy and the four-suite results that justify it; the
  amendment cannot be silently overridden.
owner: engineering.implementation
---

## decision

Amend DEC-CIT-002 with a reversibility-mitigation path. The
original DEC marked the seven-field `Citation` shape as
`reversible: false`. The amendment names the mitigation: if a
future shape change is ever needed, ship a `CitationV2`
dataclass alongside the existing `Citation`, migrate consumers
one at a time across at least one release cycle behind a
`ModelConfig.citation_shape_version` feature flag, and only then
deprecate V1. A direct in-place field shrink stays prohibited.
The V2 sketch lives at `docs/citation-shape-evolution.md`. No
production code changes today.

## alternatives

- In-place edit of the existing Citation shape — the path
  DEC-CIT-002's `reversible: false` flag already forbids.
- Type-deprecation library — adds a dependency for a problem
  that has not happened yet.
- No mitigation (accept `reversible: false` as terminal) —
  honest about today's lock-in but leaves a future maintainer
  with no forward route.
- Land CitationV2 now without a consumer — adds dead code and a
  parallel shape every consumer has to ignore.

## rationale

The amendment is a meta-decision. It does not change the
Citation shape, the verifier, or any consumer. It captures the
policy that a future shape change ships through a dual-type
migration with the four-suite eval gate at every step.

The dual-type pattern is reversible by construction. The
feature flag on `ModelConfig` lets a consumer roll back to V1
without a code change, and the eval gate catches a regression
before the next consumer migrates. The amendment strengthens
the audit story: a reader of DEC-CIT-002 plus this amendment
sees the lock-in AND the policy for how a future change is
allowed to proceed.

## evidence

- `DEC-CIT-002-citations-carry-filing-level-identifiers.md` —
  the original DEC.
- `docs/citation-shape-evolution.md` — the V2 sketch, migration
  path, and ship-or-reverse conditions.
- `src/retrieval/citations.py` — the current Citation
  dataclass.
- `DEC-EVL-001-four-suite-eval-gate-with-thresholds.md` — the
  gate that runs at every migration step.

## rollback

Discard the V2 sketch. The amendment does not change any
production code; reversing it is removing
`docs/citation-shape-evolution.md` and this DEC, leaving
DEC-CIT-002 unchanged. No eval re-run is needed because no
production behavior changes. A future maintainer choosing to
pursue an in-place shrink despite this amendment would need to
land a superseding DEC that names the new policy and the
four-suite results that justify it.
