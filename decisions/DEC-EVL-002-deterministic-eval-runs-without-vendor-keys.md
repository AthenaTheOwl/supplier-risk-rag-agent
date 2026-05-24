---
id: DEC-EVL-002-deterministic-eval-runs-without-vendor-keys
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-002
date: 2026-05-24
status: approved
reversible: true
decision: |
  Run the four eval suites against the in-memory sample corpus with
  the deterministic `HashingEmbedder`, the BM25 + cosine + overlap
  hybrid ranker, and the verbatim-span verifier. No vendor API key,
  no network egress, no LLM call. A repeat run on the same commit
  produces identical metric numbers. The CI gate runs against this
  deterministic path; live LLM calls are an opt-in path for local
  experiments only.
alternatives:
  - label: run evals against live Anthropic + live OpenAI on every CI run
    rejected_because: |
      Costs scale with PR volume and flake risk scales with API
      availability. Worse, live calls return non-deterministic
      outputs; a flaky test would block merges for reasons orthogonal
      to the code change. The eval suites need to be a stable gate,
      and stable means deterministic on every input.
  - label: run evals only when an API key has been wired up (skip otherwise)
    rejected_because: |
      Skipping silently turns the gate off in CI where no key has
      been wired up. A change that broke the gate would land green
      under "skipped"; the failure mode would only surface when an
      engineer ran the gate locally. The four suites are too
      load-bearing to be opt-in.
  - label: a hash-based mock LLM that returns canned responses
    rejected_because: |
      Hash-based mocks drift from real LLM behavior over time. The
      eval suites already cover retrieval correctness, span
      verification, and refusal classification, all of which can be
      tested deterministically without an LLM mock. The synthesis
      step is the one that needs an LLM; the suites measure the
      pieces around synthesis, which is the right scope.
rationale: |
  CI runs every push and PR. The eval gate must be stable, cheap, and
  network-free; otherwise the gate's pass/fail signal becomes noise.
  Three of the four suites measure properties that do not require
  an LLM at all: retrieval recall@5 walks the ranker, citation
  faithfulness walks the verifier, refusal precision walks the
  refusal classifier. The supplier-risk-questions suite measures the
  deterministic cited-answer path, not the LLM rewrite path.

  The deterministic build also matches the BYOK trust model: the
  deployed Streamlit demo runs the same code path under a visitor
  with no key. The eval gate proves the same path works without a
  key before any deploy ships. A regression in the deterministic
  path is a regression in the user-visible BYOK path; the gate's
  pass/fail directly maps to the BYOK contract.

  Live LLM calls graduate to a separate opt-in path. A future
  experiment that wants to measure end-to-end answer quality with
  the Anthropic rewrite enabled runs locally with a key, lands the
  metrics in `experiments/NN-*/`, and does not gate CI on the run.
evidence:
  - kind: spec
    ref: specs/0004-evals-and-thresholds/
  - kind: doc
    ref: src/evals/runner.py (no LLM imports; deterministic path)
  - kind: doc
    ref: src/retrieval/embedder.py (`HashingEmbedder` deterministic)
  - kind: doc
    ref: src/retrieval/ranker.py (hybrid with no network dependency)
  - kind: doc
    ref: src/retrieval/citations.py (span verifier, no LLM call)
  - kind: doc
    ref: .github/workflows/evals.yml (runs without secrets)
  - kind: benchmark
    ref: eval_suites/retrieval_quality.yaml (recall@5 1.000 deterministic)
rollback: |
  Single-file revert. Add an `--use-live-llm` flag to the runner that
  routes the answerer path through `LLMClient`. The flag would
  default to off, preserving the deterministic CI behavior; turning
  it on locally is a developer choice. The CI workflow stays on the
  default off; flipping CI on would require updating
  `.github/workflows/evals.yml` to set a key, which violates the
  no-secrets rule. Re-run the four-suite gate after any change.
owner: science.proof-gate-runner
---

## decision

Run the four eval suites against the in-memory sample corpus with
the deterministic `HashingEmbedder`, the hybrid ranker, and the
verbatim-span verifier. No vendor API key, no network egress, no LLM
call in CI. A repeat run on the same commit produces identical
metric numbers.

## alternatives

- Live Anthropic + OpenAI on every CI run — costs scale, flake scales,
  outputs are non-deterministic.
- Skip evals when no key has been wired up — silently turns the gate
  off in CI.
- Hash-based mock LLM — drifts from real behavior; the suites already
  cover deterministic-checkable properties.

## rationale

The eval gate must be stable, cheap, and network-free. Three of the
four suites do not need an LLM. The fourth measures the
deterministic cited-answer path. The deterministic build matches the
BYOK trust model: the same path works for a visitor with no key. A
regression in the deterministic path maps directly to the BYOK
contract.

## evidence

- `src/evals/runner.py` — no LLM imports; deterministic path.
- `src/retrieval/embedder.py` — `HashingEmbedder` is deterministic.
- `src/retrieval/ranker.py` — hybrid with no network dependency.
- `src/retrieval/citations.py` — span verifier with no LLM call.
- `.github/workflows/evals.yml` — runs without secrets.

## rollback

Add an opt-in `--use-live-llm` flag to the runner. Default off
preserves CI behavior; turning it on locally is a developer choice.
The CI workflow stays on the default off.
