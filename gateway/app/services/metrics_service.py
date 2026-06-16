"""In-memory metrics with periodic flush to system_metrics table."""
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from ..config import get_settings
from ..db.session import session_scope
from ..logging_config import get_logger

logger = get_logger(__name__)

_SYSTEM_METRICS_INSERT = text(
    """
    INSERT INTO system_metrics (time, metric_name, metric_value, labels, created_at)
    VALUES (:time, :metric_name, :metric_value, CAST(:labels AS JSONB), :created_at)
    """
)


@dataclass
class LatencySummary:
    samples: deque[float] = field(default_factory=lambda: deque(maxlen=10_000))

    def record(self, value_ms: float) -> None:
        self.samples.append(value_ms)

    def summary(self) -> dict[str, float]:
        if not self.samples:
            return {"count": 0, "avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
        ordered = sorted(self.samples)
        n = len(ordered)
        return {
            "count": float(n),
            "avg_ms": sum(ordered) / n,
            "p50_ms": ordered[int((n - 1) * 0.50)],
            "p95_ms": ordered[int((n - 1) * 0.95)],
            "p99_ms": ordered[int((n - 1) * 0.99)],
        }


class MetricsService:
    """Tracks gateway operational metrics for thesis evaluation."""

    def __init__(self) -> None:
        self.started_at = time.monotonic()
        self.counters: dict[str, int] = defaultdict(int)
        self.latencies: dict[str, LatencySummary] = defaultdict(LatencySummary)
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def incr(self, name: str, value: int = 1) -> None:
        self.counters[name] += value

    def record_latency(self, name: str, value_ms: float) -> None:
        self.latencies[name].record(value_ms)

    def snapshot(self) -> dict[str, Any]:
        return {
            "uptime_seconds": time.monotonic() - self.started_at,
            "counters": dict(self.counters),
            "latencies": {k: v.summary() for k, v in self.latencies.items()},
        }

    async def start(self) -> None:
        if self._flush_task is None:
            self._stop.clear()
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self._flush_once()

    async def _flush_loop(self) -> None:
        interval = get_settings().metrics_flush_interval_seconds
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except TimeoutError:
                pass
            if self._stop.is_set():
                break
            try:
                await self._flush_once()
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning("metrics_flush_failed", error=str(exc))

    async def _flush_once(self) -> None:
        snapshot = self.snapshot()
        now = datetime.now(UTC)
        async with self._lock:
            rows = []
            for name, value in snapshot["counters"].items():
                rows.append(
                    {
                        "time": now,
                        "metric_name": f"counter.{name}",
                        "metric_value": float(value),
                        "labels": json.dumps({"kind": "counter", "name": name}),
                        "created_at": now,
                    }
                )
            for name, lat in snapshot["latencies"].items():
                if lat["count"] == 0:
                    continue
                for stat, value in lat.items():
                    if stat == "count":
                        continue
                    rows.append(
                        {
                            "time": now,
                            "metric_name": f"latency.{name}.{stat}",
                            "metric_value": float(value),
                            "labels": json.dumps(
                                {
                                    "kind": "latency",
                                    "operation": name,
                                    "stat": stat,
                                }
                            ),
                            "created_at": now,
                        }
                    )
            if not rows:
                return
            try:
                async with session_scope() as session:
                    await session.execute(_SYSTEM_METRICS_INSERT, rows)
            except Exception as exc:
                logger.warning("metrics_persist_failed", error=str(exc))
