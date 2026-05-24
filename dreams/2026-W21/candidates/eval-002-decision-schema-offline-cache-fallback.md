---
id: dream-2026-W21-eval-002
kind: test_generation
target: tests/test_validate_decisions_offline.py
mode: golden_test_generation
human_review_required: true
status: promoted
promotion_date: 2026-05-24
evidence:
  - scripts/validate_decisions.py
  - ops/schemas-cache/decision.schema.json
  - decisions/DEC-CDCP-001-install-cdcp-governance.md
  - .agents/AGENTS.md
---

## proposal

Add a regression test at
`tests/test_validate_decisions_offline.py` that exercises the
offline-cache fallback in `scripts/validate_decisions.py`. The
test:

1. Monkeypatches `load_remote_schema` to return `None` (simulating
   a network failure or sandboxed CI without egress).
2. Calls `load_schema()` and asserts it returns the cached schema
   loaded from `ops/schemas-cache/decision.schema.json`.
3. Asserts the cached schema validates the existing DEC files
   under `decisions/` (round-trips through `parse_front_matter`
   plus `validator.iter_errors`) and returns zero violations.
4. Asserts that deleting the cache file (in a tmp_path copy)
   raises `SystemExit` with a message naming the cache path.

The test pins the offline-cache contract so a future change to
`load_schema` (caching strategy, schema source URL, retry
behavior) cannot silently break the no-network CI path.

## why it earns its keep

The offline-cache pattern is shared across the portfolio (the
same shape applies to `validate_roles`, `validate_tools`,
`validate_policies`, and the planned `validate_dreams`). This
repo's instance is the first under the cross-repo decision
schema; pinning it with a test gives the pattern a regression
signal here, and the other portfolio repos can copy the test
shape.

The CI workflow runs the six governance gates on every push. A
silent regression in the cache fallback would only surface when
network egress fails — which is exactly when the signal matters
and exactly when no one is watching. A test makes the failure
mode observable at PR time instead.

## evidence

- `scripts/validate_decisions.py` lines around `load_remote_schema`
  and `load_cached_schema` — the fallback path the test pins.
- `ops/schemas-cache/decision.schema.json` — the cached schema
  the test asserts against.
- `decisions/DEC-CDCP-001-install-cdcp-governance.md` (and the
  nine others) — the corpus the cached schema validates.
- `.agents/AGENTS.md` lines around `## Cross-repo links` — the
  policy that names the schema source URL and the cache path.

## promotion path

A human reviewer writes the new test file, runs `python -m uv
run pytest tests/test_validate_decisions_offline.py -v` to
confirm it passes against the current cache and decision set,
then runs the full suite to confirm coverage. The test adds a
handful of lines to `scripts/validate_decisions.py` coverage
(currently uncovered by the test suite since it ships as a
script, not an importable module).

## risks if promoted blindly

- The test depends on the current cached schema being the same
  schema the remote URL serves. If the remote schema evolves and
  the cache is stale, the test still passes but the fallback
  contract drifts from production. Mitigation: pair the test
  with a quarterly cache-refresh task (file as a backlog item,
  not as a CI gate, since the cache is meant to be long-lived).
- Monkeypatching `load_remote_schema` couples the test to the
  function name. A refactor that splits the function into
  smaller pieces requires updating the test. The risk is
  bounded; the alternative (a fully integration-style test that
  blocks egress at the OS level) is more fragile.
