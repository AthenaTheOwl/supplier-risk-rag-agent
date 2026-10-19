"""The UI distinguishes live evidence ordering from its safe fallbacks."""

from __future__ import annotations

from contextlib import nullcontext

import pytest

import app
from src.agent.answerer import AgentAnswer
from src.config import ModelConfig


class FakeUI:
    def __init__(self) -> None:
        self.session_state = {"openai_key": "fake-session-openai"}
        self.messages: list[tuple[str, str]] = []

    def __getattr__(self, name: str):
        if name == "expander":
            return lambda *args, **kwargs: nullcontext()
        return lambda text="", **kwargs: self.messages.append((name, str(text)))


@pytest.mark.parametrize("mode,channel,marker", [
    ("live_ordered", "success", "Live evidence order accepted"),
    ("live_rejected", "warning", "Live output rejected"),
    ("live_failed", "error", "Live provider fallback"),
    ("deterministic", "caption", "No live provider call was made"),
])
def test_mode_is_visible_and_selected_provider_key_reaches_client(
    monkeypatch: pytest.MonkeyPatch, mode: str, channel: str, marker: str,
) -> None:
    ui = FakeUI()
    client = object()
    calls: list[dict] = []

    class Agent:
        def answer(self, query: str, **kwargs) -> AgentAnswer:
            calls.append(kwargs)
            return AgentAnswer(
                text="Verified local answer.", citations=[], refused=False,
                retrieved_ids=[], confidence=1.0, generation_mode=mode,
                generation_reason="Safe fallback reason." if mode.startswith("live_") else None,
            )

    def client_factory(keys, config):
        assert keys.openai_key == "fake-session-openai"
        assert not keys.anthropic_key
        assert config.provider == "openai"
        return client

    monkeypatch.setattr(app, "st", ui)
    monkeypatch.setattr(app, "load_agent", lambda **kwargs: Agent())
    monkeypatch.setattr(app, "get_model_config", lambda: ModelConfig("openai", "gpt-4o-mini"))
    monkeypatch.setattr(app, "LLMClient", client_factory)
    app.render_answer("A supported supplier-risk question", use_live_llm=True)
    assert calls[0]["use_live_llm"] is True
    assert calls[0]["llm_client"] is client
    assert any(kind == channel and marker in text for kind, text in ui.messages)
