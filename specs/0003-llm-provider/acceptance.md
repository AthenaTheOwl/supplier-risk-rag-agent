# acceptance: llm-provider

## Gates

- `python scripts/voice_lint.py` exits 0 across the new spec files.
- `python scripts/spec_check.py` exits 0 with R-LLM-001 resolved by
  `DEC-LLM-001-provider-abstraction-default-anthropic.md` and
  R-LLM-002..003 listed under `deferred:` in the allowlist.
- `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean against `decision.schema.json`.
- `uv run pytest --cov=src --cov-fail-under=70` stays green.

## Done means

Spec 0003 is done when:

1. The six ledger files land under `specs/0003-llm-provider/`.
2. `DEC-LLM-001-*.md` lands under `decisions/`.
3. R-LLM-002 and R-LLM-003 land under `deferred:` in the allowlist
   with one-line notes.
4. `src/agent/llm.py` and `src/config.py` are unchanged by this spec.

## Explicit non-acceptance

- No edits to `src/agent/llm.py` or `src/config.py`.
- No new vendor SDK added. The two supported providers stay
  Anthropic (default) and OpenAI (switchable).
- No move to a framework (LangChain, LlamaIndex, etc.). The
  abstraction stays at the two-helper-method shape.
