"""Device endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import repositories as repo
from ..db.session import get_db

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.get("")
async def list_devices(
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    devices = await repo.list_devices(db, limit=limit)
    return [
        {
            "device_id": d.device_id,
            "location": d.location,
            "device_type": d.device_type,
            "firmware_version": d.firmware_version,
            "status": d.status,
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
        }
        for d in devices
    ]


@router.get("/{device_id}")
async def get_device(
    device_id: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    device = await repo.get_device(db, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")
    return {
        "device_id": device.device_id,
        "location": device.location,
        "device_type": device.device_type,
        "firmware_version": device.firmware_version,
        "status": device.status,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
    }


@router.get("/{device_id}/status")
async def get_device_status(
    device_id: str, limit: int = Query(50, ge=1, le=500), db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    history = await repo.device_status_history(db, device_id, limit=limit)
    return [
        {
            "time": h.time.isoformat(),
            "status": h.status,
            "firmware_version": h.firmware_version,
            "ip_address": h.ip_address,
            "rssi_dbm": h.rssi_dbm,
            "metadata": h.status_metadata,
        }
        for h in history
    ]
