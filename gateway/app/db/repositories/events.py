"""Event repository functions."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Event


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
