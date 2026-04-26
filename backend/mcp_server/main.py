"""
Boses MCP Server — Streamable HTTP transport

Each researcher connects with their own API key:
  https://mcp.temujintechnologies.com/   (X-API-Key header)
  https://mcp.temujintechnologies.com/?key=boses_xxx  (query param fallback)

Run locally:
  BOSES_API_URL=http://localhost:8000 uvicorn mcp_server.main:app --port 8001
"""
import logging

from fastapi import FastAPI, Request
from mcp_server.context import set_api_key
from mcp_server.tools import mcp
from mcp_server.config import BOSES_API_URL, MCP_PORT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

logger.info(f"Boses MCP server starting — backend: {BOSES_API_URL}, port: {MCP_PORT}")

# Wrap the MCP app with a FastAPI app so we can inject middleware
app = FastAPI(title="Boses MCP Server")


@app.middleware("http")
async def inject_api_key(request: Request, call_next):
    """
    Extract the API key from the incoming request and store it in the
    per-session ContextVar before the MCP handler runs.
    Accepts: X-API-Key header (preferred) or ?key= query param.
    """
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key") or request.query_params.get("key", "")
    if api_key:
        set_api_key(api_key)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


# Mount the MCP Streamable HTTP app at root.
# Streamable HTTP is the modern MCP transport — supports both POST (request/response)
# and GET (SSE streaming), and works correctly through HTTP/2 proxies like Render.
app.mount("/", mcp.streamable_http_app())
