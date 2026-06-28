"""Device status history repository functions."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DeviceStatusHistory


async def record_status_history(
    session: AsyncSession,
    *,
    time: datetime,
    device_id: str,
    status: str,
    firmware_version: str | None,
    ip_address: str | None,
    rssi_dbm: float | None,
    metadata: dict[str, Any] | None,
) -> None:
    session.add(
        DeviceStatusHistory(
            time=time,
            device_id=device_id,
            status=status,
            firmware_version=firmware_version,
            ip_address=ip_address,
            rssi_dbm=rssi_dbm,
            status_metadata=metadata,
        )
    )


async def device_status_history(
    session: AsyncSession, device_id: str, limit: int = 200
) -> Sequence[DeviceStatusHistory]:
    stmt = (
        select(DeviceStatusHistory)
        .where(DeviceStatusHistory.device_id == device_id)
        .order_by(desc(DeviceStatusHistory.time))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()
