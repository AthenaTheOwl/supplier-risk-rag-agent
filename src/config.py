"""Configuration helpers with Streamlit-safe BYOK key handling."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_PROVIDER = "anthropic"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_OPENAI_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class MissingKeyError(RuntimeError):
    """Raised when a required API key is missing."""


@dataclass(frozen=True)
class Keys:
    """API keys supplied explicitly by the caller."""

    anthropic_key: str
    openai_key: str | None = None
    source: str = "session"


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str


def _clean(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _load_local_env_if_allowed() -> None:
    if os.environ.get("STREAMLIT_LOCAL") == "1":
        load_dotenv(override=False)


def get_keys(session_state: Mapping[str, object] | None = None) -> Keys:
    """Resolve keys for Streamlit BYOK.

    Precedence:
    1. Streamlit session state.
    2. Environment variables only when STREAMLIT_LOCAL=1.
    3. MissingKeyError.
    """

    state = session_state or {}
    session_anthropic = _clean(state.get("anthropic_key"))
    session_openai = _clean(state.get("openai_key"))

    if session_anthropic:
        return Keys(
            anthropic_key=session_anthropic,
            openai_key=session_openai or None,
            source="session",
        )

    if session_openai and not session_anthropic:
        raise MissingKeyError("Paste an Anthropic API key to generate cited answers.")

    _load_local_env_if_allowed()
    if os.environ.get("STREAMLIT_LOCAL") == "1":
        env_anthropic = _clean(os.environ.get("ANTHROPIC_API_KEY"))
        env_openai = _clean(os.environ.get("OPENAI_API_KEY"))
        if env_anthropic:
            return Keys(
                anthropic_key=env_anthropic,
                openai_key=env_openai or None,
                source="local-env",
            )

    raise MissingKeyError(
        "Paste your Anthropic API key in the sidebar. Local env fallback is enabled only "
        "when STREAMLIT_LOCAL=1."
    )


def get_cli_keys(
    *,
    require_anthropic: bool = False,
    require_openai: bool = False,
) -> Keys:
    """Resolve keys for local CLI jobs.

    This helper is intentionally separate from Streamlit BYOK. Eval and ingest CLIs may read
    local `.env` files, but the Streamlit app must use `get_keys`.
    """

    load_dotenv(override=False)
    anthropic_key = _clean(os.environ.get("ANTHROPIC_API_KEY"))
    openai_key = _clean(os.environ.get("OPENAI_API_KEY"))

    missing: list[str] = []
    if require_anthropic and not anthropic_key:
        missing.append("ANTHROPIC_API_KEY")
    if require_openai and not openai_key:
        missing.append("OPENAI_API_KEY")
    if missing:
        raise MissingKeyError(f"Missing required local key(s): {', '.join(missing)}")

    return Keys(anthropic_key=anthropic_key, openai_key=openai_key or None, source="cli-env")


def get_model_config() -> ModelConfig:
    """Return configured chat provider and model.

    The default Anthropic model is pinned by the Worker 4 brief. Anthropic's official docs
    identify this as a Sonnet 4 API model name, although current deprecation docs mark it
    deprecated with retirement planned for June 15, 2026.
    """

    load_dotenv(override=False)
    provider = _clean(os.environ.get("LLM_PROVIDER")) or DEFAULT_PROVIDER
    provider = provider.lower()
    configured_model = _clean(os.environ.get("LLM_MODEL"))
    if configured_model:
        model = configured_model
    elif provider == "openai":
        model = DEFAULT_OPENAI_CHAT_MODEL
    else:
        model = DEFAULT_ANTHROPIC_MODEL
    return ModelConfig(provider=provider, model=model)


def sec_user_agent() -> str:
    load_dotenv(override=False)
    return _clean(os.environ.get("SEC_USER_AGENT")) or (
        "AthenaTheOwl supplier-risk-rag (vigneshthegreat@gmail.com)"
    )
