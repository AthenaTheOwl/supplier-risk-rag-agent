---
id: DEC-LLM-003-provider-switch-via-env-var-no-code-edits
spec: specs/0003-llm-provider/
requirement: R-LLM-003
date: 2026-05-24
status: approved
reversible: true
decision: |
  Make the active LLM provider reversible at the workspace level
  through a single env var (`LLM_PROVIDER`) plus a deploy restart, with
  no code edit required. `src/config.py` `get_model_config()` reads
  the env var with a default of `anthropic`; an `openai` value
  swaps the default `ModelConfig.model` to the OPENAI default (read
  from `OPENAI_MODEL` with a sensible fallback). The Streamlit app
  reads `ModelConfig` through `get_model_config()` and does not
  hard-code either vendor name.
alternatives:
  - label: provider hard-coded in `app.py`
    rejected_because: |
      A customer or operator who wants to standardize on OpenAI would
      need a code edit on every deploy. Hard-coding also makes the
      provider an implicit choice; the env var makes it explicit and
      auditable from the deploy command alone.
  - label: provider chosen per-request from a sidebar dropdown
    rejected_because: |
      Per-request switching adds a UI surface, a session-state field,
      and a code path that builds two clients per query. The use
      case (workspace-level standardization) does not need per-request
      flexibility, and the dropdown muddies the BYOK message
      ("which key do I paste?").
  - label: provider locked to Anthropic; ship a separate OpenAI fork
    rejected_because: |
      Two forks would diverge on prompt tuning and on the four-suite
      eval gate. A single binary with an env-var switch is one
      surface to test and one surface to release.
rationale: |
  The repo's deploy story has two operators in mind. One: the demo
  visitor who pastes a key and runs against the default Anthropic
  build. Two: a customer who wants to deploy the same code under
  their own OpenAI account. The env var serves the second operator
  without touching the first.

  The default stays Anthropic for the documented reasons in
  DEC-LLM-001: the deployed demo, the example queries, and the
  prompt-caching annotations all assume Claude wording. The OpenAI
  default model comes from `OPENAI_MODEL` to leave room for a
  customer to standardize on whichever OpenAI snapshot their
  procurement signed off on.

  `app.py` reads `ModelConfig` through `get_model_config()`, never
  hard-coding `"anthropic"` or `"openai"`. The Streamlit sidebar
  shows the active provider as read from `ModelConfig.provider`. A
  workspace operator who runs `LLM_PROVIDER=openai OPENAI_MODEL=gpt-4o
  streamlit run app.py` gets the OpenAI build with no source edit.
evidence:
  - kind: spec
    ref: specs/0003-llm-provider/
  - kind: doc
    ref: src/config.py (`get_model_config()` reads `LLM_PROVIDER`)
  - kind: doc
    ref: src/agent/llm.py (dispatches on `self.config.provider`)
  - kind: doc
    ref: app.py (reads `ModelConfig` without hard-coding a vendor)
  - kind: doc
    ref: README.md (model id paragraph; deprecation notice)
rollback: |
  Single-file revert. Hard-code `provider = "anthropic"` in
  `get_model_config()` and remove the env-var read. Drop the
  `_complete_openai` and `_stream_openai` helpers in
  `src/agent/llm.py` along with the dispatch branches. The
  four-suite eval gate runs on deterministic local retrieval and
  catches any prompt-shape regressions a provider change introduces.
  The rollback cost is bounded; the rule has no data lock-in.
owner: engineering.implementation
---

## decision

Make the active LLM provider reversible at the workspace level
through `LLM_PROVIDER` (default `anthropic`) plus a deploy restart,
with no code edit required. `src/config.py` reads the env var; the
Streamlit app reads `ModelConfig` through `get_model_config()` and
does not hard-code a vendor name.

## alternatives

- Hard-code the provider in `app.py` — forces a code edit on every
  customer deploy and makes the choice implicit.
- Per-request switch via sidebar dropdown — adds UI surface and
  per-query bookkeeping for a use case that wants workspace-level
  standardization.
- Lock to Anthropic; ship an OpenAI fork — two surfaces to test, two
  surfaces to release.

## rationale

The deploy story has two operators: the demo visitor on the default
Anthropic build, and a customer who wants the same code running
against their OpenAI account. The env var serves the second operator
without touching the first. Default Anthropic because the deployed
demo, the example queries, and the prompt-caching annotations all
assume Claude wording (DEC-LLM-001).

## evidence

- `src/config.py` — `get_model_config()` reads `LLM_PROVIDER`.
- `src/agent/llm.py` — dispatches on `self.config.provider`.
- `app.py` — reads `ModelConfig` without hard-coding a vendor.
- `README.md` — documents the model id and the env-var switch.

## rollback

Single-file revert. Hard-code `provider = "anthropic"` in
`get_model_config()` and drop the OpenAI branches. The four-suite
gate catches any prompt-shape regressions a provider change
introduces.
