"""
Per-session context for the MCP server.

Each SSE connection carries its own API key (from the X-API-Key header or
?key= query param). We store it in a ContextVar so tool functions can read it
without being passed it explicitly. asyncio propagates ContextVar values through
tasks spawned from the same context, so the key set during the SSE handshake is
available for the entire lifetime of that session.
"""
from contextvars import ContextVar

_api_key: ContextVar[str] = ContextVar("boses_api_key", default="")


def get_api_key() -> str:
    return _api_key.get()


def set_api_key(key: str) -> None:
    _api_key.set(key)
