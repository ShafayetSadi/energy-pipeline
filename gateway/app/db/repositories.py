"""Async database repositories for all gateway entities."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    DataQualityLog,
    Device,
    DeviceStatusHistory,
    EnergyReading,
    Event,
    RuleDefinition,
)

# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Energy readings
# ---------------------------------------------------------------------------


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
    """Insert a reading using an idempotency check on (time, device_id).

    Returns True if a new row was inserted, False on conflict.
    """
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
    from sqlalchemy import text

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


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


async def insert_event(
    session: AsyncSession,
    *,
    time: datetime,
    device_id: str | None,
    event_type: str,
    severity: str,
    rule_name: str | None,
    message: str | None,
    reading_time: datetime | None,
    event_value: float | None,
    threshold_value: float | None,
    metadata: dict[str, Any] | None,
) -> Event:
    event = Event(
        time=time,
        device_id=device_id,
        event_type=event_type,
        severity=severity,
        rule_name=rule_name,
        message=message,
        reading_time=reading_time,
        event_value=event_value,
        threshold_value=threshold_value,
        event_metadata=metadata,
    )
    session.add(event)
    await session.flush()
    return event


async def list_events(
    session: AsyncSession,
    *,
    device_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 200,
) -> Sequence[Event]:
    stmt = select(Event).order_by(desc(Event.time)).limit(limit)
    if device_id is not None:
        stmt = stmt.where(Event.device_id == device_id)
    if event_type is not None:
        stmt = stmt.where(Event.event_type == event_type)
    if severity is not None:
        stmt = stmt.where(Event.severity == severity)
    if start_time is not None:
        stmt = stmt.where(Event.time >= start_time)
    if end_time is not None:
        stmt = stmt.where(Event.time <= end_time)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_event(session: AsyncSession, event_id: int) -> Event | None:
    return await session.get(Event, event_id)


async def acknowledge_event(session: AsyncSession, event_id: int) -> bool:
    event = await session.get(Event, event_id)
    if event is None:
        return False
    event.acknowledged = True
    return True


async def count_events_by_severity(
    session: AsyncSession, since: datetime | None = None
) -> dict[str, int]:
    stmt = select(Event.severity, func.count()).group_by(Event.severity)
    if since is not None:
        stmt = stmt.where(Event.time >= since)
    result = await session.execute(stmt)
    return {row[0]: int(row[1]) for row in result.all()}


# ---------------------------------------------------------------------------
# Data quality logs
# ---------------------------------------------------------------------------


async def log_data_quality(
    session: AsyncSession,
    *,
    topic: str | None,
    device_id: str | None,
    error_type: str,
    error_message: str | None,
    raw_payload: str | None,
) -> None:
    session.add(
        DataQualityLog(
            topic=topic,
            device_id=device_id,
            error_type=error_type,
            error_message=error_message,
            raw_payload=raw_payload,
        )
    )


async def count_quality_logs_by_type(
    session: AsyncSession, since: datetime | None = None
) -> dict[str, int]:
    stmt = select(DataQualityLog.error_type, func.count()).group_by(
        DataQualityLog.error_type
    )
    if since is not None:
        stmt = stmt.where(DataQualityLog.time >= since)
    result = await session.execute(stmt)
    return {row[0]: int(row[1]) for row in result.all()}


# ---------------------------------------------------------------------------
# Device status history
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


async def upsert_rule_definition(
    session: AsyncSession,
    *,
    rule_name: str,
    enabled: bool,
    event_type: str,
    severity: str,
    config: dict[str, Any],
) -> None:
    stmt = pg_insert(RuleDefinition).values(
        rule_name=rule_name,
        enabled=enabled,
        event_type=event_type,
        severity=severity,
        config=config,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[RuleDefinition.rule_name],
        set_={
            "enabled": stmt.excluded.enabled,
            "event_type": stmt.excluded.event_type,
            "severity": stmt.excluded.severity,
            "config": stmt.excluded.config,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)


async def list_rule_definitions(session: AsyncSession) -> Sequence[RuleDefinition]:
    result = await session.execute(
        select(RuleDefinition).order_by(RuleDefinition.rule_name)
    )
    return result.scalars().all()
