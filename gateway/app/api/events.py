"""Event endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import repositories as repo
from ..db.session import get_db

router = APIRouter(prefix="/api/v1/events", tags=["events"])


def _event_to_dict(e) -> dict[str, Any]:
    return {
        "event_id": e.event_id,
        "time": e.time.isoformat(),
        "device_id": e.device_id,
        "event_type": e.event_type,
        "severity": e.severity,
        "rule_name": e.rule_name,
        "message": e.message,
        "reading_time": e.reading_time.isoformat() if e.reading_time else None,
        "event_value": e.event_value,
        "threshold_value": e.threshold_value,
        "metadata": e.event_metadata,
        "acknowledged": e.acknowledged,
    }


@router.get("")
async def list_events(
    device_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = await repo.list_events(
        db,
        device_id=device_id,
        event_type=event_type,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return [_event_to_dict(e) for e in rows]


@router.get("/{event_id}")
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    event = await repo.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")
    return _event_to_dict(event)


@router.post("/{event_id}/acknowledge", status_code=status.HTTP_200_OK)
async def acknowledge_event(event_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    ok = await repo.acknowledge_event(db, event_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")
    await db.commit()
    return {"event_id": event_id, "acknowledged": True}
