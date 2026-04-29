"""LLM provider abstraction.

This module never reads environment variables. Callers must pass a Keys object explicitly.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from src.config import Keys, ModelConfig, get_model_config


class LLMClient:
    def __init__(self, keys: Keys, config: ModelConfig | None = None) -> None:
        self.keys = keys
        self.config = config or get_model_config()
        if self.config.provider not in {"anthropic", "openai"}:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        system: str,
        max_tokens: int = 800,
    ) -> str:
        if self.config.provider == "openai":
            return self._complete_openai(messages, system=system, max_tokens=max_tokens)
        return self._complete_anthropic(messages, system=system, max_tokens=max_tokens)

    def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system: str,
        max_tokens: int = 800,
    ) -> Iterable[str]:
        if self.config.provider == "openai":
            yield from self._stream_openai(messages, system=system, max_tokens=max_tokens)
            return
        yield from self._stream_anthropic(messages, system=system, max_tokens=max_tokens)

    def _complete_anthropic(
        self,
        messages: list[dict[str, str]],
        *,
        system: str,
        max_tokens: int,
    ) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.keys.anthropic_key)
        response = client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=_anthropic_messages(messages),
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )

    def _stream_anthropic(
        self,
        messages: list[dict[str, str]],
        *,
        system: str,
        max_tokens: int,
    ) -> Iterator[str]:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.keys.anthropic_key)
        with client.messages.stream(
            model=self.config.model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=_anthropic_messages(messages),
        ) as stream:
            yield from stream.text_stream

    def _complete_openai(
        self,
        messages: list[dict[str, str]],
        *,
        system: str,
        max_tokens: int,
    ) -> str:
        if not self.keys.openai_key:
            raise ValueError("OpenAI key is required for the OpenAI provider.")
        from openai import OpenAI

        client = OpenAI(api_key=self.keys.openai_key)
        response = client.chat.completions.create(
            model=self.config.model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return response.choices[0].message.content or ""

    def _stream_openai(
        self,
        messages: list[dict[str, str]],
        *,
        system: str,
        max_tokens: int,
    ) -> Iterator[str]:
        if not self.keys.openai_key:
            raise ValueError("OpenAI key is required for the OpenAI provider.")
        from openai import OpenAI

        client = OpenAI(api_key=self.keys.openai_key)
        stream = client.chat.completions.create(
            model=self.config.model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, *messages],
            stream=True,
        )
        for event in stream:
            delta = event.choices[0].delta.content
            if delta:
                yield delta


def _anthropic_messages(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        converted.append(
            {
                "role": message["role"],
                "content": [{"type": "text", "text": message["content"]}],
            }
        )
    if converted:
        converted[-1]["content"][0]["cache_control"] = {"type": "ephemeral"}
    return converted
