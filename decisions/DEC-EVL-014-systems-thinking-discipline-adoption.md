---
id: DEC-EVL-014-systems-thinking-discipline-adoption
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-037
amends: DEC-EVL-013-supplier-risk-rag-agent-chaos-test-suite
date: 2026-05-29
status: approved
reversible: true
decision: |
  The supplier-risk-rag-agent repo adopts DEC-CDCP-020's
  systems-thinking discipline at the per-repo altitude. Four
  changes land together: (a) `ops/schemas-cache/` mirrors the
  athena-site amendment that added the four optional fields
  (`systems_map`, `transferable_principle`, `falsification_test`,
  `adoption_ladder`) to `decision.schema.json`,
  `dream-output.schema.json`, and `run.schema.json`; (b)
  `.agents/AGENTS.md` gains a top-level "Systems-thinking
  discipline" section naming the four fields and the
  warn-then-fail ratchet; (c) `scripts/validate_decisions.py`
  emits a non-fatal WARN on approved DECs missing any of the
  four fields (exit code stays 0 so the bootstrap-friendly
  default holds); (d) the three most recent DECs (DEC-EVL-011,
  DEC-EVL-012, DEC-EVL-013) carry the four fields as the
  demonstration pass.

  The remaining 29 historical DECs stay on the WARN list. A
  future amendment DEC ratchets the warning to FAIL after the
  30-day organic-adoption window and after a coverage pass that
  retrofits at least 80% of the historical DECs.
alternatives:
  - label: Option A — adopt only the schema-cache refresh, defer AGENTS.md and validator
    rejected_because: |
      A cache-only adoption installs the contract surface but
      leaves the discipline invisible to a future author. The
      validator's WARN is the surface that converts the contract
      into observable practice; AGENTS.md is the surface that
      teaches a new author the four fields exist. Shipping only
      the cache would leave the field-population rate dependent
      on each author reading the upstream DEC, which is a brittle
      signal. Cache + AGENTS.md + validator land together so the
      author sees the discipline named in three independent
      places on first contact.
  - label: Option B — set the validator to FAIL on missing fields immediately
    rejected_because: |
      Immediate FAIL would block the next 29 DEC edits in this
      repo until each one is retrofitted. The four fields are
      genuinely optional on some DEC shapes (pure-design choices
      may carry an "n/a" falsification test, for example), and a
      mid-pass FAIL would force the retrofitting pass into the
      critical path of every other edit. The WARN-now,
      FAIL-after-30-days pattern matches DEC-CDCP-020's own
      ratchet language and gives the discipline an organic
      adoption window.
  - label: Option C — retrofit all 32 DECs in this pass
    rejected_because: |
      A 32-DEC retrofit is a 32x cost on the closing pass that
      would produce padded entries on DECs whose author no longer
      remembers the systemic mechanism the decision exposed. The
      three-most-recent retrofit produces honest entries (the
      author is the same agent that wrote the DEC) and seeds the
      pattern for future DECs without producing a wall of
      reconstructed prose. A coverage pass that retrofits the
      historical DECs is the right shape to land before the
      30-day FAIL ratchet, not at the adoption moment.
  - label: Option D — install the discipline without populating the four fields on THIS DEC
    rejected_because: |
      Self-application is the strongest signal a new contract is
      load-bearing. A DEC that installs the four-field discipline
      and then omits the four fields on its own front-matter
      would model the wrong behavior on the next author. The four
      fields on THIS DEC's front-matter carry the discipline's
      first concrete example and the validator's first
      green-against-the-discipline assertion on the new DEC.
