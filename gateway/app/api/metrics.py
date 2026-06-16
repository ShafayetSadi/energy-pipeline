"""Metrics endpoints exposing counters and event summaries."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import repositories as repo
from ..db.session import get_db

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


def _metrics_snapshot(request: Request) -> dict[str, Any]:
    return request.app.state.metrics.snapshot()


@router.get("/summary")
async def summary(request: Request) -> dict[str, Any]:
    snap = _metrics_snapshot(request)
    return {
        "uptime_seconds": snap["uptime_seconds"],
        "counters": snap["counters"],
        "latencies": snap["latencies"],
    }


@router.get("/latency")
async def latency(request: Request) -> dict[str, Any]:
    snap = _metrics_snapshot(request)
    return {"latencies_ms": snap["latencies"]}


@router.get("/throughput")
async def throughput(request: Request) -> dict[str, Any]:
    snap = _metrics_snapshot(request)
    uptime = max(snap["uptime_seconds"], 1e-9)
    counters = snap["counters"]
    events_total = sum(
        v
        for k, v in counters.items()
        if k.startswith("events.") and not k.startswith("events.type.")
    )
    return {
        "uptime_seconds": snap["uptime_seconds"],
        "messages_per_second": counters.get("messages.received", 0) / uptime,
        "readings_per_second": counters.get("readings.stored", 0) / uptime,
        "events_per_second": events_total / uptime,
    }


@router.get("/data-reduction")
async def data_reduction(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    snap = _metrics_snapshot(request)
    counters = snap["counters"]
    raw_inserted = counters.get("readings.stored", 0)
    event_total = sum(v for k, v in counters.items() if k.startswith("events.type."))
    ratio = 1.0 - (event_total / max(raw_inserted, 1)) if raw_inserted else 0.0
    return {
        "raw_readings_stored": raw_inserted,
        "total_events": event_total,
        "data_reduction_ratio": max(0.0, min(1.0, ratio)),
    }


@router.get("/events-by-severity")
async def events_by_severity(
    hours: int = 24, db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    return await repo.count_events_by_severity(db, since=since)


@router.get("/quality-by-type")
async def quality_by_type(
    hours: int = 24, db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    return await repo.count_quality_logs_by_type(db, since=since)
