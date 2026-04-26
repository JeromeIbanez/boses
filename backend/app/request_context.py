"""
Request correlation ID — propagated via ContextVar so every log line
(including background task logs) carries the same request_id as the
originating HTTP request.

Usage:
    from app.request_context import get_request_id, bind_request_id

The middleware in main.py sets it automatically for all incoming requests.
Background tasks should call bind_request_id(request_id) at entry to
inherit the caller's ID.
"""
import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


def bind_request_id(request_id: str | None = None) -> str:
    """Set (or generate) the request ID for the current context. Returns the ID."""
    rid = request_id or uuid.uuid4().hex[:12]
    _request_id.set(rid)
    return rid
