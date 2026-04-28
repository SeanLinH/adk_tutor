"""Centralized config for ADK + local OpenAI-compatible model.

Both Jupyter notebooks and Streamlit apps import from here so that one
.env file controls the whole demo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class Settings:
    api_base: str
    api_key: str
    model_name: str


def load_settings(env_path: Path | str | None = None) -> Settings:
    """Read .env (if present) and return Settings.

    Streamlit apps can also pass overrides from a sidebar by constructing
    Settings(...) directly instead of calling this function.
    """
    target = Path(env_path) if env_path else ENV_FILE
    if target.exists():
        load_dotenv(target, override=False)

    api_base = os.environ.get("OPENAI_API_BASE", "http://localhost:5052/v1")
    api_key = os.environ.get("OPENAI_API_KEY", "test123")
    model_name = os.environ.get("ADK_MODEL_NAME", "openai/gpt-oss-120b")

    os.environ["OPENAI_API_BASE"] = api_base
    os.environ["OPENAI_API_KEY"] = api_key

    return Settings(api_base=api_base, api_key=api_key, model_name=model_name)


_DEFAULT = load_settings()
MODEL_NAME = _DEFAULT.model_name


def get_model(
    model_name: str | None = None,
    settings: Settings | None = None,
) -> LiteLlm:
    """Build a fresh LiteLlm instance bound to the local endpoint.

    A new instance per agent avoids state-sharing issues when several
    agents share one underlying client.
    """
    s = settings or _DEFAULT
    return LiteLlm(
        model=model_name or s.model_name,
        api_base=s.api_base,
        api_key=s.api_key,
    )
