# traceability: cognitive-delivery-control-plane

| Requirement | Design surface | Planned proof | Owner role |
|---|---|---|---|
| R-CDCP-001 | `scripts/spec_check.py` + `decisions/.spec-check-allowlist.yaml` | `python scripts/spec_check.py` walks every R-* and confirms one DEC reference or allowlist entry per ID | `owner_role: science.proof-gate-runner` |
| R-CDCP-002 | `scripts/validate_decisions.py` + `ops/schemas-cache/decision.schema.json` | `python scripts/validate_decisions.py` validates each DEC file against the cross-repo schema | `owner_role: science.proof-gate-runner` |
| R-CDCP-003 | `dreams/README.md` + future `dreams/<week>/output.json` | first dream output lands with a `validate_dreams.py` gate in a later pass; this requirement reserves the contract | `owner_role: learning.dream-orchestrator` |
| R-CDCP-004 | `ops/RELEASE_LEDGER.md` with the six-commit backfill | manual review during commit; future automation may parse the ledger | `owner_role: control.coordinator` |
| R-CDCP-005 | `ops/RESET_LEDGER.md` with documented format header | reset entries land in the same push that performs the rewrite | `owner_role: control.coordinator` |
| R-CDCP-006 | `.agents/AGENTS.md` with the four documented sections | agents read the file first; cross-repo charter names the rule | `owner_role: control.coordinator` |
| R-CDCP-007 | `.agents/skills/run-supplier-risk-query/SKILL.md` v0.1.0 | front-matter parses against `skill.schema.json`; future `validate_skills.py` lands when the second skill graduates | `owner_role: learning.skill-curator` |
| R-CDCP-008 | `.github/workflows/gates.yml` running six python gates | a failed gate fails the CI run on PR | `owner_role: science.proof-gate-runner` |
| R-CDCP-009 | `dreams/README.md` documents the human-gate rule + `.agents/policies/dream-candidates-require-human-approval.yaml` | dream outputs land with `human_review_required: true`; policy file encodes the rule | `owner_role: learning.dream-orchestrator` |
| R-CDCP-010 | `scripts/validate_*.py` network-fetch paths + `ops/schemas-cache/` | schema bodies live in athena-site; this repo holds only cache copies | `owner_role: science.proof-gate-runner` |
