"""
Boses MCP Server — SSE transport
Run with: uvicorn mcp_server.main:app --host 0.0.0.0 --port 8001
"""
import logging

from mcp_server.tools import mcp  # registers all tools via decorators
from mcp_server.config import BOSES_API_KEY, BOSES_API_URL, MCP_PORT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

if not BOSES_API_KEY:
    logger.warning(
        "BOSES_API_KEY is not set — all tool calls will be rejected by the backend. "
        "Generate a key in Boses Settings → API Keys and set BOSES_API_KEY in your environment."
    )

logger.info(f"Boses MCP server configured — backend: {BOSES_API_URL}, port: {MCP_PORT}")

# FastMCP exposes a Starlette app via .sse_app() for SSE transport
app = mcp.sse_app()
