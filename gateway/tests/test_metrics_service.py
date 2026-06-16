"""Tests for MetricsService counter / snapshot behavior."""
from __future__ import annotations

import asyncio

from gateway.app.services.metrics_service import LatencySummary, MetricsService


def test_latency_summary_empty() -> None:
    summary = LatencySummary()
    s = summary.summary()
    assert s["count"] == 0
    assert s["avg_ms"] == 0.0


def test_latency_summary_records() -> None:
    summary = LatencySummary()
    for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
        summary.record(v)
    s = summary.summary()
    assert s["count"] == 5
    assert s["avg_ms"] == 3.0
    assert s["p50_ms"] == 3.0
    # With the discrete index formula int((n-1) * p) -> int(3.8) = 3, p95 = 4.0
    assert s["p95_ms"] == 4.0


def test_metrics_incr_and_snapshot() -> None:
    svc = MetricsService()
    svc.incr("foo")
    svc.incr("foo")
    svc.incr("bar", value=5)
    svc.record_latency("op", 1.5)
    snap = svc.snapshot()
    assert snap["counters"]["foo"] == 2
    assert snap["counters"]["bar"] == 5
    assert snap["latencies"]["op"]["count"] == 1
    assert snap["uptime_seconds"] >= 0


def test_metrics_start_stop_no_db() -> None:
    svc = MetricsService()
    asyncio.run(svc.start())
    svc.incr("test")
    asyncio.run(svc.stop())
