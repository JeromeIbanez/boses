import os

# URL of the Boses backend API (internal Docker network in prod, localhost in dev)
BOSES_API_URL: str = os.environ.get("BOSES_API_URL", "http://localhost:8000").rstrip("/")

# API key used by the MCP server to call the Boses backend.
# Generate one via the Boses Settings → API Keys page, then set it here.
BOSES_API_KEY: str = os.environ.get("BOSES_API_KEY", "")

# Public-facing base URL for building links back to the Boses web app
BOSES_APP_URL: str = os.environ.get("BOSES_APP_URL", "https://app.temujintechnologies.com")

# Port the MCP server listens on
MCP_PORT: int = int(os.environ.get("MCP_PORT", "8001"))
