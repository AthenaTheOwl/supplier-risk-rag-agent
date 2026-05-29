"""Config / keys / provider tests.

DEC requirements exercised: R-LLM-001 (provider abstraction with the
Anthropic default), R-LLM-002 (keys flow via an explicit Keys object,
no env reads), R-LLM-003 (provider switch via env var, no code edits),
R-DEP-001 (BYOK on Streamlit, no committed keys), R-DEP-002 (a missing
key falls back to deterministic retrieval), R-DEP-003 (the Streamlit
local-env gate guards dotenv loading).
"""

import pytest

from src.config import (
    DEFAULT_ANTHROPIC_MODEL,
    MissingKeyError,
    get_keys,
    get_model_config,
)


def test_get_keys_prefers_session_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Session-state keys carry through the explicit Keys object.

    Covers: R-LLM-002.
    """
    monkeypatch.delenv("STREAMLIT_LOCAL", raising=False)
    keys = get_keys({"anthropic_key": "sk-ant", "openai_key": "sk-openai"})
    assert keys.anthropic_key == "sk-ant"
    assert keys.openai_key == "sk-openai"
    assert keys.source == "session"


def test_get_keys_blocks_env_without_streamlit_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """No STREAMLIT_LOCAL gate -> env vars are not read; BYOK is required
    and a missing key trips MissingKeyError so the caller can fall back
    to deterministic retrieval.

    Covers: R-DEP-001, R-DEP-002.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    monkeypatch.setenv("STREAMLIT_LOCAL", "0")
    with pytest.raises(MissingKeyError):
        get_keys({})


def test_get_keys_allows_env_when_streamlit_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """STREAMLIT_LOCAL=1 gates dotenv-style env-var loading.

    Covers: R-DEP-003.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("STREAMLIT_LOCAL", "1")
    keys = get_keys({})
    assert keys.anthropic_key == "sk-env"
    assert keys.openai_key == "sk-openai"
    assert keys.source == "local-env"


def test_default_model_is_corrected_anthropic_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """With LLM_PROVIDER / LLM_MODEL unset the provider abstraction
    defaults to Anthropic; setting LLM_PROVIDER swaps providers without
    a code edit.

    Covers: R-LLM-001, R-LLM-003.
    """
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert get_model_config().model == DEFAULT_ANTHROPIC_MODEL
