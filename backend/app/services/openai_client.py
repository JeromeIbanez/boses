"""Singleton OpenAI client shared across all services.

Using a single client instance reuses the underlying HTTP connection pool
and ensures timeout/retry settings are applied consistently everywhere.
"""
from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=60.0,
            max_retries=3,
        )
    return _client