rationale: |
  Phase 1 landed DEC-CDCP-020 in athena-site, which amended
  three cross-repo schemas to add the four optional
  systems-thinking fields and named the warn-then-fail ratchet.
  This DEC is the per-repo landing of that contract in
  supplier-risk-rag-agent. The pattern matches the other
  cross-repo schema discipline landings in this repo (the
  run-evidence chain, the dream-output schema): refresh the
  cache from the upstream, name the new surface in AGENTS.md,
  extend the local validator, and anchor the pattern on a small
  batch of artifacts.

  The four-surface adoption (cache + AGENTS.md + validator +
  retrofit) is the same shape any future portfolio-wide schema
  edit lands with. Skipping any surface degrades the discipline:
  cache-only leaves the discipline invisible; AGENTS.md-only
  leaves it unenforced; validator-only leaves it unexplained;
  retrofit-only leaves it un-anchored to the schema. Landing all
  four together gives the discipline four independent surfaces
  any future author or reviewer touches on first contact.

  The WARN-now-FAIL-later ratchet is the right shape for a
  discipline whose four fields some DEC shapes legitimately
  carry as "n/a" (a pure-design choice may not have a
  falsification test in the empirical-experiment sense). The
  30-day window is the organic-adoption signal: if new DECs
  populate the fields at >=80% rate without further enforcement,
  the discipline is taking hold and the FAIL ratchet is safe to
  land; if the rate stays below 20%, the discipline isn't
  landing and the ratchet escalates instead of forcing a
  surprise FAIL on every author at day 31.

  Reversibility: dropping this DEC means reverting the
  schemas-cache changes (three files), reverting the AGENTS.md
  section, reverting the validator extension, dropping the
  four-field front-matter blocks from DEC-EVL-011..013, and
  dropping R-EVL-037..040 from the spec ledger. The four
  upstream schemas at athena-site are not touched by rollback;
  this repo simply stops mirroring the four optional fields.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: decision
    ref: decisions/DEC-EVL-013-supplier-risk-rag-agent-chaos-test-suite.md
  - kind: decision
    ref: https://github.com/AthenaTheOwl/athena-site/blob/main/decisions/DEC-CDCP-020-systems-thinking-discipline.md
  - kind: doc
    ref: ops/schemas-cache/decision.schema.json
  - kind: doc
    ref: ops/schemas-cache/dream-output.schema.json
  - kind: doc
    ref: ops/schemas-cache/run.schema.json
  - kind: doc
    ref: .agents/AGENTS.md
  - kind: doc
    ref: scripts/validate_decisions.py
  - kind: doc
    ref: decisions/DEC-EVL-011-supplier-risk-replay-determinism-test.md
  - kind: doc
    ref: decisions/DEC-EVL-012-edgar-refresh-and-adversarial-refusal-suite.md
  - kind: doc
    ref: decisions/DEC-EVL-013-supplier-risk-rag-agent-chaos-test-suite.md
rollback: |
  Revert the schemas-cache updates for
  `ops/schemas-cache/decision.schema.json`,
  `ops/schemas-cache/dream-output.schema.json`, and
  `ops/schemas-cache/run.schema.json`. Revert the
  "Systems-thinking discipline" section in `.agents/AGENTS.md`.
  Revert the systems-thinking WARN block in
  `scripts/validate_decisions.py`. Drop the four-field
  front-matter additions from DEC-EVL-011..013. Drop
  R-EVL-037..040 from
  `specs/0004-evals-and-thresholds/requirements.md` and the
  matching rows from
  `specs/0004-evals-and-thresholds/traceability.md`. Delete this
  DEC.
owner: control.coordinator
systems_map: |
  Per-repo adoption of cross-repo control-plane discipline. The
  schema cache is the contract; AGENTS.md is the readme; the
  validator is the enforcement; the retrofit is the
  demonstration. Four surfaces, one mechanism: a portfolio-wide
  schema lands per-repo via cache + readme + enforcement +
  demonstration.
transferable_principle: |
  Any cross-repo schema discipline lands per-repo via the same
  four-surface pattern (cache + readme + enforcement +
  demonstration); skipping any surface degrades the discipline.
falsification_test: |
  If new DECs in this repo over the 30-day organic-adoption
  window populate the four fields at less than 20% rate despite
  the validator WARN, the discipline isn't taking hold and the
  ratchet escalates to FAIL instead of staying on the
  bootstrap-friendly default.
