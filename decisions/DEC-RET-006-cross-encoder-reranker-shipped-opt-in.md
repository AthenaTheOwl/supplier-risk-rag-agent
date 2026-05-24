---
id: DEC-RET-006-cross-encoder-reranker-shipped-opt-in
spec: specs/0002-retrieval/
requirement: R-RET-004
date: 2026-05-24
status: approved
reversible: true
decision: |
  Amend DEC-RET-004 by recording the production-ship of the
  cross-encoder reranker as opt-in. The wiring promised by DEC-RET-004
  (constructor argument on `HybridRanker`, `--reranker` flag on the
  eval runner) is now exercised end-to-end through a Streamlit sidebar
  checkbox and a graceful-fallback contract on model-load failure.
  The default Streamlit state, the default runner invocation, and the
  default `HybridRanker` constructor all keep the deterministic hybrid
  (60% BM25 + 25% cosine + 15% term overlap) per DEC-RET-001. The
  opt-in path is shippable for workspaces that accept the latency
  tradeoff. This DEC does not replace DEC-RET-004; it amends it by
  naming the ship date, the surface that exposes the switch to a
  user, and the failure-handling posture.
alternatives:
  - label: keep the reranker as a code path with no UI hook
    rejected_because: |
      Deferring the user-flip surface has been the state since
      experiment 01 reverted. Making the path UI-accessible forces
      the design to be honest about the latency tradeoff and gives
      a workspace owner a real switch to test on their corpus
      instead of a code-only knob the eval runner alone could reach.
  - label: ship the reranker as default and revert the hybrid
    rejected_because: |
      DEC-RET-001 measured a faithfulness regression
      (1.000 to 0.933, below the 0.95 gate) on the sample corpus.
      Experiment 02 reproduces the same regression with the same
      magnitude. Default-on inverts the safe state.
  - label: auto-select the reranker by query length or query type
    rejected_because: |
      A black-box selector splits the retrieval contract by a hidden
      rule the user cannot inspect. The opt-in switch keeps the
      latency-versus-recall tradeoff explicit at the call site (UI
      checkbox, runner flag, constructor argument). A future auto-
      select policy can be a separate DEC once there is data to
      tune it on.
  - label: ship the reranker behind an env-var
    rejected_because: |
      DEC-RET-004 already rejected env-var-driven activation because
      it couples retrieval behavior to shell state and breaks the
      determinism property R-RET-002 holds. The same logic applies
      to the user-facing surface: a checkbox plus a runner flag
      makes the choice auditable at the call site.
rationale: |
  DEC-RET-004 named the architectural promise (opt-in via constructor
  and runner flag). Until now the user-facing surface for that promise
  was the eval runner, which is fine for experiments but invisible
  to a workspace user. The Streamlit checkbox makes the switch real:
  a compliance use case that prioritizes recall on a larger ingested
  corpus can flip it and pay the latency cost; the default workspace
  pays nothing.

  The faithfulness gate stays meaningful as the floor. Experiment 02
  measured the same regression as experiment 01 (recall@5 1.000 to
  1.000; faithfulness 1.000 to 0.933; answer_quality 0.920 to 0.880;
  refusal_precision 1.000 unchanged). Recall@5 is saturated on the
  sample corpus, so the reranker has no headroom to claim and its
  reorderings only hurt the downstream verbatim-span verifier. On a
  larger live-EDGAR corpus the saturation goes away; that is the
  follow-up 01b experiment from the original notes, still uncommitted.

  The latency cost is bounded but real. Local CPU measurements:
  hybrid baseline ~0.4 ms per query, cold reranker load ~7.5 s on
  first call (one-time model load), warm reranker per query ~83 ms
  on the sample corpus with a 50-candidate pool. The 150-400 ms range
  the prompt named is plausible on larger or longer chunks. The
  Streamlit caption tells the user about the one-time load and the
  per-query overhead so the tradeoff is visible at the moment of
  choice.

  The graceful-fallback contract matters because the
  sentence-transformers and torch deps live in the `experiments` uv
  group, not in the production set. If a deployed Streamlit build
  does not have the experiments group installed, a checked sidebar
  box must not crash the app. The reranker catches `Exception` at
  `_ensure_loaded`, logs a warning, sets a `_load_failed` flag, and
  rerank() returns the input candidates' top_k unchanged. A second
  failed call short-circuits without retrying the load.
