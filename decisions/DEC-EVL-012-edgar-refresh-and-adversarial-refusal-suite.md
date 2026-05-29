---
id: DEC-EVL-012-edgar-refresh-and-adversarial-refusal-suite
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-031
amends: DEC-EVL-011-supplier-risk-replay-determinism-test
date: 2026-05-29
status: approved
reversible: true
decision: |
  The supplier-risk-rag-agent repo SHALL add two paired surfaces:
  (a) a live EDGAR refresh script at `scripts/refresh_sample_corpus.py`
  that wraps the existing `refresh_edgar_corpus` pipeline with a
  three-CIK manifest (NVDA, TSM, AMAT) and writes a bounded fixture
  to `data/refreshed_corpus/chunks.jsonl` plus a refresh manifest at
  `data/refreshed_corpus/manifest.json`; and (b) an adversarial
  refusal precision eval suite at
  `eval_suites/adversarial_refusal_precision.yaml` with 10 cases
  that look in-scope for supplier-risk analysis but ask for
  information no SEC filing supplies (exact future numerical
  predictions, confidential business data, named-individual
  identifications, acquisition or policy-action predictions).

  The refresh script keyword-ranks each CIK's chunk set against a
  supplier-risk vocabulary and keeps the top two chunks per CIK so
  the fixture lands on risk-bearing prose instead of the XBRL
  header metadata at the start of each filing. The script falls back to a
  small offline-stub fixture when the SEC fetch fails (no network
  in the sandbox, rate-limit, transport error); the refresh
  manifest's `source` field records which path produced the
  fixture (`live_edgar` or `offline_stub`).

  The adversarial refusal suite shares the `evaluate_abstention`
  evaluator with the existing `refusal_cases` suite. Two refusal
  paths cover the new failure mode: a new `ADVERSARIAL_PHRASES`
  set in `src/agent/refusal.py` lists the substrings that should
  trigger refusal (predict, forecast, confidential, secret,
  private contract, will fail in, will be acquired, exact, risk
  score, etc.), and `should_refuse` carries a new branch that
  fires when any adversarial phrase matches the lowercased query.
  The runner gate threshold is `refusal_precision >= 0.85`,
  matching the existing refusal-cases threshold.

  The canonical sample corpus at `data/sample_corpus/` is not
  touched. The refresh fixture under `data/refreshed_corpus/` is a
  separate artifact that downstream consumers can opt into via the
  `--corpus` flag on `src/ingest/run_ingest.py`; the eval suites
  and the determinism fixture continue to load
  `data/sample_corpus/` by default.
alternatives:
  - label: Option A — pick citation_depth instead of adversarial refusal precision
    rejected_because: |
      Citation depth (measuring whether the cited span points at
      the most informative span vs a generic chunk) was the other
      candidate suite. Two reasons it lost the bake-off. First,
      the existing `citation_faithfulness` suite already covers
      verbatim-span verification at the 0.95 threshold, so a
      citation-depth suite would extend an existing gate's
      coverage instead of opening a new failure mode. Second,
      citation depth requires a separate "informative span"
      labelling pass on each retrieved chunk, which the runner
      cannot produce deterministically without either an LLM-
      based ranker or a hand-labelled gold set — both of which
      add cost the run-evidence chain does not pay for today.
      Adversarial refusal precision opens a distinct failure
      surface (an in-scope-looking query that should still
      refuse) and reuses the deterministic `evaluate_abstention`
      evaluator.
  - label: Option B — commit only the refresh fixture without the script
    rejected_because: |
      The fixture without the script is a one-shot blob a reviewer
      cannot reproduce. The script lands the script and the
      fixture together so a reviewer can re-run the refresh and
      diff the output against the committed file. The script also
      carries the offline-stub fallback so the repo's CI gates can
      run the script in sandboxes that block outbound traffic.
  - label: Option C — extend refusal_cases.yaml in place with the new cases
    rejected_because: |
      Extending the existing suite would tangle two failure modes
      in one gate. The original suite covers generic out-of-scope
      queries (weather, sports, personal phone numbers); the new
      surface covers in-scope-looking adversarial queries. Two
      named suites give a future reviewer two named failure
      surfaces to dispatch on; one tangled suite collapses to a
      single gate that says "refusal precision dropped" without
      naming the failure mode.
  - label: Option D — commit the refreshed corpus to data/sample_corpus/ alongside the canonical chunks
    rejected_because: |
      The canonical sample corpus is the deterministic eval fixture
      every checked-in suite + the replay-determinism test loads.
      Adding new chunks would re-roll the recall and answer
      metrics against the new chunk set, which would invalidate
      the canonical run record at `run-643dff8f3b9c` and break
      the replay-equivalence chain DEC-EVL-011 installs. Keeping
      the refresh fixture under a separate directory preserves the
      canonical sample as the eval anchor.
