import logging
import os
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: [%(name)s] %(message)s",
)

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine
from app.limiter import limiter
from app.models import Base

# Initialise Sentry before the app is created so all errors are captured,
# including startup failures. A missing DSN (local dev) is a no-op.
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,   # 10 % of requests traced — adjust as needed
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Boses API",
    version="1.0.0",
    description=(
        "**Boses** is an AI-powered market simulation platform built for Southeast Asia. "
        "It generates culturally grounded consumer personas (ID, PH, VN) and runs simulated "
        "research studies — concept tests, surveys, focus groups, in-depth interviews, and "
        "conjoint analyses — entirely with AI personas.\n\n"
        "### Authentication\n"
        "All endpoints (except `/health` and `/api/v1/auth/*`) require a JWT bearer token.\n"
        "Obtain one via `POST /api/v1/auth/login`, then pass it as:\n"
        "```\nAuthorization: Bearer <token>\n```\n\n"
        "### Base URL\n"
        "Production: `https://api.temujintechnologies.com`\n\n"
        "Staging: `https://api-staging.temujintechnologies.com`"
    ),
    contact={
        "name": "Temujin Technologies",
        "url": "https://temujintechnologies.com",
        "email": "hello@temujintechnologies.com",
    },
    license_info={
        "name": "Proprietary",
    },
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


# Routers registered after models are defined
from app.routers import projects, persona_groups, personas, briefings, simulations, library, auth, internal  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(persona_groups.router, prefix="/api/v1")
app.include_router(personas.router, prefix="/api/v1")
app.include_router(briefings.router, prefix="/api/v1")
app.include_router(simulations.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")

# Ensure uploads/avatars dirs exist before mounting — StaticFiles checks at import time
os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
