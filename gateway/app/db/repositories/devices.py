"""Device repository functions."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Device


async def upsert_device(
    session: AsyncSession,
    *,
    device_id: str,
    location: str | None = None,
    device_type: str = "energy_node",
    firmware_version: str | None = None,
) -> Device:
    stmt = (
        pg_insert(Device)
        .values(
            device_id=device_id,
            location=location,
            device_type=device_type,
            firmware_version=firmware_version,
            status="unknown",
        )
        .on_conflict_do_update(
            index_elements=[Device.device_id],
            set_={
                "location": func.coalesce(Device.location, Device.location),
                "firmware_version": func.coalesce(
                    Device.firmware_version, Device.firmware_version
                ),
                "updated_at": func.now(),
            },
        )
        .returning(Device)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def update_device_status(
    session: AsyncSession,
    *,
    device_id: str,
    status: str,
    last_seen_at: datetime | None = None,
) -> None:
    device = await session.get(Device, device_id)
    if device is None:
        device = Device(device_id=device_id, status=status)
        session.add(device)
    else:
        device.status = status
    if last_seen_at is not None:
        device.last_seen_at = last_seen_at


async def list_devices(session: AsyncSession, limit: int = 1000) -> Sequence[Device]:
    result = await session.execute(select(Device).order_by(Device.device_id).limit(limit))
    return result.scalars().all()


async def get_device(session: AsyncSession, device_id: str) -> Device | None:
    return await session.get(Device, device_id)
