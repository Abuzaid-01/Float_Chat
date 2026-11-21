"""Shared Groq configuration for the query pipeline and the legacy UI."""

import os

from groq import Groq

DEFAULT_MODEL = "openai/gpt-oss-120b"
REQUEST_TIMEOUT_SECONDS = 15.0
MAX_RETRIES = 1


def setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name, default)
    except (ImportError, FileNotFoundError):
        return default
    except Exception as error:
        if type(error).__name__ != "StreamlitSecretNotFoundError":
            raise
        return default


def make_client() -> Groq:
    key = setting("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is required for free-form questions.")
    return Groq(api_key=key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=MAX_RETRIES)
