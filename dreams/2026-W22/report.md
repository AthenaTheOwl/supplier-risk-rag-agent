dream 2026-W22 supplier-risk-rag-agent
========================================

Second weekly dream pass. Lookback window 2026-05-25 to
2026-05-29 (five days). The window covers the v2
engineering-grade run-evidence rollout: Rounds 1-8 plus the
matching Workflow A/B passes that landed the CI enforcement
contract.

Subject
-------

Retrospect on the v2 engineering-grade run-evidence rollout and
project the next moves with the largest payoff.

What the v2 rollout shipped in this repo
----------------------------------------

Five DECs landed in five days, all amending or extending the
eval subsystem:

- DEC-EVL-006: Eval runner emits a conformant Run record per
  the cross-repo schema. The runner now writes one
  ops/run-records/run-<id>.json per suite invocation, plus a
  matching ops/event-ledger/run-<id>.jsonl carrying the typed
  events.
- DEC-EVL-007: The validator gained Round-3 cross-checks. Every
  Run.events_uri resolves to a real ledger file, every ledger
  event run_id matches the Run record, and every typed event
  payload validates against the matching ref in
  event.schema.json.
- DEC-EVL-008: A HEAD-strict equivalence-replay command shipped
  at scripts/replay_run.py. The command re-runs the recorded
  sample under the recorded code state and exits 0 only if
  replay_equivalent: true on three signals
  (prompt_snapshot_hash, tool_schemas_snapshot_hash,
  gate_results_summary).
- DEC-EVL-009: The emitter migrated to the portable repo:// URI
  grammar from athena-site DEC-CDCP-014. The same DEC fixed the
  systemic sandbox_image_ref off-by-one via a two-pass emit
  pattern (PENDING placeholder plus post-commit
  finalize_sandbox_ref.py). The PENDING-aware replay path lets
  a freshly regenerated sample stay verifiable without an
  intervening finalize step.
- DEC-EVL-010: A second CI workflow at
  .github/workflows/run-evidence-gates.yml enforces the
  portfolio-wide gate chain from athena-site DEC-CDCP-015 on
  every PR and every push to main. Two jobs: universal-gates
  (schema cache freshness, voice lint, BOM check, spec check,
  six typed-artifact validators, typed-event-payload validation,
  pytest) and packet-and-replay (packet gen from canonical
  sample, packet validate, replay smoke against the recorded
  sandbox SHA).

Plus the supporting infrastructure: 22 new R-EVL requirements
across spec 0004, two schema-cache refreshes (run.schema.json,
event.schema.json), the canonical sample run-643dff8f3b9c, and
a third-pass voice-lint update (harness removed from
BANNED_FAIL).

What is now load-bearing that was not 30 days ago
-------------------------------------------------

The repo now has a typed run-evidence chain end to end:

