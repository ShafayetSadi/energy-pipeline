from __future__ import annotations

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/wattflow",
)

engine = create_async_engine(
    DATABASE_URL,
    pool_size=int(os.getenv("DB_POOL_SIZE", "50")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "100")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
    pool_pre_ping=True,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
