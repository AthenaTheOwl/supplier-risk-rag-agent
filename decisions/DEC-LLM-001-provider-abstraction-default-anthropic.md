---
id: DEC-LLM-001-provider-abstraction-default-anthropic
spec: specs/0003-llm-provider/
requirement: R-LLM-001
date: 2026-05-24
status: approved
reversible: true
decision: |
  Ship a thin provider abstraction in `src/agent/llm.py` that selects
  Anthropic (default) or OpenAI via the `LLM_PROVIDER` env var read
  in `src/config.py`. The abstraction dispatches `complete` and
  `stream` on `config.provider` and rejects any other provider at
  construction time. The Anthropic path also wires the
  `cache_control` annotation for prompt caching; the OpenAI path
  passes the message list through directly.
alternatives:
  - label: hard-code Anthropic
    rejected_because: |
      Workspace-level vendor switching is a real deployment
      requirement: a customer standardized on OpenAI should not need
      a fork. Hard-coding also bakes in vendor risk (a deprecation
      or pricing change forces a rewrite).
  - label: hard-code OpenAI
    rejected_because: |
      The deployed demo, the example queries, and the prompt-caching
      story are all written around Claude. Hard-coding OpenAI would
      drop the caching annotation and re-do the prompt tuning.
  - label: multi-vendor with model-routing rules (cheap model for
      retrieval, expensive for synthesis)
    rejected_because: |
      Premature. The current usage is one model per call; per-call
      routing adds a config layer, a cost ledger, and a routing
      policy with no measured cost problem to solve. A future spec
      may add routing if usage data justifies it.
  - label: adopt a framework (LangChain, LlamaIndex, Pydantic-AI)
    rejected_because: |
      Frameworks turn over every six months and the abstraction here
      is two helper methods per provider. The framework dependency
      adds churn risk and lock-in for less surface area than the
      hand-written abstraction covers.
rationale: |
  The provider abstraction has two jobs. One: let a workspace switch
  vendor by env var and process restart, without code edits. Two:
  keep the agent module testable by forbidding env reads inside
  `src/agent/llm.py`; keys flow in via an explicit `Keys` object.

  Default Anthropic because the deployed demo, the example queries,
  and the prompt-caching annotations all assume Claude wording. The
  default ships with `claude-sonnet-4-6`; the older snapshot
  `claude-sonnet-4-20250514` is deprecated (retirement planned
  June 15, 2026) and is not the default here.

  The abstraction is small on purpose: two helper methods per
  provider (`_complete_anthropic`, `_stream_anthropic`,
  `_complete_openai`, `_stream_openai`). Removing it later is one
  file edit; the cost of vendor lock-in is higher than the cost of
  carrying the abstraction.
evidence:
  - kind: spec
    ref: specs/0003-llm-provider/
  - kind: doc
    ref: src/agent/llm.py
  - kind: doc
    ref: src/config.py
  - kind: doc
    ref: README.md (model id paragraph; deprecation notice)
  - kind: doc
    ref: app.py (calls `get_model_config()` without hard-coding a vendor)
rollback: |
  Single-file revert. The abstraction lives entirely in
  `src/agent/llm.py`. To drop OpenAI, remove the `_complete_openai`
  and `_stream_openai` methods and the dispatch branch in `complete`
  and `stream`. To drop Anthropic, do the same on the Anthropic
  side. The `Keys` and `ModelConfig` types in `src/config.py` can
  shrink to one provider in a follow-up commit. The four-suite eval
  gate continues to run against deterministic local retrieval and
  catches any prompt-shape regressions a provider change introduces.
owner: engineering.implementation
---

## decision

Ship a thin provider abstraction in `src/agent/llm.py` that selects
Anthropic (default) or OpenAI via the `LLM_PROVIDER` env var read in
`src/config.py`. Dispatch `complete` and `stream` on
`config.provider`; reject any other provider at construction time.

## alternatives

- Hard-code Anthropic — bakes in vendor risk and blocks
  workspace-level switching.
- Hard-code OpenAI — drops the Anthropic prompt-caching annotation
  and forces re-tuning the prompts.
- Multi-vendor model routing — premature; no cost data justifies a
  routing layer today.
- Adopt a framework — framework churn risk for less surface area
  than the hand-written abstraction.

## rationale

Workspace-level vendor switching is a real deployment requirement.
The abstraction is small (two helper methods per provider) and keeps
the agent module testable by forbidding env reads. Default Anthropic
because the deployed demo, the example queries, and the prompt
caching all assume Claude wording. The default model is
`claude-sonnet-4-6`; the older snapshot is deprecated per the
upstream retirement notice.

## evidence

- `src/agent/llm.py` — the dispatch implementation.
- `src/config.py` — the env-reading boundary.
- `README.md` — the model id paragraph and deprecation pointer.
- `app.py` — calls `get_model_config()` without hard-coding a vendor.

## rollback

Single-file revert. The abstraction lives entirely in
`src/agent/llm.py`. To drop one provider, remove the two helper
methods and the dispatch branch. The four-suite eval gate continues
to run on deterministic local retrieval and catches any prompt-shape
regressions.
