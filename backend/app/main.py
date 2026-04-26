import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

class _RequestIdFilter(logging.Filter):
    """Injects request_id from the ContextVar into every log record."""
    def filter(self, record: logging.LogRecord) -> bool:
        from app.request_context import get_request_id
        record.request_id = get_request_id()
        return True


_root_handler = logging.StreamHandler()
_root_handler.addFilter(_RequestIdFilter())
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: [%(name)s] [req:%(request_id)s] %(message)s",
    handlers=[_root_handler],
)

import sentry_sdk
from fastapi import FastAPI, Request
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


async def _cleanup_refresh_tokens() -> None:
    """Periodically delete refresh tokens older than REFRESH_TOKEN_EXPIRE_DAYS + 30 days."""
    while True:
        await asyncio.sleep(24 * 60 * 60)  # run once every 24 hours
        try:
            from app.database import SessionLocal
            from app.models.refresh_token import RefreshToken
            cutoff = datetime.utcnow() - timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS + 30)
            with SessionLocal() as db:
                deleted = db.query(RefreshToken).filter(RefreshToken.created_at < cutoff).delete()
                db.commit()
            if deleted:
                logging.getLogger(__name__).info("Token cleanup: deleted %d expired refresh tokens", deleted)
        except Exception as e:
            logging.getLogger(__name__).error("Token cleanup failed: %s", e)


def _check_grounding_data_staleness() -> None:
    """Warn if grounding_data.json hasn't been updated in over 90 days."""
    import json
    from pathlib import Path
    _log = logging.getLogger(__name__)
    try:
        path = Path(__file__).parent / "data" / "grounding_data.json"
        meta = json.loads(path.read_text()).get("_meta", {})
        last_updated_str = meta.get("last_updated")
        if not last_updated_str:
            _log.warning("grounding_data.json has no _meta.last_updated field")
            return
        last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d")
        age_days = (datetime.utcnow() - last_updated).days
        if age_days > 90:
            msg = (
                f"grounding_data.json is {age_days} days old (last_updated={last_updated_str}). "
                "Run scripts/fetch_world_bank.py and update DataReportal figures."
            )
            _log.warning(msg)
            if settings.SENTRY_DSN:
                sentry_sdk.capture_message(msg, level="warning")
        else:
            _log.info("grounding_data.json is %d days old — OK", age_days)
    except Exception as e:
        _log.error("Failed to check grounding data staleness: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_grounding_data_staleness()
    task = asyncio.create_task(_cleanup_refresh_tokens())
    yield
    task.cancel()


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
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With", "X-API-Key"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Generate a short request ID for every request and propagate it via ContextVar."""
    from app.request_context import bind_request_id
    # Honour an upstream-supplied ID (e.g. from Render's load balancer) if present
    incoming = request.headers.get("X-Request-Id") or request.headers.get("X-Correlation-Id")
    rid = bind_request_id(incoming)
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


# Routers registered after models are defined
from app.routers import projects, persona_groups, personas, briefings, simulations, library, auth, internal, settings as settings_router, share, admin_personas, admin, prediction_outcomes, api_keys  # noqa: E402
from app.routers import simulation_idi, simulation_survey, simulation_conjoint, simulation_reliability  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(persona_groups.router, prefix="/api/v1")
app.include_router(personas.router, prefix="/api/v1")
app.include_router(briefings.router, prefix="/api/v1")
app.include_router(simulations.router, prefix="/api/v1")
app.include_router(simulation_idi.router, prefix="/api/v1")
app.include_router(simulation_survey.router, prefix="/api/v1")
app.include_router(simulation_conjoint.router, prefix="/api/v1")
app.include_router(simulation_reliability.router, prefix="/api/v1")
app.include_router(prediction_outcomes.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(share.router, prefix="/api/v1")
app.include_router(admin_personas.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")

# Ensure uploads/avatars dirs exist before mounting — StaticFiles checks at import time
os.makedirs(os.path.join(settings.UPLOAD_DIR, "avatars"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
