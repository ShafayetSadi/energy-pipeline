"""Background worker for durable alert delivery."""
from __future__ import annotations

import asyncio

from ..config import get_settings
from ..db.repositories import alert_outbox as outbox_repo
from ..db.session import session_scope
from ..logging_config import get_logger
from ..services.alert_service import AlertService

logger = get_logger(__name__)


class AlertOutboxWorker:
    """Polls and delivers alert_outbox rows asynchronously."""

    def __init__(self, *, alert_service: AlertService) -> None:
        self._settings = get_settings()
        self._alert_service = alert_service
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if not self._settings.alert_outbox_enabled:
            return
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception as exc:  # pragma: no cover
                logger.warning("alert_outbox_tick_failed", error=str(exc))
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self._settings.alert_outbox_poll_seconds
                )
            except TimeoutError:
                continue

    async def _tick(self) -> None:
        async with session_scope() as session:
            rows = await outbox_repo.claim_due_alerts(
                session,
                batch_size=self._settings.alert_outbox_batch_size,
            )
        for row in rows:
            await self._process_row(row)

    async def _process_row(self, row) -> None:
        attempts = int(row.attempts) + 1
        try:
            status, response = await self._alert_service.deliver_outbox_message(
                row.channel, row.payload
            )
            async with session_scope() as session:
                await outbox_repo.record_delivery(
                    session,
                    event_id=row.event_id,
                    channel=row.channel,
                    status=status,
                    response=response,
                )
                if status == "ok":
                    await outbox_repo.mark_sent(session, outbox_id=row.outbox_id)
                else:
                    await outbox_repo.mark_failed(
                        session,
                        outbox_id=row.outbox_id,
                        attempts=attempts,
                        error=response or status,
                        max_attempts=self._settings.alert_outbox_max_attempts,
                    )
        except Exception as exc:
            error = f"exception: {exc}"
            async with session_scope() as session:
                await outbox_repo.record_delivery(
                    session,
                    event_id=row.event_id,
                    channel=row.channel,
                    status="error",
                    response=error,
                )
                await outbox_repo.mark_failed(
                    session,
                    outbox_id=row.outbox_id,
                    attempts=attempts,
                    error=error,
                    max_attempts=self._settings.alert_outbox_max_attempts,
                )
