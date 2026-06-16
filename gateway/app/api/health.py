"""Health, readiness, version endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "edge-gateway"}


@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"db unavailable: {exc}"
        ) from exc
    return {"status": "ready"}


@router.get("/version")
async def version() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "env": settings.app_env,
        "processing_mode": settings.processing_mode,
    }
