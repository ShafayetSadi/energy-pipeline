"""Energy reading repository functions."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EnergyReading


async def insert_reading(
    session: AsyncSession,
    *,
    time: datetime,
    device_id: str,
    voltage_v: float,
    current_a: float,
    power_w: float,
    temperature_c: float | None,
    sequence_no: int | None,
    raw_payload: dict[str, Any] | None,
) -> bool:
    """Insert a reading using an idempotency check on (time, device_id)."""
    stmt = (
        pg_insert(EnergyReading)
        .values(
            time=time,
            device_id=device_id,
            voltage_v=voltage_v,
            current_a=current_a,
            power_w=power_w,
            temperature_c=temperature_c,
            sequence_no=sequence_no,
            raw_payload=raw_payload,
        )
        .on_conflict_do_nothing(index_elements=[EnergyReading.time, EnergyReading.device_id])
        .returning(EnergyReading.device_id)
    )
    result = await session.execute(stmt)
    return result.first() is not None


async def count_readings(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(EnergyReading))
    return int(result.scalar_one() or 0)


async def latest_reading_for_device(
    session: AsyncSession, device_id: str
) -> EnergyReading | None:
    stmt = (
        select(EnergyReading)
        .where(EnergyReading.device_id == device_id)
        .order_by(desc(EnergyReading.time))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def readings_for_device(
    session: AsyncSession,
    *,
    device_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 1000,
) -> Sequence[EnergyReading]:
    stmt = (
        select(EnergyReading)
        .where(EnergyReading.device_id == device_id)
        .order_by(desc(EnergyReading.time))
        .limit(limit)
    )
    if start_time is not None:
        stmt = stmt.where(EnergyReading.time >= start_time)
    if end_time is not None:
        stmt = stmt.where(EnergyReading.time <= end_time)
    result = await session.execute(stmt)
    return result.scalars().all()


async def readings_aggregate(
    session: AsyncSession,
    *,
    device_id: str,
    start_time: datetime,
    end_time: datetime,
    interval: str = "1 minute",
) -> list[dict[str, Any]]:
    """Return a list of bucketed aggregates using time_bucket()."""
    sql = """
        SELECT
            time_bucket(:interval::interval, time) AS bucket,
            AVG(voltage_v) AS avg_voltage_v,
            AVG(current_a) AS avg_current_a,
            AVG(power_w) AS avg_power_w,
            MAX(power_w) AS max_power_w,
            MIN(voltage_v) AS min_voltage_v,
            COUNT(*) AS sample_count
        FROM energy_readings
        WHERE device_id = :device_id
          AND time >= :start_time
          AND time < :end_time
        GROUP BY bucket
        ORDER BY bucket
    """
    result = await session.execute(
        text(sql),
        {
            "interval": interval,
            "device_id": device_id,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]
