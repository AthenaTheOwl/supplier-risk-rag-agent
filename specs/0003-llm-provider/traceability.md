# traceability: llm-provider

| Requirement | Design surface | Planned proof | Owner role |
|---|---|---|---|
| R-LLM-001 | `src/agent/llm.py` `LLMClient.__init__` provider check + `complete`/`stream` dispatch | `DEC-LLM-001-provider-abstraction-default-anthropic.md` + Streamlit demo runs against both providers via env var | `engineering.implementation` |
| R-LLM-002 | `src/agent/llm.py` module docstring + every SDK call reading `self.keys.<vendor>_key` | code review confirms no `os.environ` reads in `src/agent/llm.py`; allowlisted under `deferred:` until DEC-LLM-002 lands | `engineering.implementation` |
| R-LLM-003 | `src/config.py` `get_model_config()` reading `LLM_PROVIDER` + `app.py` calling `get_model_config()` without hard-coding a vendor | a workspace operator switches provider by env var and process restart; allowlisted under `deferred:` until DEC-LLM-003 lands | `engineering.implementation` |
