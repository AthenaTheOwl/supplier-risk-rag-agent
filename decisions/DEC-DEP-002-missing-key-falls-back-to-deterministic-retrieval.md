---
id: DEC-DEP-002-missing-key-falls-back-to-deterministic-retrieval
spec: specs/0005-deploy-and-secrets/
requirement: R-DEP-002
date: 2026-05-24
status: approved
reversible: true
decision: |
  When a visitor has not pasted an Anthropic key (or the live LLM
  call fails for any reason), the Streamlit app falls back to the
  deterministic cited-answer path. `render_answer` catches
  `MissingKeyError`, sets `use_live_llm = False`, and runs the local
  cited-answer path. The user-facing message names the fallback
  explicitly ("Showing deterministic retrieval preview without a live
  LLM call."). A failed live LLM call (rate limit, bad key, network
  error) also falls back to the local cited answer with an error
  message that names the failure mode.
alternatives:
  - label: refuse to answer without a key
    rejected_because: |
      The deployed demo is meant to be exercisable by a visitor
      with no credentials. Refusing without a key turns the demo
      into a paywall and breaks the first-pass exploration flow.
      The deterministic preview shows the cited answer the agent
      composed; the only thing missing is the LLM-paraphrased
      wording on top.
  - label: silently call a platform-paid LLM whenever no visitor key has been pasted
    rejected_because: |
      Platform-paid keys would bill the project owner per visitor
      and would violate the BYOK trust model documented in
      `docs/trust_model.md`. The deployed demo carries no committed
      keys; that is the contract.
  - label: return a generic refusal message
    rejected_because: |
      A generic refusal hides the demo's actual capability. The
      deterministic preview shows the verified citations, the
      retrieved chunks, and the composed answer; a refusal would
      throw away the work the agent already did before the LLM
      rewrite step. The fallback is information, not nothing.
rationale: |
  The agent's deterministic path produces a cited answer without an
  LLM call. The LLM rewrite step polishes the wording but does not
  change the cited spans (the verified spans remain the source of
  truth per DEC-CIT-001). Falling back to the deterministic path on
  a missing key returns the actual answer minus the polished
  wording. That is the right user experience for a no-key demo.

  The fallback message names the trade-off explicitly. A visitor
  reading "Showing deterministic retrieval preview without a live
  LLM call" understands that the citations are real and the answer
  is real, while the wording falls back to the deterministic
  template instead of a paraphrased rewrite. The message is honest about what
  changed and what did not.

  The same fallback path catches live-LLM failures (rate limit, bad
  key, network error). A visitor with a stale Anthropic key sees
  the deterministic preview plus an error message naming the failure
  mode; they can paste a new key and retry. The fallback is the
  resilience story for the deployed demo.
evidence:
  - kind: spec
    ref: specs/0005-deploy-and-secrets/
  - kind: doc
    ref: app.py (`render_answer` `MissingKeyError` catch)
  - kind: doc
    ref: src/config.py (`MissingKeyError` raised by `get_keys`)
  - kind: doc
    ref: src/agent/answerer.py (deterministic cited-answer path)
  - kind: doc
    ref: docs/trust_model.md (BYOK + no platform keys)
rollback: |
  Single-file revert. Remove the `MissingKeyError` catch from
  `render_answer` and let the error bubble up to a Streamlit error
  card. The deployed demo would then fail for any no-key visitor
  with a Python traceback. The cost of rollback is high (visitor
  experience regression); the cost of carrying the fallback is one
  try/except block. Re-run the four-suite eval gate after any change
  to confirm the deterministic path still passes (it should; the
  four suites cover the deterministic path directly).
owner: engineering.implementation
---

## decision

When a visitor has not pasted an Anthropic key (or the live LLM call
fails), the Streamlit app falls back to the deterministic
cited-answer path. `render_answer` catches `MissingKeyError`, sets
`use_live_llm = False`, and runs the local cited-answer path. The
user-facing message names the fallback explicitly.

## alternatives

- Refuse to answer without a key — paywalls the demo.
- Silently call a platform-paid LLM — bills the project owner per
  visitor and violates the BYOK trust model.
- Return a generic refusal — throws away the work the agent already
  did before the LLM rewrite step.

## rationale

The deterministic path produces a cited answer without an LLM call.
The LLM rewrite polishes wording but does not change cited spans.
Falling back to the deterministic path returns the actual answer
minus the polished wording. The fallback message is honest about
what changed. The same path catches live-LLM failures (rate limit,
bad key, network), making the fallback the resilience story too.

## evidence

- `app.py` — `render_answer` catches `MissingKeyError`.
- `src/config.py` — `MissingKeyError` raised by `get_keys`.
- `src/agent/answerer.py` — the deterministic cited-answer path.
- `docs/trust_model.md` — BYOK rule and the no-platform-keys promise.

## rollback

Single-file revert. Remove the `MissingKeyError` catch and let the
error bubble up to a Streamlit error card. The deployed demo would
then fail for any no-key visitor with a traceback.
