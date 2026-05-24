# research: llm-provider

Research checked 2026-05-24.

- The provider abstraction predates CDCP. The repo shipped with both
  Anthropic and OpenAI as message-list-style chat clients; the
  abstraction picked the smaller surface area both vendors share.
- Default is Anthropic. The deployed demo, the Streamlit BYOK flow,
  and the example queries are all written assuming Claude wording.
  OpenAI exists as a switchable alternate for workspaces that
  standardize on it.
- The `LLM_PROVIDER` env var is read in `src/config.py` and nowhere
  else. `src/agent/llm.py` never reads the environment; it accepts a
  `Keys` object and a `ModelConfig` explicitly. This keeps the
  agent module testable without env var manipulation.
- Anthropic prompt caching is wired in via `cache_control`
  annotations on the system block and the last message turn. This is
  Anthropic-specific; the OpenAI code path does not have an
  equivalent caching annotation.

## Why now

- The provider abstraction is one of the load-bearing decisions in
  the repo. The flat `DECISIONS.md` named it in a paragraph; no
  per-requirement DEC existed. The first one (R-LLM-001) earns its
  DEC in this pass.
- The BYOK Streamlit flow depends on the abstraction (workspace
  picks the vendor, visitor pastes the matching key). Naming the
  requirements explicitly closes the contract between the BYOK spec
  (0005) and the provider spec.

## Alternatives considered

- Hard-code Anthropic: rejected. Workspace-level vendor switching is
  a real deployment requirement; a workspace standardized on OpenAI
  should not need a fork.
- Hard-code OpenAI: rejected for the same reason in reverse, and
  because Anthropic prompt caching is part of the cost story.
- Multi-vendor with model-routing rules (cheap model for retrieval,
  expensive model for synthesis): deferred. The current usage is
  one model per call; adding a router belongs to a later spec when
  cost data justifies the complexity.

## Open questions

- Should the OpenAI code path also annotate caching once OpenAI ships
  an equivalent? Open. The abstraction would carry an optional
  `cache_control` flag per provider.
- Does adding Bedrock or Vertex as a third provider warrant a new
  spec? Likely yes; the current `ValueError` on unknown providers is
  the right enforcement until the abstraction is widened.
