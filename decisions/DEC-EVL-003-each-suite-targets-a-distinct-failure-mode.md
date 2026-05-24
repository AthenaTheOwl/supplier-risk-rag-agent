---
id: DEC-EVL-003-each-suite-targets-a-distinct-failure-mode
spec: specs/0004-evals-and-thresholds/
requirement: R-EVL-003
date: 2026-05-24
status: approved
reversible: true
decision: |
  Carve the eval surface into four named suites, each scoped to one
  failure mode of the supplier-risk RAG agent: `retrieval_quality`
  for chunk recall, `citation_faithfulness` for verbatim-span
  verification, `supplier_risk_questions` for end-to-end answer
  composition, and `refusal_cases` for abstention precision. A
  failed suite maps to a narrow class of root cause; a reviewer can
  read the failed suite name and know which subsystem to inspect.
alternatives:
  - label: one big eval suite with mixed cases
    rejected_because: |
      A single suite with mixed retrieval, faithfulness, refusal, and
      end-to-end cases turns a failure into a search problem. The
      reviewer would have to triage which case broke and infer the
      subsystem; the per-suite split makes that mapping mechanical.
  - label: per-test-method suites (one suite per src/ module)
    rejected_because: |
      Code-shaped suites drift with refactors. A failure-mode-shaped
      suite stays stable across code reorganization. The
      `citation_faithfulness` suite would survive a file split or a
      rename of `citations.py`; a `test_citations` suite would not.
  - label: combine `supplier_risk_questions` into `retrieval_quality`
    rejected_because: |
      The end-to-end suite measures answer composition (required
      terms present, expected accessions cited) which is downstream
      of retrieval and would pass-mask a recall regression. The
      separation lets the gate fire on the upstream cause.
rationale: |
  The four failure modes match the four error classes the agent
  produces under real load. The
  retriever can miss chunks (chunk-recall failure). The verifier can
  let a hallucinated span through (faithfulness failure). The
  composed answer can drop a required term or cite the wrong
  accession (composition failure). The refusal classifier can
  paraphrase an out-of-scope question instead of refusing (refusal
  failure). Each suite covers one of these modes and nothing else.

  The mapping pays off when a gate fires. `retrieval_quality` red
  means the ranker is wrong: check `src/retrieval/ranker.py` and
  `src/retrieval/embedder.py`. `citation_faithfulness` red means the
  verifier let a non-verbatim span through: check
  `src/retrieval/citations.py`. `supplier_risk_questions` red means
  the answerer composed wrong text: check `src/agent/answerer.py`.
  `refusal_cases` red means the refusal classifier missed: check
  `src/agent/refusal.py`. The cross-encoder experiment fired
  `citation_faithfulness` specifically; the failure pointed straight
  at the verifier's interaction with reordered candidates.

  Future suites will earn their own slot when a new failure mode
  surfaces. A hypothetical `latency` suite (catch a regression that
  slows answers below an SLA) would graduate as a fifth suite, not
  fold into one of the four.
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
  - kind: postmortem
    ref: experiments/01-cross-encoder-rerank/notes.md (the reranker fired faithfulness, not retrieval)
rollback: |
  Merge any two suites by concatenating their case lists in a single
  YAML and updating the runner to handle the combined case shape.
  The runner reads each suite independently today, so a merge is one
  YAML edit plus one runner constant change. The case shape itself
  is stable across the four suites; concatenation does not break
  parsing. Re-run `--suite all` after any change. Reverting back to
  four suites is the reverse operation.
owner: science.proof-gate-runner
---

## decision

Carve the eval surface into four named suites, each scoped to one
failure mode: `retrieval_quality` for chunk recall,
`citation_faithfulness` for verbatim-span verification,
`supplier_risk_questions` for end-to-end answer composition, and
`refusal_cases` for abstention precision.

## alternatives

- One big eval suite with mixed cases — turns a failure into a
  triage problem.
- Per-module suites (one per `src/` file) — drifts with refactors.
- Fold `supplier_risk_questions` into `retrieval_quality` — the
  composed-answer signal would pass-mask a recall regression.

## rationale

Four named failure modes, four suites, one-to-one mapping. A failed
suite name points the reviewer at the responsible subsystem. The
cross-encoder experiment fired `citation_faithfulness` and the
failure pointed straight at the verifier's interaction with
reordered candidates; the per-suite split made the mapping
mechanical.

## evidence

- The four suite YAMLs under `eval_suites/`.
- `experiments/01-cross-encoder-rerank/notes.md` — the reranker fired
  faithfulness specifically, not retrieval; the per-suite split paid
  off as the gate reported the right failure mode.

## rollback

Merge any two suites by concatenating their YAMLs and updating the
runner to handle the combined case shape. Reverting back is the
reverse operation.