adoption_ladder:
  minimum_viable: |
    Cache refreshed; AGENTS.md updated; validator emits WARN on
    missing fields.
  mid_adoption: |
    Three most recent DECs retrofitted; new DECs populate the
    four fields organically; coverage pass retrofits historical
    DECs toward the 80% bar.
  full_adoption: |
    Validator FAILs on missing fields per a future amendment
    DEC; at least 80% of historical DECs carry the four fields;
    sibling consumer repos in the portfolio install the same
    four-surface adoption.
  monitoring_signals:
    - new-DEC field-population rate per week
    - validator WARN-count trend over the 30-day window
    - count of historical DECs retrofitted per coverage pass
---

## decision

The supplier-risk-rag-agent repo adopts DEC-CDCP-020's
systems-thinking discipline. Four surfaces land together: the
schemas-cache mirror, the AGENTS.md section, the validator's WARN
block, and the three-DEC retrofit (DEC-EVL-011..013). The remaining
29 historical DECs stay on the WARN list until a future coverage
pass; the warn-then-fail ratchet escalates after the 30-day
organic-adoption window.

## alternatives

- Option A (cache-only adoption): rejected because cache without
  AGENTS.md + validator leaves the discipline invisible to a new
  author.
- Option B (immediate FAIL): rejected because it would block 29
  in-flight DEC edits and force the retrofit pass into the
  critical path of every other edit.
- Option C (retrofit all 32 DECs): rejected because a 32-DEC
  retrofit produces padded entries on DECs whose mechanism the
  author no longer remembers.
- Option D (install discipline without self-applying): rejected
  because self-application is the strongest signal a new contract
  is load-bearing.

## rationale

Phase 1 landed DEC-CDCP-020 in athena-site as the cross-repo
schema amendment. This DEC is the per-repo landing in
supplier-risk-rag-agent. The four-surface pattern (cache +
AGENTS.md + validator + retrofit) mirrors the other cross-repo
schema landings in this repo and gives the discipline four
independent surfaces a future author or reviewer touches on first
contact.

The WARN-now-FAIL-later ratchet matches DEC-CDCP-020's own
language and gives the discipline an organic-adoption window. If
new-DEC field-population rate stays above 80% over 30 days, the
FAIL ratchet is safe to land; if the rate drops below 20%, the
discipline isn't landing and the ratchet escalates with a
surprise-free amendment DEC.

## evidence

- `ops/schemas-cache/{decision,dream-output,run}.schema.json`
  carry the upstream four-field amendment.
- `.agents/AGENTS.md` carries the top-level "Systems-thinking
  discipline" section.
- `scripts/validate_decisions.py` carries the systems-thinking
  WARN block.
- `decisions/DEC-EVL-011..013` carry the four-field front-matter
  blocks as the demonstration pass.
- `decisions/DEC-CDCP-020` in athena-site is the upstream
  contract this DEC adopts.

## rollback

Revert the four schemas-cache files, the AGENTS.md section, the
validator extension, the three retrofitted DECs, and drop
R-EVL-037..040 from the spec ledger. Delete this DEC.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-037` The repo mirrors the upstream
  `decision.schema.json`, `dream-output.schema.json`, and
  `run.schema.json` from athena-site under
  `ops/schemas-cache/` so the four optional systems-thinking
  fields (`systems_map`, `transferable_principle`,
  `falsification_test`, `adoption_ladder`) are visible to the
  local validators.
- `R-EVL-038` `.agents/AGENTS.md` carries a top-level
  "Systems-thinking discipline (per DEC-CDCP-020)" section that
  names the four fields, the WARN-now-FAIL-later ratchet, and
  the 30-day organic-adoption window.
- `R-EVL-039` `scripts/validate_decisions.py` emits a non-fatal
  WARN to stderr on every approved DEC missing any of the four
  systems-thinking fields. Exit code stays 0; the bootstrap-
  friendly default holds until a future amendment DEC ratchets
  the warning to FAIL.
- `R-EVL-040` The three most recent DECs (DEC-EVL-011,
  DEC-EVL-012, DEC-EVL-013) carry the four systems-thinking
  fields on their front-matter as the demonstration pass; the
  validator emits no WARN against the three retrofitted DECs.