rationale: |
  This DEC amends DEC-EVL-011. The prior DEC installed the
  replay-determinism fixture that locks the canonical sample run
  record into the contract chain. Two gaps remained.

  First gap: the EDGAR refresh path. Spec 0007 requirement
  R-ING-001 already named the production-shape refresh path at
  `python -m src.ingest.run_ingest --refresh-edgar`, but the
  module-level CLI lands generated output at
  `data/generated/edgar_corpus/` which is gitignored. A reviewer
  asking "does the live EDGAR fetch produce real output, and what
  does that output look like?" had to run the refresh against the
  SEC servers themselves. The new `scripts/refresh_sample_corpus.py`
  wrapper commits a small, bounded, post-fetch fixture under
  `data/refreshed_corpus/` (which is not gitignored) so the answer
  to that question lives in the repo. The wrapper is the right
  altitude: it keeps the production-shape pipeline at
  `src/ingest/edgar_refresh.py` untouched, picks the three-CIK
  manifest specific to the fixture goal (NVDA + TSM + AMAT cover
  the fab + foundry + equipment supplier surface), and tops the
  per-CIK chunk count at two so the diff stays reviewable.

  The keyword-overlap ranker on truncation is a small, opinionated
  choice that maps to the fixture's goal. A 10-K's first dozens of
  chunks land on XBRL header metadata that scores zero on
  supplier-risk vocabulary, so the fixture would otherwise commit
  XBRL boilerplate instead of supplier-risk prose. Ranking
  by keyword overlap with `RISK_KEYWORDS` (supplier, foundry,
  concentration, geopolitical, export control, capacity, raw
  materials, etc.) keeps the fixture small and on-topic. The
  ranker fires only at refresh time; the canonical eval corpus
  and the agent's runtime retrieval path are not touched.

  Second gap: adversarial refusal coverage. The existing
  `refusal_cases` suite covers broad out-of-scope queries
  (weather, sports, personal phone numbers) plus a few
  forecasting cases. It does not cover the failure mode where a
  query carries supplier-risk vocabulary, retrieves a top chunk
  above the 0.18 confidence threshold, and the agent paraphrases
  the retrieved chunk into an answer that fabricates a future
  number or a confidential business detail. The new suite adds 10
  cases that target exactly that surface: each query carries
  domain vocabulary (NVIDIA, TSMC, foundry, EUV, supplier,
  capacity), retrieves a non-empty result set, and asks for
  information the filing does not provide.

  The refusal-logic update is paired with the suite. Without the
  new `ADVERSARIAL_PHRASES` branch in `should_refuse`, the agent
  paraphrases a retrieved chunk on most of the 10 cases (only 5
  of 10 refused under the prior logic; the new branch raises that
  to 10 of 10). The phrase list is intentionally narrow so the
  existing `supplier_risk_questions` suite's legitimate queries
  ("What does TSMC say about geopolitical risks?", "Which
  customers does NVIDIA name?") continue to retrieve and answer
  normally. All four pre-existing suites stay green at the same
  scores after the refusal-logic update.

  Reversibility: dropping this DEC means deleting
  `scripts/refresh_sample_corpus.py`, the
  `data/refreshed_corpus/` directory, the
  `eval_suites/adversarial_refusal_precision.yaml` file, the
  matching ledger and run record under `ops/`, the reports under
  `reports/`, the `ADVERSARIAL_PHRASES` set + branch in
  `src/agent/refusal.py`, the new entries in `GATES`,
  `GATE_LABELS`, `_evaluate_suite`, and `_tool_name_for_suite` in
  `src/evals/runner.py`, R-EVL-031..033 in
  `specs/0004-evals-and-thresholds/requirements.md` and the
  matching rows in `traceability.md`, plus this DEC.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/requirements.md
  - kind: spec
    ref: specs/0007-edgar-refresh/requirements.md
  - kind: decision
    ref: decisions/DEC-EVL-011-supplier-risk-replay-determinism-test.md
  - kind: doc
    ref: scripts/refresh_sample_corpus.py
  - kind: doc
    ref: data/refreshed_corpus/chunks.jsonl
  - kind: doc
    ref: data/refreshed_corpus/manifest.json
  - kind: doc
    ref: eval_suites/adversarial_refusal_precision.yaml
  - kind: doc
    ref: src/agent/refusal.py
  - kind: doc
    ref: src/evals/runner.py
  - kind: run
    ref: ops/run-records/run-c63148a1afa2.json
rollback: |
  Delete `scripts/refresh_sample_corpus.py`. Delete the
  `data/refreshed_corpus/` directory. Delete
  `eval_suites/adversarial_refusal_precision.yaml`. Delete
  `ops/run-records/run-c63148a1afa2.json` and
  `ops/event-ledger/run-c63148a1afa2.jsonl`. Delete the matching
  files under `reports/`. Revert the `ADVERSARIAL_PHRASES` set
  and the new refusal branch in `src/agent/refusal.py`. Revert
  the new entries in `GATES`, `GATE_LABELS`, `_evaluate_suite`,
  and `_tool_name_for_suite` in `src/evals/runner.py`. Drop
  R-EVL-031..033 from `specs/0004-evals-and-thresholds/requirements.md`
  and the matching rows from
  `specs/0004-evals-and-thresholds/traceability.md`. Delete this
  DEC.
owner: control.coordinator
systems_map: |
  Two surfaces sharing one repo. The refresh script exposes the
  ingestion path's live-vs-offline-stub dual mode; the adversarial
  refusal suite exposes the refusal logic's domain-vocabulary blind
  spot. The shared mechanism is a deterministic evaluator that fans
  out across both surfaces without re-rolling the canonical eval
  fixture.
transferable_principle: |
  Open one new failure mode at a time and pair the suite with the
  smallest code change that closes the mode; tangling two failure
  modes in one gate hides the dispatch signal a future regression
  needs.
falsification_test: |
  If the adversarial suite scores >= 0.85 on the unmodified refusal
  logic (without the new ADVERSARIAL_PHRASES branch), the claim
  that the new failure mode is distinct from the existing
  refusal-cases coverage is falsified.
adoption_ladder:
  minimum_viable: |
    Ship the 10-case YAML + the ADVERSARIAL_PHRASES branch; gate
    at refusal_precision >= 0.85.
  mid_adoption: |
    Wire the refresh script into a documented operator runbook;
    publish the offline-stub fallback as the default for sandboxed
    CI.
  full_adoption: |
    Expand the adversarial suite past the initial 10 cases as new
    domain-vocabulary failure patterns surface; treat the suite as
    a regression-anchor for any future refusal-logic edit.
  monitoring_signals:
    - refusal_precision trend on the adversarial suite per PR
    - refresh-fixture diff size per refresh run
    - count of new adversarial cases added per quarter
---

## decision

The supplier-risk-rag-agent repo adds a live EDGAR refresh script at
`scripts/refresh_sample_corpus.py` that writes a bounded fixture
under `data/refreshed_corpus/`, plus an adversarial refusal
precision eval suite at
`eval_suites/adversarial_refusal_precision.yaml` with 10 cases that
look in-scope for supplier-risk analysis but ask for information
no SEC filing supplies. The refusal logic in `src/agent/refusal.py`
gains an `ADVERSARIAL_PHRASES` set and a matching branch in
`should_refuse` so the agent refuses those queries instead of
paraphrasing a retrieved chunk into a fabricated answer. The runner
in `src/evals/runner.py` gains entries in `GATES`, `GATE_LABELS`,
`_evaluate_suite`, and `_tool_name_for_suite` for the new suite.
The canonical sample corpus at `data/sample_corpus/` and the
canonical run record at `run-643dff8f3b9c` are not touched.

## alternatives

- Option A (citation depth instead of adversarial refusal):
  rejected because citation depth extends an existing gate's
  coverage and requires labelled gold spans the deterministic
  pipeline does not produce.
- Option B (fixture without the script): rejected because the
  fixture alone is not reproducible.
- Option C (extend `refusal_cases.yaml` in place): rejected
  because tangling two failure modes in one gate hides the
  failure surface a reviewer needs to dispatch on.
- Option D (write the refresh fixture into `data/sample_corpus/`):
  rejected because it would re-roll the canonical eval metrics
  and break the replay-equivalence chain.

## rationale

This DEC amends DEC-EVL-011 and closes two gaps. The first gap is
the EDGAR refresh path: spec 0007 named the refresh requirement
but the generated output landed at a gitignored path, so a
reviewer asking "what does a live fetch produce?" had no checked-
in answer. The new wrapper script keeps the production-shape
pipeline at `src/ingest/edgar_refresh.py` untouched, picks a
three-CIK manifest (NVDA + TSM + AMAT, covering fab + foundry +
equipment), and writes a bounded post-fetch fixture under
`data/refreshed_corpus/`. The keyword-overlap truncation step
keeps the fixture on supplier-risk prose instead of XBRL header
metadata.

The second gap is adversarial refusal coverage. The existing
`refusal_cases` suite covers broad out-of-scope queries; the new
suite covers in-scope-looking queries that retrieve a non-empty
top chunk and tempt the agent into paraphrasing. The paired
refusal-logic update (`ADVERSARIAL_PHRASES` + a new branch in
`should_refuse`) raises refusal precision on the new suite from
5 of 10 to 10 of 10 without affecting any of the other four
suites' scores.

## evidence

- `scripts/refresh_sample_corpus.py` carries the wrapper script
  with the three-CIK manifest, the keyword-overlap truncation,
  and the offline-stub fallback.
- `data/refreshed_corpus/chunks.jsonl` and `manifest.json` carry
  the live-fetch fixture produced against the 2025-2026 filings
  the three CIKs filed before this DEC's date.
- `eval_suites/adversarial_refusal_precision.yaml` carries the 10
  adversarial cases.
- `src/agent/refusal.py` carries the `ADVERSARIAL_PHRASES` set
  and the new branch in `should_refuse`.
- `src/evals/runner.py` carries the new entries in `GATES`,
  `GATE_LABELS`, `_evaluate_suite`, and `_tool_name_for_suite`.
- `ops/run-records/run-c63148a1afa2.json` and
  `ops/event-ledger/run-c63148a1afa2.jsonl` carry the initial
  run-evidence for the new suite. The reports under
  `reports/adversarial_refusal_precision_*.{html,json}` carry
  the same data in the report shape the existing suites use.

## rollback

Delete the script, the fixture directory, the suite YAML, the
matching ledger and run record under `ops/`, the matching reports,
the refusal-logic additions in `src/agent/refusal.py`, and the
runner additions in `src/evals/runner.py`. Drop R-EVL-031..033
from spec 0004 and the matching traceability rows. Delete this
DEC.

## coverage

This DEC resolves the following requirements added to spec 0004:

- `R-EVL-031` The repo ships `scripts/refresh_sample_corpus.py`
  that reads a three-CIK manifest (NVDA, TSM, AMAT), calls
  `refresh_edgar_corpus` with `max_per_cik=1` and
  `filing_types=["10-K", "20-F"]`, truncates each CIK's chunk
  set by keyword overlap with a supplier-risk vocabulary, and
  writes the top two chunks per CIK to
  `data/refreshed_corpus/chunks.jsonl` plus a refresh manifest
  to `data/refreshed_corpus/manifest.json`. The script falls
  back to an offline-stub fixture when the SEC fetch fails; the
  manifest's `source` field records which path produced the
  fixture.
- `R-EVL-032` The repo ships
  `eval_suites/adversarial_refusal_precision.yaml` with 10
  adversarial supplier-risk cases (each marked
  `expected_refusal: true`), and `src/evals/runner.py` carries
  the new suite under the `refusal_precision >= 0.85` gate.
  `src/agent/refusal.py` carries an `ADVERSARIAL_PHRASES` set
  and a new branch in `should_refuse` so the agent refuses
  those queries instead of paraphrasing a retrieved chunk.
- `R-EVL-033` The runner emits a Run record at
  `ops/run-records/run-c63148a1afa2.json` and a ledger at
  `ops/event-ledger/run-c63148a1afa2.jsonl` for the initial
  adversarial refusal run. `scripts/validate_run_evidence.py`
  exits zero against the produced artifacts. Reports at
  `reports/adversarial_refusal_precision_report.html` and
  `reports/adversarial_refusal_precision_metrics.json` carry
  the same data in the report shape the existing suites use.
