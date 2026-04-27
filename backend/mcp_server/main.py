"""
Boses MCP Server — Streamable HTTP transport

Each researcher connects with their own API key:
  https://mcp.temujintechnologies.com/mcp   (X-API-Key header)
  https://mcp.temujintechnologies.com/mcp?key=boses_xxx  (query param fallback)

Run locally:
  BOSES_API_URL=http://localhost:8000 uvicorn mcp_server.main:app --port 8001
"""
import logging
import os
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp_server.context import set_api_key
from mcp_server.tools import mcp
from mcp_server.config import BOSES_API_URL, MCP_PORT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

# Sentry — only initialised when SENTRY_DSN is set (production / staging)
_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialised for MCP server")
    except ImportError:
        logger.warning("sentry-sdk not installed — skipping Sentry init")

logger.info(f"Boses MCP server starting — backend: {BOSES_API_URL}, port: {MCP_PORT}")

# Build the MCP Streamable HTTP app first (this creates the session manager lazily)
_mcp_app = mcp.streamable_http_app()


class APIKeyMiddleware:
    """
    Pure ASGI middleware — no response buffering, safe for streaming / SSE.
    FastAPI's BaseHTTPMiddleware buffers responses which breaks Streamable HTTP.
    Accepts: X-API-Key header (preferred) or ?key= query param (Claude Desktop).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            api_key = headers.get(b"x-api-key", b"").decode()
            if not api_key:
                qs = scope.get("query_string", b"").decode()
                for part in qs.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        if k == "key":
                            api_key = v
                            break
            if api_key:
                set_api_key(api_key)
        await self.app(scope, receive, send)


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@asynccontextmanager
async def lifespan(app: Starlette):
    """
    Start the MCP session manager before serving requests.
    streamable_http_app()'s own lifespan is never called when it's mounted
    as a sub-app, so we run it manually here.
    """
    async with mcp.session_manager.run():
        yield


_inner = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/health", health),
        Mount("/", app=_mcp_app),
    ],
)

# Wrap with pure ASGI middleware for API key injection
app = APIKeyMiddleware(_inner)
