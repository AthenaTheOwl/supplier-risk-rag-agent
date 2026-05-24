# design: llm-provider

## Shape

```mermaid
flowchart LR
  ENV["env: LLM_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY"] --> CFG["src/config.py: get_keys + get_model_config"]
  CFG --> KEYS["Keys(anthropic_key, openai_key)"]
  CFG --> MC["ModelConfig(provider, model)"]
  KEYS --> CL["LLMClient(keys, config)"]
  MC --> CL
  CL --> ROUTE{"config.provider"}
  ROUTE -- "anthropic (default)" --> ANTH["anthropic.Anthropic(api_key=keys.anthropic_key).messages.create"]
  ROUTE -- "openai" --> OAI["openai.OpenAI(api_key=keys.openai_key).chat.completions.create"]
```

## Modules

### `src/agent/llm.py`

Defines `LLMClient`. Holds a `Keys` and a `ModelConfig`. Provides
`complete(messages, *, system, max_tokens)` and
`stream(messages, *, system, max_tokens)`. Dispatches on
`config.provider` to the matching SDK. The module-level docstring
names the no-env-read rule.

### `src/config.py`

Defines `Keys`, `ModelConfig`, `MissingKeyError`, `get_keys`, and
`get_model_config`. Reads env vars in one place. Streamlit's
`st.session_state` is one accepted source for `get_keys` so the
BYOK sidebar can feed keys without setting env vars.

## Failure modes

- Unknown provider in `ModelConfig.provider`: `LLMClient.__init__`
  raises `ValueError` with the offending provider name.
- OpenAI provider selected without `openai_key`: the OpenAI code
  paths raise `ValueError` before any network call.
- Anthropic SDK call raises (rate limit, bad model): the Streamlit
  app catches at the call site in `app.py` and falls back to the
  local cited answer.

## Why a thin abstraction

The two providers share the message-list shape closely. The
abstraction is small (two helper methods per provider) and avoids a
framework dependency. The cost of removing the abstraction is one
file edit; the cost of vendor lock-in (when a customer mandates the
other provider) is higher.
