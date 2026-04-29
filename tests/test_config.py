import pytest

from src.config import (
    DEFAULT_ANTHROPIC_MODEL,
    MissingKeyError,
    get_keys,
    get_model_config,
)


def test_get_keys_prefers_session_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STREAMLIT_LOCAL", raising=False)
    keys = get_keys({"anthropic_key": "sk-ant", "openai_key": "sk-openai"})
    assert keys.anthropic_key == "sk-ant"
    assert keys.openai_key == "sk-openai"
    assert keys.source == "session"


def test_get_keys_blocks_env_without_streamlit_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    monkeypatch.setenv("STREAMLIT_LOCAL", "0")
    with pytest.raises(MissingKeyError):
        get_keys({})


def test_get_keys_allows_env_when_streamlit_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("STREAMLIT_LOCAL", "1")
    keys = get_keys({})
    assert keys.anthropic_key == "sk-env"
    assert keys.openai_key == "sk-openai"
    assert keys.source == "local-env"


def test_default_model_is_corrected_anthropic_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert get_model_config().model == DEFAULT_ANTHROPIC_MODEL
