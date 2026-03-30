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

    # Test 1: raw httpx connectivity
    try:
        r = httpx.get("https://api.openai.com", timeout=5)
        reachable = True
        http_status = r.status_code
    except Exception as e:
        reachable = False
        http_status = str(e)

    # Test 2: actual OpenAI SDK call
    try:
        client = OpenAI(api_key=key)
        models = client.models.list()
        sdk_ok = True
        sdk_error = None
    except Exception as e:
        sdk_ok = False
        sdk_error = str(e)

    return {
        "key_set": bool(key),
        "key_prefix": key[:12] + "..." if key else None,
        "httpx_version": httpx.__version__,
        "openai_reachable": reachable,
        "http_status": http_status,
        "sdk_ok": sdk_ok,
        "sdk_error": sdk_error,
    }


# Routers registered after models are defined
from app.routers import projects, persona_groups, personas, briefings, simulations  # noqa: E402

app.include_router(projects.router, prefix="/api/v1")
app.include_router(persona_groups.router, prefix="/api/v1")
app.include_router(personas.router, prefix="/api/v1")
app.include_router(briefings.router, prefix="/api/v1")
app.include_router(simulations.router, prefix="/api/v1")
