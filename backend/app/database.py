from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

engine = create_engine(
    settings.database_url_psycopg,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_timeout=10,
    connect_args={"connect_timeout": 10},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_background_db():
    """Context manager for database sessions in background tasks."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
