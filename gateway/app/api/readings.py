"""Reading endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import repositories as repo
from ..db.session import get_db

router = APIRouter(prefix="/api/v1/readings", tags=["readings"])


def _reading_to_dict(r) -> dict[str, Any]:
    return {
        "time": r.time.isoformat(),
        "device_id": r.device_id,
        "voltage_v": r.voltage_v,
        "current_a": r.current_a,
        "power_w": r.power_w,
        "temperature_c": r.temperature_c,
        "sequence_no": r.sequence_no,
    }


@router.get("")
async def list_readings(
    device_id: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(200, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="device_id query parameter is required",
        )
    rows = await repo.readings_for_device(
        db,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return [_reading_to_dict(r) for r in rows]


@router.get("/{device_id}/latest")
async def latest_reading(
    device_id: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    r = await repo.latest_reading_for_device(db, device_id)
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no readings")
    return _reading_to_dict(r)


@router.get("/{device_id}/aggregate")
async def aggregate_readings(
    device_id: str,
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    interval: str = Query("1 minute"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await repo.readings_aggregate(
        db, device_id=device_id, start_time=start_time, end_time=end_time, interval=interval
    )
