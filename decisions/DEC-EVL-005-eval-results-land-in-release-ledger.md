---
id: DEC-EVL-005-eval-results-land-in-release-ledger
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-005
date: 2026-05-24
status: approved
reversible: true
decision: |
  Record per-release eval results in `ops/RELEASE_LEDGER.md` as
  human-edited entries. Each entry names the released commit SHA, the
  date, the release title, the scope, and the four-suite gate result
  (pass or per-suite failure with the metric and threshold). A
  reverted experiment that did not pass the gate ships as a ledger
  entry too, with the failed gate named. Future automation may parse
  the ledger; today the contract is human-readable Markdown.
alternatives:
  - label: store per-release eval JSON only under `reports/`
    rejected_because: |
      JSON files under `reports/` rot. A reviewer six months later
      cannot scan `reports/` and know which release passed which
      gate without re-parsing every file. The ledger is the single
      append-only artifact a reviewer reads; it points back to the
      JSON files where they exist.
  - label: rely on GitHub Actions run history for the eval audit trail
    rejected_because: |
      Actions history is bounded (90 days by default) and tied to the
      hosting platform. The ledger is in-repo and survives a platform
      change. A reviewer with only a git clone can read the full eval
      history; a reviewer who has lost access to the GitHub Actions
      UI cannot.
  - label: a fully automated ledger writer in CI
    rejected_because: |
      Automation today would over-fit the ledger to the current four
      suites. The ledger is small enough that human edits are
      tractable; the gain from automation is not worth the lock-in
      to a specific suite shape. A future spec may add automation
      once the suite set stabilizes past a year.
rationale: |
  The release ledger is the human-readable audit trail. A reviewer
  who wants to know whether release v0.4.0 passed the faithfulness
  gate should be able to grep the ledger and read the answer. JSON
  artifacts under `reports/` are the machine-readable form; the
  ledger is the human-readable form. Both shapes earn their keep.

  The reverted experiments earn ledger entries too. The
  cross-encoder reranker's revert is recorded as a release entry
  that names the gate that failed (citation faithfulness at 0.933,
  below the 0.95 threshold). That entry is the audit trail for the
  reverted artifact under `experiments/01-cross-encoder-rerank/`.

  Human-edited Markdown is the right shape for the ledger today
  because the cadence is low (a release per change to the trunk's
  agent behavior, not a release per PR). A future spec may automate
  ledger writes once the cadence picks up and the suite set
  stabilizes; today the manual edit is fast and accurate.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/
  - kind: doc
    ref: ops/RELEASE_LEDGER.md
  - kind: doc
    ref: .agents/AGENTS.md `## Workflow conventions` (release ledger rule)
  - kind: doc
    ref: experiments/01-cross-encoder-rerank/notes.md (the reverted release)
rollback: |
  Drop the per-release entry requirement and let CI pipeline history
  carry the audit trail. The change is one paragraph in
  `.agents/AGENTS.md` and one paragraph in `ops/RELEASE_LEDGER.md`
  (the rule that requires an entry per release). The ledger file
  stays in tree as an append-only artifact even under this
  rollback; new entries become optional. Re-add the rule if a future
  audit reveals the GitHub Actions retention is too short.
owner: control.coordinator
---

## decision

Record per-release eval results in `ops/RELEASE_LEDGER.md` as
human-edited entries. Each entry names the released commit SHA, the
date, the title, the scope, and the four-suite gate result. A
reverted experiment that did not pass the gate ships as a ledger
entry with the failed gate named.

## alternatives

- Per-release JSON under `reports/` only — files rot; the ledger is
  the single append-only artifact.
- GitHub Actions run history — bounded retention; in-repo ledger
  survives a platform change.
- Fully automated ledger writer in CI — premature; the ledger is
  small enough for human edits and automation locks in the current
  suite shape.

## rationale

The ledger is the human-readable audit trail. JSON under `reports/`
is the machine-readable form. Reverted experiments earn ledger
entries: the cross-encoder revert is recorded with the failed gate
named (citation faithfulness at 0.933, below 0.95). Human edits are
tractable at the current cadence.

## evidence

- `ops/RELEASE_LEDGER.md` — the ledger file.
- `.agents/AGENTS.md` `## Workflow conventions` — the rule that names
  the ledger as the per-release proof surface.
- `experiments/01-cross-encoder-rerank/notes.md` — the reverted
  artifact the ledger references.

## rollback

Drop the per-release entry requirement and let CI history carry the
audit trail. The ledger file stays in tree as append-only; new
entries become optional. Re-add the rule if Actions retention turns
out to be too short.
