# traceability: llm-provider

| Requirement | Design surface | Decision | Planned proof | Owner role |
|---|---|---|---|---|
| R-LLM-001 | `src/agent/llm.py` `LLMClient.__init__` provider check + `complete`/`stream` dispatch | `DEC-LLM-001-provider-abstraction-default-anthropic.md` | the Streamlit demo runs against both providers via env var | `owner_role: engineering.implementation` |
| R-LLM-002 | `src/agent/llm.py` module docstring + every SDK call reading `self.keys.<vendor>_key` | `DEC-LLM-002-keys-flow-via-explicit-keys-object-no-env-reads.md` | code review confirms no `os.environ` reads in `src/agent/llm.py` | `owner_role: engineering.implementation` |
| R-LLM-003 | `src/config.py` `get_model_config()` reading `LLM_PROVIDER` + `app.py` calling `get_model_config()` without hard-coding a vendor | `DEC-LLM-003-provider-switch-via-env-var-no-code-edits.md` | a workspace operator switches provider by env var and process restart | `owner_role: engineering.implementation` |
