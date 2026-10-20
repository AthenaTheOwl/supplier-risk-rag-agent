"""Config / keys / provider tests.

DEC requirements exercised: R-LLM-001 (provider abstraction with the
Anthropic default), R-LLM-002 (keys flow via an explicit Keys object,
no env reads), R-LLM-003 (provider switch via env var, no code edits),
R-DEP-001 (BYOK on Streamlit, no committed keys), R-DEP-002 (a missing
key falls back to deterministic retrieval), R-DEP-003 (the Streamlit
local-env gate guards dotenv loading).
"""

import json
from pathlib import Path

import pytest

from src import config as config_module
from src.config import (
    DEFAULT_ANTHROPIC_MODEL,
    MissingKeyError,
    ModelConfig,
    get_cli_model_config,
    get_keys,
    get_model_config,
)
from src.evals import runner


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


def test_openai_selection_accepts_only_openai_session_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STREAMLIT_LOCAL", raising=False)
    keys = get_keys({"openai_key": "fake-openai"}, provider="openai")
    assert keys.openai_key == "fake-openai"
    assert not keys.anthropic_key
    assert keys.source == "session"
    with pytest.raises(MissingKeyError, match="OpenAI"):
        get_keys({"anthropic_key": "fake-anthropic"}, provider="openai")


def test_openai_env_fallback_keeps_local_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_module, "load_dotenv", lambda **kwargs: None)
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("STREAMLIT_LOCAL", "0")
    with pytest.raises(MissingKeyError, match="OpenAI"):
        get_keys({}, provider="openai")
    monkeypatch.setenv("STREAMLIT_LOCAL", "1")
    keys = get_keys({}, provider="openai")
    assert keys.openai_key == "fake-openai"
    assert not keys.anthropic_key
    assert keys.source == "local-env"


def test_selected_provider_session_does_not_mix_in_local_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STREAMLIT_LOCAL", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-local-openai")
    with pytest.raises(MissingKeyError, match="OpenAI"):
        get_keys({"anthropic_key": "fake-session-anthropic"}, provider="openai")


def test_unknown_provider_fails_without_reading_keys() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_keys({}, provider="unknown")


@pytest.mark.parametrize("local_flag,expected_calls", [("0", 0), ("1", 1)])
def test_model_config_keeps_dotenv_behind_local_gate(
    monkeypatch: pytest.MonkeyPatch, local_flag: str, expected_calls: int,
) -> None:
    calls: list[bool] = []
    monkeypatch.setenv("STREAMLIT_LOCAL", local_flag)
    monkeypatch.setattr(config_module, "load_dotenv", lambda **kwargs: calls.append(True))
    get_model_config()
    assert len(calls) == expected_calls


def _fake_dotenv(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Stand in for a developer `.env` that selects OpenAI."""
    calls: list[bool] = []
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    def load(**kwargs: object) -> None:
        calls.append(True)
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_MODEL", "fake-dotenv-model")

    monkeypatch.setattr(config_module, "load_dotenv", load)
    return calls


def test_streamlit_model_config_ignores_dotenv_without_local_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_dotenv(monkeypatch)
    monkeypatch.delenv("STREAMLIT_LOCAL", raising=False)
    assert get_model_config() == ModelConfig("anthropic", DEFAULT_ANTHROPIC_MODEL)
    assert not calls


def test_cli_model_config_reads_dotenv_without_streamlit_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_dotenv(monkeypatch)
    monkeypatch.delenv("STREAMLIT_LOCAL", raising=False)
    assert get_cli_model_config() == ModelConfig("openai", "fake-dotenv-model")
    assert calls


def test_eval_runner_records_dotenv_model_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _fake_dotenv(monkeypatch)
    monkeypatch.delenv("STREAMLIT_LOCAL", raising=False)
    monkeypatch.setenv(runner.EVENT_LEDGER_ENV, str(tmp_path / "event-ledger"))
    monkeypatch.setenv(runner.RUN_RECORDS_ENV, str(tmp_path / "run-records"))
    metrics = {"refusal_precision": 1.0, "gate_metric": "refusal_precision",
               "threshold": 0.85, "passed": True}
    _, record_path = runner._record_suite_run(
        "refusal_cases", metrics, [], runner.build_parser().parse_args([]),
        started_at="2026-10-19T00:00:00Z", finished_at="2026-10-19T00:00:01Z",
    )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["agent_id"] == "openai:fake-dotenv-model"
