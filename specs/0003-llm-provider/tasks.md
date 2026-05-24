# tasks: llm-provider

Spec 0003 is a backfill spec. The provider abstraction already
shipped; this ledger records the requirement IDs and pairs the first
one with a DEC.

## Spec ledger

- [x] `specs/0003-llm-provider/requirements.md` with R-LLM-001..003.
- [x] `specs/0003-llm-provider/design.md`.
- [x] `specs/0003-llm-provider/tasks.md` (this file).
- [x] `specs/0003-llm-provider/acceptance.md`.
- [x] `specs/0003-llm-provider/research.md`.
- [x] `specs/0003-llm-provider/traceability.md`.
- [x] `specs/README.md` lists the spec folder.

## Decision coverage

- [x] `decisions/DEC-LLM-001-provider-abstraction-default-anthropic.md`
  resolves R-LLM-001.
- [ ] R-LLM-002 and R-LLM-003 land in
  `decisions/.spec-check-allowlist.yaml` under `deferred:` until a
  backfill pass writes their DECs.

## Code under this spec (already shipped, not changed by this spec)

- `src/agent/llm.py`
- `src/config.py` (the env-reading boundary)

## Verification

- [x] `python scripts/spec_check.py` exits 0 with R-LLM-001 resolved
  and R-LLM-002..003 deferred.
- [x] `python scripts/validate_decisions.py` exits 0 with the new DEC
  parsing clean.
- [x] `uv run pytest --cov=src --cov-fail-under=70` stays green;
  `src/agent/llm.py` is omitted from coverage by the existing
  `pyproject.toml`.
- [x] The Streamlit demo continues to read `get_model_config()` and
  route through `LLMClient` without code edits.
