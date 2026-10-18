"""Database connection and session management for PostgreSQL."""

from __future__ import annotations

import os
from typing import Any, Optional

# Hypothetical PostgreSQL Connection URLs
DEFAULT_ASYNC_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentforge_db"
DEFAULT_SYNC_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/agentforge_db"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_ASYNC_DATABASE_URL)
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", DEFAULT_SYNC_DATABASE_URL)

try:
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import declarative_base, sessionmaker

    Base = declarative_base()

    # Async Engine & Session (for FastAPI / LangGraph async tools)
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("DB_ECHO", "False").lower() in ("true", "1"),
        future=True,
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Sync Engine & Session (fallback / migrations / scripts)
    sync_engine = create_engine(
        SYNC_DATABASE_URL,
        echo=os.getenv("DB_ECHO", "False").lower() in ("true", "1"),
        future=True,
    )
    SyncSessionLocal = sessionmaker(
        bind=sync_engine,
        autocommit=False,
        autoflush=False,
    )
    HAS_SQLALCHEMY = True

except ImportError:
    Base = object  # type: ignore
    async_engine = None
    sync_engine = None
    AsyncSessionLocal = None
    SyncSessionLocal = None
    HAS_SQLALCHEMY = False


async def get_async_db():
    """Dependency helper for FastAPI/async routes to yield database session."""
    if not HAS_SQLALCHEMY or AsyncSessionLocal is None:
        raise RuntimeError("SQLAlchemy and asyncpg are required for database operations. Please install them.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
