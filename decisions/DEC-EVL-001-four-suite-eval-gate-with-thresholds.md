---
id: DEC-EVL-001-four-suite-eval-gate-with-thresholds
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-001
date: 2026-05-24
status: approved
reversible: true
decision: |
  Ship four named eval suites as a pre-merge gate, each with its own
  non-zero-defect threshold: retrieval_quality at recall@5 >= 0.70,
  citation_faithfulness at faithfulness >= 0.95, refusal_cases at
  refusal_precision >= 0.85, and supplier_risk_questions as a
  per-case answer-quality check (required terms present, expected
  accessions cited). The runner under `src/evals/runner.py` walks
  all four on `--suite all`; `.github/workflows/evals.yml` runs the
  runner on push and PR; a single failed suite blocks merge.
alternatives:
  - label: single composite eval gate (one number)
    rejected_because: |
      A single composite score hides which failure mode regressed.
      The four-suite split maps a failed gate to a narrow class of
      root cause (missing chunks vs hallucinated citations vs dropped
      required terms vs paraphrased refusals). That mapping is the
      whole point of the gate.
  - label: no eval gate (review-only)
    rejected_because: |
      The cross-encoder reranker experiment would have shipped under
      review-only. The reranker reordered chunks in ways that broke
      verbatim-span verification; faithfulness dropped 1.000 to
      0.933. The four-suite gate caught it without a human review
      cycle. Review-only would have shipped the regression.
  - label: post-merge eval only (nightly)
    rejected_because: |
      Bad prompts and bad model swaps would reach main before the
      gate ran. The `.agents/policies/eval-suite-required-before-
      prompt-change.yaml` policy requires a pre-merge eval pass; a
      nightly-only gate breaks the policy.
  - label: looser thresholds (zero-defect off, eyeball deltas)
    rejected_because: |
      Thresholds make automated reversion possible. The cross-encoder
      experiment was reverted automatically by the 0.95 faithfulness
      gate; without a hard threshold, the regression would have
      landed in a reviewer's queue instead of going CI red.
rationale: |
  Prompt and model changes have a known regression risk: any change
  to the system prompt, the answerer template, the model id, the
  retrieval weights, or the verifier rules can shift answer quality
  in a way that is invisible to pytest. Four suites cover four
  distinct failure modes. Each suite has a threshold that holds the
  line against the failure mode it covers.

  Thresholds were chosen against the sample corpus. Recall@5 sits at
  1.000 today across the 20-case suite; the 0.70 floor leaves
  headroom for a larger corpus to drop without breaking CI but
  catches a real recall collapse. Faithfulness at 0.95 is the
  threshold the cross-encoder experiment hit (0.933 < 0.95) and that
  reverted the experiment. Refusal precision at 0.85 leaves room for
  one or two borderline in-scope queries to slip through.

  All four suites run on the in-memory sample corpus with
  deterministic local retrieval and verification. No vendor API key
  is required in CI. A repeat run on the same commit produces
  identical metric numbers, so failures are not flaky.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/
  - kind: doc
    ref: eval_suites/retrieval_quality.yaml
  - kind: doc
    ref: eval_suites/citation_faithfulness.yaml
  - kind: doc
    ref: eval_suites/supplier_risk_questions.yaml
  - kind: doc
    ref: eval_suites/refusal_cases.yaml
  - kind: doc
    ref: src/evals/runner.py
  - kind: doc
    ref: .github/workflows/evals.yml
  - kind: doc
    ref: .agents/policies/eval-suite-required-before-prompt-change.yaml
  - kind: postmortem
    ref: experiments/01-cross-encoder-rerank/notes.md (gate caught the
      faithfulness regression at 0.933 < 0.95)
rollback: |
  Lower thresholds or move evals to nightly. Threshold values live in
  `src/evals/runner.py` (search for the per-suite minimum constants).
  To loosen, edit the constants; to move to nightly only, remove the
  evals job from `.github/workflows/evals.yml` and schedule it from
  a separate workflow. The suites themselves stay in tree as
  reference artifacts even under a nightly-only regime. Re-run
  `uv run python -m src.evals.runner --suite all` after any change.
owner: science.proof-gate-runner
---

## decision

Ship four named eval suites as a pre-merge gate. Each suite has its
own non-zero-defect threshold: retrieval_quality at recall@5 ≥ 0.70,
citation_faithfulness at ≥ 0.95, refusal_cases at refusal_precision
≥ 0.85, and supplier_risk_questions as per-case answer-quality. A
single failed suite blocks merge.

## alternatives

- Single composite gate — hides which failure mode regressed.
- No gate (review-only) — would have shipped the cross-encoder
  faithfulness regression.
- Post-merge only (nightly) — breaks the
  eval-suite-required-before-prompt-change policy.
- Looser thresholds — breaks automated reversion.

## rationale

Four suites cover four distinct failure modes. Each threshold holds
the line against the failure mode it covers. Thresholds were tuned
against the sample corpus; the cross-encoder experiment was reverted
automatically by the 0.95 faithfulness gate, which is direct evidence
the gate carries weight.

## evidence

- The four suite files under `eval_suites/`.
- `src/evals/runner.py` — the runner that computes per-suite metrics.
- `.github/workflows/evals.yml` — the CI wiring.
- `.agents/policies/eval-suite-required-before-prompt-change.yaml` —
  the policy that requires a pre-merge eval pass.
- `experiments/01-cross-encoder-rerank/notes.md` — the reverted
  experiment that the faithfulness gate caught.

## rollback

Lower thresholds or move evals to nightly. The threshold constants
live in `src/evals/runner.py`. Re-run `--suite all` after any change.
The suites stay in tree as reference artifacts even under a
nightly-only regime.
