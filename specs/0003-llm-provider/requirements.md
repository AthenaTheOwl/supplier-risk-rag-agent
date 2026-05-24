# requirements: llm-provider

## Scope

Spec 0003 backfills the LLM provider abstraction under
`src/agent/llm.py`. The agent today supports Anthropic as the default
provider and OpenAI as a switchable alternate, selected at the
workspace level via the `LLM_PROVIDER` env var read in
`src/config.py`. This spec records the requirements that abstraction
answers.

## Requirements

### R-LLM-001: provider abstraction selects Anthropic or OpenAI per workspace

WHEN a caller constructs an `LLMClient`, THE SYSTEM SHALL accept a
`ModelConfig` whose `provider` field selects Anthropic (default) or
OpenAI, and route `complete` and `stream` to the matching SDK.

Acceptance:
- `src/agent/llm.py` carries an `LLMClient` whose `__init__` raises
  `ValueError` on any provider other than `"anthropic"` or
  `"openai"`.
- `complete` and `stream` each dispatch on `self.config.provider` and
  call the matching vendor SDK.
- `src/config.py` reads `LLM_PROVIDER` from the environment with a
  default of `anthropic`.

### R-LLM-002: provider keys never leak into module-level globals

WHEN the agent code calls the LLM, THE SYSTEM SHALL pass the API key
in via an explicit `Keys` object held by `LLMClient`, and SHALL NOT
read environment variables inside `src/agent/llm.py`.

Acceptance:
- The docstring at the top of `src/agent/llm.py` names the rule
  ("This module never reads environment variables").
- The Anthropic and OpenAI client constructors receive
  `self.keys.anthropic_key` or `self.keys.openai_key` directly.
- An OpenAI-routed call with a missing `openai_key` raises a
  `ValueError` whose message names the OpenAI provider and the
  required key, before any network call.

### R-LLM-003: provider selection is reversible without code edits

WHEN a workspace operator wants to switch provider, THE SYSTEM SHALL
support the switch through an env var change plus a deploy restart,
with no code edit required.

Acceptance:
- `LLM_PROVIDER=openai` (with a matching `OPENAI_MODEL`) switches the
  default `ModelConfig` to the OpenAI provider on the next process
  start.
- The default Anthropic model is `claude-sonnet-4-6`; the default
  OpenAI model is read from `OPENAI_MODEL` with a sensible fallback.
- The Streamlit app reads `ModelConfig` from `get_model_config()`
  without hard-coding either vendor name.
