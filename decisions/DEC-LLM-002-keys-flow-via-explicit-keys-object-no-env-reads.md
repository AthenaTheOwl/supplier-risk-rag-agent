---
id: DEC-LLM-002-keys-flow-via-explicit-keys-object-no-env-reads
spec: specs/0003-llm-provider/
requirement: R-LLM-002
date: 2026-05-24
status: approved
reversible: true
decision: |
  Pass API keys into `LLMClient` through an explicit `Keys` object
  held on the client. Forbid environment-variable reads inside
  `src/agent/llm.py`. The module docstring states the rule, the
  Anthropic and OpenAI SDK constructors receive `self.keys.anthropic_key`
  or `self.keys.openai_key` directly, and a missing OpenAI key on an
  OpenAI-routed call raises `ValueError` before any network round trip.
alternatives:
  - label: read keys from environment inside `src/agent/llm.py`
    rejected_because: |
      Hidden env reads make the module untestable in isolation. A test
      that wants to exercise the OpenAI dispatch branch would have to
      monkey-patch `os.environ`, which leaks across tests. Worse, the
      deployed BYOK path stores keys in `st.session_state`, not in env
      vars; an env read here would silently bypass the BYOK contract.
  - label: pass keys as positional arguments to `complete` and `stream`
    rejected_because: |
      Every call site would then need to remember to thread keys
      through. The `Keys` object on the client is one indirection that
      both call sites already pay; promoting it to per-call would
      multiply the surface area without surfacing a new failure mode.
  - label: a thread-local or module-global key registry
    rejected_because: |
      Hides the dependency. A future contributor could not tell, from
      the `LLMClient` signature alone, that a key was required.
      Explicit beats implicit; the `Keys` argument keeps the
      dependency visible.
rationale: |
  The deployed Streamlit demo runs BYOK: visitors paste keys into the
  sidebar, the keys live in `st.session_state` only, and nothing on
  disk or in environment variables holds them. The agent module must
  honor that contract; an `os.environ.get("ANTHROPIC_API_KEY")` inside
  `src/agent/llm.py` would silently pull a deploy-server env var into
  a visitor's request.

  The fail-loud rule on a missing OpenAI key matters because the
  failure mode is invisible otherwise. The Anthropic SDK constructor
  accepts an empty string and only fails on the actual API call;
  raising `ValueError` at construction time with the provider name
  and the required key turns a confusing 401 into a precise error.

  The module docstring at the top of `src/agent/llm.py` carries the
  contract in plain text so a code reviewer or a future agent can
  see the rule without inferring it from the call shape.
evidence:
  - kind: spec
    ref: specs/0003-llm-provider/
  - kind: doc
    ref: src/agent/llm.py (module docstring; never reads environment)
  - kind: doc
    ref: src/config.py (`Keys` dataclass; the explicit carrier)
  - kind: doc
    ref: app.py (`sidebar_keys()` populates `st.session_state`)
  - kind: doc
    ref: .agents/AGENTS.md `## Domain decisions` (BYOK rule)
rollback: |
  Single-file revert. Remove the `keys: Keys` parameter from
  `LLMClient.__init__`, inline `os.environ.get(...)` calls inside the
  `_complete_*` and `_stream_*` helpers, and drop the module
  docstring rule. The BYOK trust model in `docs/trust_model.md` would
  also need a corresponding update; without that, the rollback breaks
  the deploy contract. Re-run `uv run pytest` and the four-suite eval
  gate after any change. The cost of rollback is high; the cost of
  carrying the abstraction is one parameter on one constructor.
owner: engineering.implementation
---

## decision

Pass API keys into `LLMClient` through an explicit `Keys` object held
on the client. Forbid environment-variable reads inside
`src/agent/llm.py`. The Anthropic and OpenAI SDK constructors receive
`self.keys.anthropic_key` or `self.keys.openai_key` directly. A
missing OpenAI key on an OpenAI-routed call raises `ValueError`
before any network round trip.

## alternatives

- Read keys from `os.environ` inside `src/agent/llm.py` — hidden env
  reads make the module untestable and silently bypass the BYOK
  contract.
- Pass keys as positional arguments to `complete` and `stream` — adds
  call-site bookkeeping without a new failure mode.
- Thread-local or module-global key registry — hides the dependency
  and breaks the explicit-is-better rule.

## rationale

The deployed Streamlit demo runs BYOK. Keys live in
`st.session_state` only; nothing on disk or in env vars holds them.
The agent module must honor that contract. The `Keys` object is the
single explicit carrier between the Streamlit sidebar and the SDK
constructor. The early-fail rule on a missing OpenAI key turns an
invisible 401 into a precise construction-time error.

## evidence

- `src/agent/llm.py` — the module docstring states the rule
  ("This module never reads environment variables").
- `src/config.py` — the `Keys` dataclass that carries the keys.
- `app.py` — `sidebar_keys()` populates `st.session_state` with the
  values; `get_keys()` reads them out.
- `.agents/AGENTS.md` `## Domain decisions` — the BYOK paragraph.

## rollback

Single-file revert. Remove the `keys: Keys` parameter from
`LLMClient.__init__`, inline env reads, and drop the docstring rule.
The BYOK trust model documentation would also need an update;
without that, the rollback breaks the deploy contract.
