# Eval discipline

The single most distinctive thing about this repo is that four
eval suites gate every push and every PR — not just nightly, not
just before release, every change. This note explains the four
suites, the thresholds, the workflow, and the relationship to the
citation verifier and the experiments folder.

## the four suites

Each suite targets a single failure mode. A single failed gate
blocks merge.

| Suite | What it measures | Gate | What a failure means |
|---|---|---|---|
| `retrieval_quality` | recall@5 on 20 query/expected-accession pairs | >= 0.70 | The retriever stopped surfacing the right filings. |
| `citation_faithfulness` | verbatim-span verification across 15 supported questions | >= 0.95 | A cited span did not appear in any retrieved chunk. Hallucinated citation. |
| `supplier_risk_questions` | answer-quality proxy over 25 realistic questions (required terms + expected accessions in citations) | >= 0.80 | The answer dropped the term the question asked about, or cited the wrong filing. |
| `refusal_cases` | refusal precision on 10 out-of-scope queries | >= 0.85 | The agent answered a question it should have refused. |

The suite files live under `eval_suites/`. The runner lives at
`src/evals/runner.py`. CI invokes
`uv run python -m src.evals.runner --suite all` on every push.

## why each gate exists

Each gate was chosen against a known failure mode. Each threshold
was sized against the sample corpus today, with headroom for the
corpus to grow before CI goes red on noise.

- **Retrieval recall** catches a ranker regression. The hybrid
  ranker sits at recall@5 = 1.000 today; the 0.70 floor leaves
  room for a larger corpus to drop without breaking CI, but
  catches a real collapse (e.g., the BM25 normalization broke, or
  the embedder index got corrupted).
- **Citation faithfulness** catches hallucinated citations. The
  verbatim-span verifier (see `src/retrieval/citations.py` and
  [DEC-CIT-001](../decisions/DEC-CIT-001-verbatim-span-verification-post-generation.md))
  is the request-time guardrail; the 0.95 gate is the eval-time
  signal that the verifier is still doing its job. The
  cross-encoder reranker experiment was reverted by this exact
  gate — faithfulness dropped 1.000 to 0.933 because the reranker
  reordered chunks in ways that broke verbatim matching. See
  [experiments/01-cross-encoder-rerank](../experiments/01-cross-encoder-rerank/).
- **Answer quality** catches paraphrased answers that drop the
  term the user asked about. The proxy is deterministic: it
  checks that the required term appears in the answer and that
  the expected accessions are among the citations.
- **Refusal precision** catches an agent that started answering
  out-of-scope questions. The suite is 10 cases covering stock
  prices, weather, personal contact info, private contracts, and
  forward-looking predictions — questions the supplier-risk
  agent should not touch.

## why this gates PRs, not just nightly

A post-merge nightly eval finds regressions after they ship. The
policy
[`.agents/policies/eval-suite-required-before-prompt-change.yaml`](../.agents/policies/eval-suite-required-before-prompt-change.yaml)
requires a pre-merge eval pass for any change that touches the
prompt, the answerer template, the model id, the retrieval
weights, or the verifier rules. The CI wiring at
`.github/workflows/evals.yml` runs the runner on push and PR.
A pre-merge gate makes automated reversion possible: the
cross-encoder reranker did not need a human reviewer to catch
the faithfulness regression — the 0.95 threshold caught it.

The decision context lives in
[DEC-EVL-001](../decisions/DEC-EVL-001-four-suite-eval-gate-with-thresholds.md).
The choice was deliberate over four alternatives: a single
composite gate (hides the failure mode), no gate (would have
shipped the reranker), post-merge only (breaks the policy), and
looser thresholds (breaks automated reversion).

## how a prompt or model change ships

The discipline is the same whether the change is a one-line
prompt edit or a model swap:

1. Make the change on a branch or worktree.
2. Run the suites locally:
   `uv run python -m src.evals.runner --suite all`.
3. If every gate passes at the published threshold, commit and
   open a PR. CI re-runs the gates.