- Typed event payloads. Each event in ops/event-ledger/*.jsonl
  has a payload that validates against the matching ref in
  event.schema.json. The run.evidence.replayed event type is
  shipped and verified. Before this rollout, events were
  free-form JSON; the schema was advisory.
- Portable repo:// URIs. Run.sandbox_image_ref,
  Run.inputs[].ref, and Run.workspace_id all use the cross-repo
  URI grammar. A sibling consumer in another portfolio repo can
  resolve a reference without baking in this repo local layout.
  Before, refs were Windows absolute paths.
- Two-pass sandbox SHA emission. The PENDING placeholder plus
  scripts/finalize_sandbox_ref.py pattern pins the data-bearing
  commit instead of its parent. Four agents across the portfolio
  caught the same off-by-one independently; the fix landed once
  across all of them.
- HEAD-strict replay. scripts/replay_run.py enforces that the
  working tree sits at the SHA the recorded sandbox_image_ref
  pins before computing replay equivalence. The PENDING branch
  handles freshly regenerated samples.
- CI contract chain on every PR. Schema cache freshness, voice
  lint, BOM check, spec check, six typed-artifact validators
  (decisions, roles, tools, policies, skills, dreams),
  typed-event-payload validation, packet gen, packet validate,
  and replay smoke all block the merge. No gate carries
  continue-on-error: true. No step uses --no-verify.

What used to be manual: regenerating the canonical sample,
running the validators locally, checking that the recorded SHA
matched the commit. What CI now catches automatically: any of
those drifting.

What surfaced as a fragile edge
-------------------------------

Four edges showed up during the rollout and are worth naming:

1. sandbox_image_ref off-by-one. Caught by four agents
   independently across the portfolio. The Round-5 single-pass
   emit recorded the parent of the data-bearing commit.
   DEC-EVL-009 Option A (two-pass emit with PENDING placeholder)
   fixes it without restructuring the runner emission pipeline.
   The fragile shape: any future record-the-SHA-at-emit-time
   refactor would re-introduce the same bug.
2. Voice-lint harness ban. voice_lint.py originally listed
   harness in BANNED_FAIL, which blocked landing
   tests/test_replay_determinism.py (the docstring uses
   ChatGPT-pulse replay-determinism harness). Commit da83e4e
   removed it. The fragile shape: the editorial wordlist is
   coupled to a moving target.
3. CRLF line endings on Windows. The .gitattributes file plus
   the check_no_bom.py gate caught it portfolio-wide. The
   tests/test_replay_run.py and test_run_evidence.py files had
   to be written with explicit LF endings to pass CI.
4. Legacy local-path acceptance. The validator and replay
   command both accept repo:// URIs AND legacy <abs-path>@<sha>
   shapes during the migration round. That tolerance is a
   temporary scaffold; it widens the validator surface and lets
   a stale sample slip through unnoticed.

DECs vs documented-but-unenforced
---------------------------------

Every behavioral promise landed as a DEC backed by an executable
gate:

| Promise | DEC | Gate |
|---|---|---|
| Emitter produces conformant Run records | DEC-EVL-006 | scripts/validate_run_evidence.py in CI |
| Run/Event cross-checks | DEC-EVL-007 | same script, Round-3 branch |
| Replay equivalence is testable | DEC-EVL-008 | scripts/replay_run.py in CI plus tests/test_replay_run.py |
| Portable URI grammar | DEC-EVL-009 | validator and replay both resolve repo:// |
| Two-pass sandbox SHA | DEC-EVL-009 | scripts/finalize_sandbox_ref.py plus PENDING branch |
| CI contract chain | DEC-EVL-010 | .github/workflows/run-evidence-gates.yml |

Nothing landed as documentation-without-enforcement this week.
The two-pass emission pattern is documented in the DEC and
encoded in the script; the PENDING semantics are documented in
the DEC and encoded in replay_run.py _enforce_head. The gap
from W21 (allowlist-deferred R-* requirements) is also narrower:
most new R-EVL-006..027 requirements ship with a DEC in the same
commit pair, so the spec-check allowlist did not grow during
this rollout.

Candidates produced
-------------------

Five candidates across four modes:

| File | Mode | Kind | Shape |
|---|---|---|---|
| candidates/backlog-001-retire-legacy-local-path-acceptance.md | architecture_drift_detection | backlog_item | reduce |
| candidates/memory-001-two-pass-emission-pattern.md | memory_consolidation | memory_update | anchor a load-bearing pattern |
| candidates/backlog-002-replay-chaos-suite.md | failure_clustering | backlog_item | audit |
| candidates/skill-001-finalize-sandbox-ref-workflow.md | skill_extraction | skill_patch | extend |
| candidates/backlog-003-cross-link-sibling-consumer-resolver-contract.md | architecture_drift_detection | backlog_item | cross-link to athena-site / sibling consumer |

Every candidate carries human_review_required: true per
dream-candidates-require-human-approval.yaml. The orchestrator
does not promote any candidate; the operator applies, rejects,
or files each one.

Skipped modes
-------------

Three modes do not run this week. Reopen preconditions:

- adversarial_simulation: same as W21; generation budget and
  safe sandbox still not wired. Reopen when the
  adversarial-test-generation skill graduates.
- golden_test_generation: the W21 pass pinned ranker weights
  and the offline-cache fallback; no fresh spec-without-eval
  gap surfaced this week. Reopen when a new spec ships
  requirements without paired eval coverage.
- prompt_patch_generation: no prompt drift signal; the default
  model is unchanged and the
  eval-suite-required-before-prompt-change policy still gates
  prompt edits. Reopen when the prompt suite shows quality
  drift across consecutive runs.

Evidence sources
----------------

- git log --oneline -30 (the v2 rollout window).
- decisions/DEC-EVL-006 through DEC-EVL-010 (the five DECs that
  landed during the window).
- specs/0004-evals-and-thresholds/requirements.md
  R-EVL-006..027.
- ops/run-records/run-643dff8f3b9c.json plus the matching
  ledger at ops/event-ledger/run-643dff8f3b9c.jsonl.
- .github/workflows/run-evidence-gates.yml (the contract
  chain).
- scripts/validate_run_evidence.py, scripts/replay_run.py,
  scripts/finalize_sandbox_ref.py (the producer-side gate
  scripts).
- src/evals/run_evidence.py, src/evals/runner.py (the emitter
  sites).
- tests/test_run_evidence.py, tests/test_replay_run.py,
  tests/test_replay_determinism.py (the determinism harness
  the W22 voice-lint update unblocked).
- dreams/2026-W21/ (last week pass for cross-week continuity).

Next pass
---------

The 2026-W23 dream pass should re-run the four W22 modes plus
re-evaluate adversarial_simulation. The replay-determinism
harness shipped this week (tests/test_replay_determinism.py)
is the natural adversarial-input target: a chaos suite that
permutes the ledger, mutates the recorded sample, and asserts
the replay command catches each mutation. Backlog-002 in this
week candidates seeds that work.
