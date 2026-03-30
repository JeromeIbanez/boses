import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(title="Boses API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://app.temujintechnologies.com",
        "https://staging.temujintechnologies.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/openai")
def debug_openai():
    import httpx
    from openai import OpenAI
    key = settings.OPENAI_API_KEY

    # Test 1: raw httpx GET to api.openai.com root
    try:
        r = httpx.get("https://api.openai.com", timeout=10)
        reachable = True
        http_status = r.status_code
    except Exception as e:
        reachable = False
        http_status = str(e)

    # Test 2: raw httpx GET to actual models endpoint
    try:
        r2 = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=15,
        )
        raw_api_ok = True
        raw_api_status = r2.status_code
    except Exception as e:
        raw_api_ok = False
        raw_api_status = f"{type(e).__name__}: {str(e)}"

    # Test 3: OpenAI SDK with custom transport (no connection pooling)
    try:
        transport = httpx.HTTPTransport(retries=0)
        http_client = httpx.Client(transport=transport, timeout=30.0)
        client = OpenAI(api_key=key, http_client=http_client, max_retries=0)
        models = client.models.list()
        sdk_ok = True
        sdk_error = None
        sdk_error_type = None
    except Exception as e:
        sdk_ok = False
        sdk_error = str(e)
        sdk_error_type = type(e).__name__
        sdk_cause = type(e.__cause__).__name__ if hasattr(e, "__cause__") and e.__cause__ else None
        sdk_error = f"{sdk_error_type}: {sdk_error} (cause: {sdk_cause})"

    return {
        "key_set": bool(key),
        "key_prefix": key[:12] + "..." if key else None,
        "httpx_version": httpx.__version__,
        "test1_raw_root": {"ok": reachable, "status": http_status},
        "test2_raw_api": {"ok": raw_api_ok, "status": raw_api_status},
        "test3_sdk": {"ok": sdk_ok, "error": sdk_error},
    }


# Routers registered after models are defined
from app.routers import projects, persona_groups, personas, briefings, simulations  # noqa: E402

app.include_router(projects.router, prefix="/api/v1")
app.include_router(persona_groups.router, prefix="/api/v1")
app.include_router(personas.router, prefix="/api/v1")
app.include_router(briefings.router, prefix="/api/v1")
app.include_router(simulations.router, prefix="/api/v1")
