"""Aggregation worker: periodically refreshes continuous aggregates when
TimescaleDB is available, and prunes old data quality logs.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from ..config import get_settings
from ..db.session import session_scope
from ..logging_config import get_logger

logger = get_logger(__name__)


class AggregationWorker:
    """Refreshes TimescaleDB continuous aggregates and trims old quality logs."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if not self._settings.enable_aggregation:
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
                logger.warning("aggregation_tick_failed", error=str(exc))
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=60.0)
            except TimeoutError:
                continue

    async def _tick(self) -> None:
        await self._refresh_continuous_aggregates()
        await self._prune_quality_logs()

    async def _refresh_continuous_aggregates(self) -> None:
        if not self._settings.enable_timescale:
            return
        async with session_scope() as session:
            try:
                rows = await session.execute(
                    text(
                        """
                        SELECT view_name FROM timescaledb_information.continuous_aggregates
                        """
                    )
                )
                views = [r[0] for r in rows.all()]
            except Exception as exc:
                logger.debug("continuous_aggregates_list_failed", error=str(exc))
                return
            for view in views:
                try:
                    await session.execute(text(f"CALL refresh_continuous_aggregate('{view}', NULL, NULL);"))
                except Exception as exc:
                    logger.debug(
                        "continuous_aggregate_refresh_failed", view=view, error=str(exc)
                    )

    async def _prune_quality_logs(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        async with session_scope() as session:
            try:
                result = await session.execute(
                    text("DELETE FROM data_quality_logs WHERE time < :cutoff"),
                    {"cutoff": cutoff},
                )
                rowcount = getattr(result, "rowcount", 0)
                if rowcount:
                    logger.info("quality_logs_pruned", rows=rowcount)
            except Exception as exc:  # pragma: no cover
                logger.debug("quality_logs_prune_failed", error=str(exc))
