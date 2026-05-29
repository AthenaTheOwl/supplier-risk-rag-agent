---
id: dream-2026-W22-backlog-003
target_kind: backlog_item
mode: architecture_drift_detection
human_review_required: true
status: candidate
evidence:
  - kind: decision
    ref: decisions/DEC-EVL-009-supplier-risk-rag-agent-portable-repo-uri-migration.md
  - kind: decision
    ref: decisions/DEC-EVL-010-supplier-risk-rag-agent-ci-enforces-run-evidence-chain.md
  - kind: doc
    ref: .github/workflows/run-evidence-gates.yml
  - kind: doc
    ref: scripts/validate_run_evidence.py
  - kind: doc
    ref: ops/run-records/run-643dff8f3b9c.json
---

## title

Pin a cross-link contract test between this repo and the sibling `trace-to-eval-consumer` for the `repo://` resolver semantics

## rationale

DEC-EVL-009 emits `repo://` URIs per the athena-site DEC-CDCP-014
grammar. DEC-EVL-010 wires the packet-and-replay job in CI to
check out the sibling consumer repo (`trace-to-eval-consumer`),
pip-install it, and run packet-gen + packet-validate against the
canonical sample with `--portfolio-root` pointing at the workspace.
That CI job already verifies the producer-side URI emits a packet
the consumer-side schema accepts.

What is not pinned: the consumer-side resolver semantics. If the
sibling consumer's `repo://` resolver changes its handling of (a)
missing path components, (b) the empty-path-after-SHA shape, or
(c) the `artifact://` scheme dispatch, this repo's CI catches
nothing until the contract breaks at packet-validate time. The
gap shows up as a green CI run today that turns red the day the
sibling consumer ships a backward-incompatible resolver change.

The proposed work is two pieces:

1. Add a contract test under `tests/test_repo_uri_contract.py`
   that asserts the producer-side emitter produces URIs the
   sibling consumer's resolver round-trips correctly. The test
   imports the sibling resolver (sibling consumer is already
   pip-installed in CI per DEC-EVL-010), runs the producer
   emitter against a fixture, feeds the output URIs to the
   sibling resolver, and asserts each resolves to the expected
   relative path.
2. Land a cross-link DEC at this repo (and a matching companion
   DEC at the sibling consumer, file separately) naming the
   round-trip contract. The DEC references athena-site
   DEC-CDCP-014 as the spec source.

The cross-link DEC closes the loop: producer and consumer both
hold each other accountable to the URI grammar, not to each
other's implementation details.

## cost

Small to medium. The contract test is a single file with
fixture-driven assertions. The cross-link DEC is one DEC plus
a companion DEC at the sibling repo (out of scope for this
work item; that lands as a separate W23 commit at the sibling
repo).

## risk

Adding a direct import of the sibling consumer's resolver as a
test dependency couples this repo's test surface to the sibling
repo's API. If the sibling repo refactors the resolver location
or signature, this repo's contract test breaks. Mitigation: the
sibling consumer's resolver API is already pinned by
athena-site DEC-CDCP-014 (the grammar) and the sibling repo's
own DEC (the resolver shape). The contract test pins the round-
trip behavior, not the import path; if the sibling resolver
moves, the contract test gets a one-line import update.

A second risk: the contract test creates a new failure mode
where the sibling consumer's CI green status depends on this
repo's CI green status. Mitigation: the contract is symmetric
under athena-site DEC-CDCP-014; both repos are constrained by
the same grammar, so neither can land a unilateral change
without breaking the other.

## timeline

Next sprint (2026-W23). The work is well-scoped, the sibling
consumer is already wired in CI per DEC-EVL-010, and the
contract is small.

## promotion path

The operator opens a draft DEC-EVL-011 (or DEC-CDCP-016 at the
athena-site level if that DEC name is reserved), writes the
contract test under `tests/test_repo_uri_contract.py`, confirms
it passes against the current sibling consumer, lands the DEC
referencing athena-site DEC-CDCP-014, and merges. A companion
DEC lands at the sibling consumer repo in the same week.

## risks if promoted blindly

- The cross-link DEC creates a portfolio-wide dependency between
  two repos' CI status. The dependency is already implicit in
  DEC-EVL-010 (CI checks out and installs the sibling repo);
  this candidate makes it explicit and adds a test that pins it.
- The companion DEC at the sibling repo is out of scope for this
  repo's W22 work. The cross-link is one-sided until the
  companion lands. Mitigation: the contract test runs against
  the sibling repo's current resolver shape; if the sibling
  repo's resolver changes, the test breaks and surfaces the
  drift. The companion DEC formalizes the contract symmetrically.
- This candidate is the only cross-link in the W22 candidate
  set. Promoting it without the companion creates a
  documentation asymmetry; the audit trail at this repo points
  at the sibling, the sibling has no matching pointer back.
  Mitigation: the companion DEC is filed at the sibling repo in
  the same commit pair.