evidence:
  - kind: spec
    ref: specs/0002-retrieval/requirements.md (R-RET-004)
  - kind: decision
    ref: DEC-RET-001-hybrid-bm25-cosine-term-overlap-weighted.md
      (the production default this opt-in wraps)
  - kind: decision
    ref: DEC-RET-004-opt-in-reranker-via-constructor-and-runner-flag.md
      (the architectural promise this DEC amends)
  - kind: doc
    ref: src/retrieval/reranker.py (CrossEncoderReranker with
      graceful-fallback contract)
  - kind: doc
    ref: src/retrieval/ranker.py (HybridRanker reranker + candidate_pool
      composition path)
  - kind: doc
    ref: src/evals/runner.py (--reranker flag, with_reranker JSON field)
  - kind: doc
    ref: app.py (Streamlit sidebar checkbox, load_agent(use_reranker))
  - kind: run
    ref: experiments/02-cross-encoder-opt-in/baseline.json (hybrid-only A
      side of the A/B)
  - kind: run
    ref: experiments/02-cross-encoder-opt-in/metrics.json (reranker-on B
      side; reproduces the 01 regression on the same sample corpus)
  - kind: postmortem
    ref: experiments/02-cross-encoder-opt-in/notes.md (the comparison
      writeup and the ship-as-opt-in decision)
  - kind: doc
    ref: tests/test_cross_encoder.py (five mocked tests covering shape,
      lazy load, empty input, fallback, end-to-end)
rollback: |
  Remove the user-facing surface and the test in a single revert:
  drop the Streamlit checkbox block in `app.py` (revert the
  `use_reranker` argument on `load_agent` back to a no-arg signature),
  drop the `with_reranker` field from the runner's JSON config block,
  delete `experiments/02-cross-encoder-opt-in/`, and delete
  `tests/test_cross_encoder.py`. The graceful-fallback edit in
  `src/retrieval/reranker.py` can stay; it strictly broadens the
  safe-state contract. The `HybridRanker` constructor arguments and
  the eval runner's `--reranker` flag belong to DEC-RET-004 and
  remain in place after a DEC-RET-006 rollback.

  To go further and remove the opt-in surface entirely, follow the
  rollback path in DEC-RET-004 (delete `src/retrieval/reranker.py`
  and drop the constructor kwargs). To make the reranker the default
  instead, see DEC-RET-001's rollback note; the 0.95 faithfulness
  gate would block the switch on the current sample corpus.
owner: engineering.implementation
---

## decision

Amend DEC-RET-004 by recording the production-ship of the
cross-encoder reranker as opt-in. The wiring is now exercised
end-to-end through a Streamlit sidebar checkbox and a
graceful-fallback contract on model-load failure. The default
Streamlit state, the default runner invocation, and the default
`HybridRanker` constructor all keep the deterministic hybrid per
DEC-RET-001. The opt-in path is shippable for workspaces that
accept the latency tradeoff.

## alternatives

- Keep the reranker as a code path with no UI hook — defers the
  user-flip surface that has been pending since experiment 01.
- Ship the reranker as default and revert the hybrid — rejected by
  the faithfulness gate; the regression reproduced in experiment 02.
- Auto-select the reranker by a hidden rule — black-box behavior;
  the opt-in switch keeps the tradeoff explicit at the call site.
- Env-var activation — rejected by DEC-RET-004 already (couples
  retrieval behavior to shell state).

## rationale

The architectural promise in DEC-RET-004 has been pending. Experiment
02 reproduces the same regression that experiment 01 measured
(recall@5 saturated; faithfulness 1.000 to 0.933 below the 0.95 gate;
answer_quality 0.920 to 0.880; refusal_precision unchanged). The
saturation is corpus-dependent; the larger live-EDGAR corpus the 01b
follow-up targets may move the numbers. The opt-in shape lets a
workspace owner test that on their corpus without re-implementing
the integration. The Streamlit caption surfaces the latency cost
(~7.5 s one-time cold load, ~80 ms warm overhead per query on the
sample corpus) at the moment the user flips the switch. The
graceful-fallback contract guarantees a checked sidebar box cannot
crash the app on a deploy that does not have the experiments group
installed.

## evidence

- `src/retrieval/reranker.py` — the graceful-fallback contract.
- `src/retrieval/ranker.py` — the composition path for the reranker.
- `src/evals/runner.py` — the `--reranker` flag and the
  `with_reranker` JSON config field.
- `app.py` — the Streamlit sidebar checkbox.
- `tests/test_cross_encoder.py` — the five mocked tests.
- `experiments/02-cross-encoder-opt-in/baseline.json` and
  `metrics.json` — the A/B numbers.
- `experiments/02-cross-encoder-opt-in/notes.md` — the comparison
  writeup.
- `DEC-RET-001`, `DEC-RET-004` — the production default and the
  opt-in promise this DEC amends.

## rollback

Remove the user-facing surface in a single revert: drop the
Streamlit checkbox, drop the `with_reranker` JSON field, delete
the experiment folder, delete the test file. The
graceful-fallback edit can stay; it broadens the safe-state contract
either way. The `HybridRanker` constructor kwargs and the
`--reranker` runner flag belong to DEC-RET-004 and survive a
DEC-RET-006 rollback.
