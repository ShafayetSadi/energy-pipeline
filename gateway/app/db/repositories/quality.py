"""Data quality repository functions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DataQualityLog


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
