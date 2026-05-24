---
id: DEC-CIT-001-verbatim-span-verification-post-generation
spec: specs/0006-citation-faithfulness/
requirement: R-CIT-001
date: 2026-05-24
status: approved
reversible: true
decision: |
  Run a second-pass post-hoc verifier on every cited span before the
  agent response ships. `verify_citations` in
  `src/retrieval/citations.py` asserts the cited span appears
  verbatim in one of the retrieved chunks, that the recorded offsets
  match the substring, and that the chunk id was in the answerer's
  retrieved set. A failed check raises `CitationVerificationError`;
  the answerer treats the error as a refusal trigger and does not
  ship the unverified claim. The eval suite
  `citation_faithfulness` at threshold >= 0.95 sits on top of this
  verifier.
alternatives:
  - label: trust the model (no verifier)
    rejected_because: |
      Hallucinated citations are the dominant failure mode in
      supplier-risk briefs. A paraphrased citation that looks plausible
      but does not appear verbatim in any retrieved chunk is the exact
      pattern outside reviewers catch first. Trusting the model means
      shipping that failure mode in production responses.
  - label: train a citation classifier
    rejected_because: |
      The substring check is zero-training-cost and deterministic. A
      learned classifier adds a model artifact and a training cycle
      without catching anything the substring check misses on this
      corpus. The classifier would also introduce nondeterminism into
      the citation_faithfulness eval.
  - label: no verification (rely on eval-time checks only)
    rejected_because: |
      The eval gate would catch regressions at PR time but the
      deployed app would still emit unverified citations to live
      visitors between releases. The verifier closes that gap at
      request time, not just at PR time.
  - label: LLM-as-judge faithfulness scoring at request time
    rejected_because: |
      Doubles latency and adds vendor cost per request. The
      substring verifier catches the dominant failure class for free.
      An LLM judge belongs in a follow-up experiment (claim-level
      scoring; see follow-up 04 in
      experiments/01-cross-encoder-rerank/notes.md), not as the
      first line.
rationale: |
  Hallucinated citations are the #1 failure mode in supplier-risk
  briefs. A reviewer reading a brief expects every quoted phrase to
  be findable in the source filing; a paraphrased citation breaks
  that expectation in the most visible way.

  The verifier is the cheapest deterministic guardrail against that
  pattern. It adds a substring search per citation, not another LLM
  call. The latency cost is microseconds; the correctness payoff is
  one failure mode caught at request time, not just at PR time.

  The verifier also catches a second-order failure: a reranker (or
  any future retrieval change) that reorders chunks in ways that
  promote topically-related but non-exact candidates. The reverted
  cross-encoder experiment hit this exact pattern: faithfulness
  dropped 1.000 to 0.933 because the reranker pushed exact-span
  chunks out of the answerer's reach. The verifier surfaced the
  regression at eval time; the 0.95 gate threshold reverted the
  experiment.

  The verifier accepts both raw `DocumentChunk` and SearchResult-like
  inputs (anything exposing a `chunk` attribute) so the answerer
  does not need to unwrap retrieval results before calling it. The
  failure modes (wrong chunk id, out-of-bounds offsets, missing
  substring) each raise a specific message naming the citation
  label, so a failed verification points at the exact citation that
  broke.
evidence:
  - kind: spec
    ref: specs/0006-citation-faithfulness/
  - kind: doc
    ref: src/retrieval/citations.py (verify_citations + Citation +
      citation_from_chunk + CitationVerificationError)
  - kind: doc
    ref: src/agent/answerer.py (call site for verify_citations)
  - kind: doc
    ref: eval_suites/citation_faithfulness.yaml (>= 0.95 gate)
  - kind: decision
    ref: DEC-EVL-001-four-suite-eval-gate-with-thresholds.md (the gate
      that wraps this verifier)
  - kind: postmortem
    ref: experiments/01-cross-encoder-rerank/notes.md (verifier
      caught the reranker faithfulness regression)
rollback: |
  Gate the verifier behind a config flag. Add a boolean
  `verify_citations_enabled` to `ModelConfig` in `src/config.py`,
  default `True`, and let `src/agent/answerer.py` skip the verifier
  when the flag is `False`. Keep the eval suite's verifier path
  unconditional so the regression signal stays intact even if the
  request-time verifier is disabled for a latency experiment.
  Reverting fully is a single-file change to `src/agent/answerer.py`
  (remove the `verify_citations` call). The `citation_faithfulness`
  eval suite still runs against the answerer's output and will fail
  the 0.95 gate if unverified citations ship.
owner: science.proof-gate-runner
---

## decision

Run a post-hoc verifier on every cited span before the agent response
ships. The verifier asserts the cited span appears verbatim in one
of the retrieved chunks, that the offsets line up, and that the
chunk id was in the retrieved set. A failed check raises and the
answerer treats it as a refusal trigger.

## alternatives

- Trust the model — ships the dominant failure mode (hallucinated
  citations) in production responses.
- Train a citation classifier — adds a model artifact and
  nondeterminism for no failure-class the substring check misses.
- Eval-time checks only — leaves a request-time gap between
  releases.
- LLM-as-judge at request time — doubles latency and adds vendor
  cost; belongs in a follow-up experiment, not the first line.

## rationale

Hallucinated citations are the #1 failure mode in supplier-risk
briefs. The substring verifier is the cheapest deterministic
guardrail and catches the failure class at request time. The eval
suite `citation_faithfulness` at ≥ 0.95 sits on top of the
verifier; the cross-encoder experiment was reverted by that gate
when reordered chunks broke verbatim verification.

## evidence

- `src/retrieval/citations.py` — the verifier implementation.
- `src/agent/answerer.py` — the call site.
- `eval_suites/citation_faithfulness.yaml` — the 0.95 gate.
- `DEC-EVL-001-four-suite-eval-gate-with-thresholds.md` — the gate
  that wraps this verifier.
- `experiments/01-cross-encoder-rerank/notes.md` — the reverted
  experiment that confirmed the verifier carries weight.

## rollback

Gate the verifier behind a `verify_citations_enabled` flag on
`ModelConfig`, default `True`. Keep the eval suite's verifier path
unconditional so the regression signal stays intact even if a
latency experiment disables the request-time verifier. Reverting
fully is a one-file change to `src/agent/answerer.py`.
