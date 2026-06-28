"""Alert outbox repository functions."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AlertDelivery, AlertOutbox

RETRY_DELAYS = (
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=10),
    timedelta(minutes=30),
)


async def enqueue_alert(
    session: AsyncSession,
    *,
    event_id: int,
    channel: str,
    payload: dict[str, Any],
    now: datetime | None = None,
) -> bool:
    timestamp = now or datetime.now(UTC)
    stmt = (
        pg_insert(AlertOutbox)
        .values(
            event_id=event_id,
            channel=channel,
            payload=payload,
            status="pending",
            attempts=0,
            next_attempt_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
        .on_conflict_do_nothing(index_elements=[AlertOutbox.event_id, AlertOutbox.channel])
        .returning(AlertOutbox.outbox_id)
    )
    result = await session.execute(stmt)
    return result.first() is not None


async def claim_due_alerts(
    session: AsyncSession, *, batch_size: int, now: datetime | None = None
) -> Sequence[AlertOutbox]:
    timestamp = now or datetime.now(UTC)
    claim_sql = text(
        """
        UPDATE alert_outbox
        SET status = 'processing',
            locked_at = :now,
            updated_at = :now
        WHERE outbox_id IN (
            SELECT outbox_id
            FROM alert_outbox
            WHERE status IN ('pending', 'failed')
              AND next_attempt_at <= :now
            ORDER BY next_attempt_at, outbox_id
            LIMIT :batch_size
            FOR UPDATE SKIP LOCKED
        )
        RETURNING outbox_id
        """
    )
    result = await session.execute(
        claim_sql, {"now": timestamp, "batch_size": batch_size}
    )
    ids = [row[0] for row in result.all()]
    if not ids:
        return []
    rows = await session.execute(
        select(AlertOutbox).where(AlertOutbox.outbox_id.in_(ids)).order_by(AlertOutbox.outbox_id)
    )
    return rows.scalars().all()


async def mark_sent(
    session: AsyncSession,
    *,
    outbox_id: int,
    now: datetime | None = None,
) -> None:
    timestamp = now or datetime.now(UTC)
    await session.execute(
        update(AlertOutbox)
        .where(AlertOutbox.outbox_id == outbox_id)
        .values(
            status="sent",
            sent_at=timestamp,
            locked_at=None,
            updated_at=timestamp,
            last_error=None,
        )
    )


async def mark_failed(
    session: AsyncSession,
    *,
    outbox_id: int,
    attempts: int,
    error: str,
    max_attempts: int,
    now: datetime | None = None,
) -> str:
    timestamp = now or datetime.now(UTC)
    if attempts >= max_attempts:
        status = "discarded"
        next_attempt_at = timestamp
    else:
        status = "failed"
        delay = RETRY_DELAYS[min(max(attempts - 1, 0), len(RETRY_DELAYS) - 1)]
        next_attempt_at = timestamp + delay
    await session.execute(
        update(AlertOutbox)
        .where(AlertOutbox.outbox_id == outbox_id)
        .values(
            status=status,
            attempts=attempts,
            next_attempt_at=next_attempt_at,
            locked_at=None,
            updated_at=timestamp,
            last_error=error[:1000],
        )
    )
    return status


async def record_delivery(
    session: AsyncSession,
    *,
    event_id: int,
    channel: str,
    status: str,
    response: str | None,
    now: datetime | None = None,
) -> None:
    session.add(
        AlertDelivery(
            event_id=event_id,
            channel=channel,
            status=status,
            response=response,
            sent_at=now or datetime.now(UTC),
        )
    )
