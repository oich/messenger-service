"""Pytest fixtures for messenger-service backend tests.

Uses a throwaway file-based SQLite DB instead of the production Postgres
setup - database.py already branches on DATABASE_URL.startswith("sqlite")
for exactly this. Env vars must be set before any `app.*` module is
imported, since app.config reads them at import time.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_messenger.db")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest

from app.database import Base, engine, SessionLocal
import app.models  # noqa: F401 - registers all models on Base.metadata


@pytest.fixture(autouse=True)
def db_session():
    """Fresh schema + session per test, so tests never see each other's rows."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
