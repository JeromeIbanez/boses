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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


# Routers registered after models are defined
from app.routers import projects, persona_groups, personas, briefings, simulations  # noqa: E402

app.include_router(projects.router, prefix="/api/v1")
app.include_router(persona_groups.router, prefix="/api/v1")
app.include_router(personas.router, prefix="/api/v1")
app.include_router(briefings.router, prefix="/api/v1")
app.include_router(simulations.router, prefix="/api/v1")
