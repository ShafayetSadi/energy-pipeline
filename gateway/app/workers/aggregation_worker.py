"""Maintenance worker: refreshes continuous aggregates and prunes retained data.
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
    """Refreshes TimescaleDB continuous aggregates and applies retention settings."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if not self._settings.enable_aggregation and not self._settings.retention_enabled:
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
        await self._prune_retained_tables()

    async def _refresh_continuous_aggregates(self) -> None:
        if not self._settings.enable_aggregation or not self._settings.enable_timescale:
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

    def _retention_cutoff(self, days: int) -> datetime | None:
        if not self._settings.retention_enabled or days <= 0:
            return None
        return datetime.now(UTC) - timedelta(days=days)

    async def _prune_retained_tables(self) -> None:
        plans = (
            ("energy_readings", "time", self._settings.retention_raw_readings_days),
            ("data_quality_logs", "time", self._settings.retention_quality_logs_days),
            ("system_metrics", "time", self._settings.retention_system_metrics_days),
            (
                "device_status_history",
                "time",
                self._settings.retention_status_history_days,
            ),
            (
                "alert_deliveries",
                "sent_at",
                self._settings.retention_alert_deliveries_days,
            ),
            (
                "alert_outbox",
                "created_at",
                self._settings.retention_alert_outbox_days,
            ),
        )
        for table, column, days in plans:
            cutoff = self._retention_cutoff(days)
            if cutoff is None:
                continue
            if table == "alert_outbox":
                await self._prune_table(
                    table,
                    column,
                    cutoff,
                    " AND status IN ('sent', 'discarded')",
                )
            else:
                await self._prune_table(table, column, cutoff)

    async def _prune_table(
        self,
        table: str,
        column: str,
        cutoff: datetime,
        extra_where: str = "",
    ) -> None:
        async with session_scope() as session:
            try:
                result = await session.execute(
                    text(f"DELETE FROM {table} WHERE {column} < :cutoff{extra_where}"),
                    {"cutoff": cutoff},
                )
                rowcount = getattr(result, "rowcount", 0)
                if rowcount:
                    logger.info("retention_pruned", table=table, rows=rowcount)
            except Exception as exc:  # pragma: no cover
                logger.debug("retention_prune_failed", table=table, error=str(exc))