4. If a gate fails, either fix the regression or revert the
   change. Document the result in `experiments/NN-<slug>/` if
   the change was a deliberate experiment, or in the PR
   description if it was a fix attempt.

The runner is deterministic. The four suites run against the
in-memory sample corpus with no vendor key. A repeat run on the
same commit produces identical metric numbers, so a red CI is
never flaky.

## relationship to the citation verifier

The `citation_faithfulness` suite at >= 0.95 sits on top of the
request-time verifier defined in
`src/retrieval/citations.py`. The verifier is the request-time
guardrail: it raises `CitationVerificationError` when a cited
span does not appear verbatim in any retrieved chunk, and the
answerer treats the error as a refusal trigger. The eval suite
is the eval-time signal that the verifier is still wired in and
that the upstream pipeline is still feeding it correctly-shaped
inputs.

The two layers catch different failure windows. The verifier
catches a single bad response before it ships to a live visitor;
the eval suite catches a systematic regression before the
verifier ever gets to fire. The cross-encoder reranker tripped
both: the verifier raised on individual cases, and the eval
suite dropped below the gate. The DEC chain is
[DEC-CIT-001](../decisions/DEC-CIT-001-verbatim-span-verification-post-generation.md)
(the verifier) +
[DEC-EVL-001](../decisions/DEC-EVL-001-four-suite-eval-gate-with-thresholds.md)
(the gate that wraps it).

## the run-experiment-with-revert SKILL

The
[`run-experiment-with-revert`](../.agents/skills/run-experiment-with-revert/SKILL.md)
SKILL codifies the disciplined-experimentation pattern. The
pre-conditions name the four-suite-green-on-trunk requirement.
The steps name the
`experiments/NN-<slug>/{config.yaml,baseline.json,variant.json,notes.md}`
layout. The decision rule names the four gates as a conjunction:
every gate must pass on the variant for the change to ship; a
single failure reverts the variant and keeps the opt-in surface
in tree for a future re-run on a larger corpus.

The reverted cross-encoder experiment is the canonical example.
The variant ran against the four-suite gate, recall@5 was already
saturated at 1.000, the reranker had no headroom to claim,
reordered candidates broke verbatim-span verification, the 0.95
faithfulness gate failed, and the variant was reverted in the
same commit that recorded the result. The opt-in surface
(`--reranker` on the runner, a constructor argument on
`HybridRanker`) stayed in tree — the follow-up `01b` on a larger
live-ingested corpus can re-run without re-implementation.

## the experiments folder convention

Every experiment ships four files:

- `config.yaml` — pre-registered hypothesis section
  (`hypothesis`, `success_criteria`, `revert_criteria`), the
  parameter or model under test, and the exact runner invocation
  for baseline and variant.
- `baseline.json` — runner output with the variant off.
- `variant.json` — runner output with the variant on.
- `notes.md` — opens with the hypothesis paragraph; closes with
  the delta table and the kept-or-reverted decision.

The decision rule lives in `experiments/README.md` and in the
SKILL: ship when a gated metric lifts and no other gate
regresses; revert when any required gate fails. A no-lift
outcome is also a revert, with the postmortem recorded as a
documented dead-end.

## what a future practitioner can copy

Three patterns are repo-portable:

1. **Per-failure-mode suites with named thresholds.** Avoid a
   single composite score. One suite per failure class makes a
   red CI map to a narrow root-cause window.
2. **Pre-merge gates plus a policy file.** The CI workflow at
   `.github/workflows/evals.yml` plus the policy at
   `.agents/policies/eval-suite-required-before-prompt-change.yaml`
   together make the gate enforced and explainable.
3. **Experiments-and-revert as a graduated SKILL.** The
   `run-experiment-with-revert` SKILL captures the workflow as a
   reusable contract; the reverted cross-encoder is the proof
   the gate carries weight.

These three combine into the operating discipline the repo
publishes alongside the demo: a citation-faithful RAG agent
where the eval contract is as legible as the code.
