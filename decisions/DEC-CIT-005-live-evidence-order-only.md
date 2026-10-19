---
id: DEC-CIT-005-live-evidence-order-only
spec: specs/0006-citation-faithfulness/
requirement: R-CIT-001
date: 2026-10-19
status: approved
reversible: true
decision: |
  Let a live provider order a complete set of verified citation labels.
  Render every displayed claim locally from the corresponding source span.
  Reject missing, duplicate, unknown, malformed, blank, or extra-content output.
  Distinguish accepted ordering, rejected output, and provider failure in answer
  metadata and the UI. Resolve session keys for the explicitly selected provider.
  Keep model-configuration dotenv loading behind the existing local-mode gate.
alternatives:
  - label: check only that generated prose contains known citation labels
    rejected_because: |
      A valid label can accompany an unsupported claim. Label membership does
      not establish that generated prose follows from the cited span.
  - label: let the provider select an arbitrary subset
    rejected_because: |
      Dropping evidence can remove a conflicting or qualifying source. A complete
      permutation preserves the existing deterministic evidence coverage.
rationale: |
  The prior path verified deterministic citations before generation and then
  attached them to arbitrary model text. Offline fake responses reproduced the
  failure with invented claims, unknown labels, missing labels, and blank output.
  Returning only label order bounds the model's authority and preserves the
  existing provider, model, retrieval defaults, refusal behavior, and spans.
evidence:
  - kind: test
    ref: tests/test_live_evidence_order.py
  - kind: test
    ref: tests/test_config.py
  - kind: doc
    ref: reports/live-evidence-order-baseline.json
  - kind: doc
    ref: reports/live-evidence-order-variant.json
rollback: |
  Disable live ordering and keep deterministic cited answers if the provider
  cannot meet the JSON contract. Do not restore unrestricted generated prose.
owner: engineering.implementation
systems_map: |
  A verifier established a property of source spans, but its result was carried
  across a generation boundary and presented as a property of new claims.
transferable_principle: |
  Restrict downstream output to transformations that preserve the verified
  property; reusing a receipt does not verify a new artifact.
falsification_test: |
  An arbitrary generated claim, omitted label, unknown label, or duplicate label
  reaches a non-fallback answer, or the five-suite baseline loses faithfulness.
adoption_ladder:
  minimum_viable: Validate the complete label permutation and render spans locally.
  mid_adoption: Expose distinct accepted, rejected, and failed modes to the operator.
  full_adoption: Check the bounded live path in a credentialed deployment smoke.
  monitoring_signals:
    - Rejected live output frequency.
    - Provider failure frequency.
    - Citation faithfulness and refusal suite regressions.
---

## Decision

Live output controls citation order. Local verified spans supply all displayed
claims. The credential resolver requires the selected provider's key and keeps
the existing local-environment gate.

## Validation

The paired reports distinguish keyless deterministic suite scores from fake
provider guard tests. They do not claim an OpenAI live request or establish that
the source corpus is complete, current, or independently true.
