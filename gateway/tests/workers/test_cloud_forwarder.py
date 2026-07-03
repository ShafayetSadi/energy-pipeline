"""Tests for the score-gated edge->cloud escalation worker (Phase 2)."""
from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest
from gateway.app.config import Settings
from gateway.app.schemas.telemetry import TelemetryPayload
from gateway.app.services.anomaly_detector import AnomalyResult
from gateway.app.services.metrics_service import MetricsService
from gateway.app.workers.cloud_forwarder import CloudForwarderWorker, EscalationJob


def _telemetry(device_id: str = "house_0001") -> TelemetryPayload:
    return TelemetryPayload(
        schema_version="1.0",
        device_id=device_id,
        timestamp=datetime.now(UTC),
        voltage_v=220.0,
        current_a=2.0,
        power_w=440.0,
        temperature_c=30.0,
    )


def _result(score: float, *, is_anomaly: bool, threshold: float = 0.545) -> AnomalyResult:
    return AnomalyResult(
        anomaly_score=score,
        is_anomaly=is_anomaly,
        model_version="iforest_v1",
        threshold=threshold,
    )


def _job(score: float, *, is_anomaly: bool) -> EscalationJob:
    return EscalationJob(
        reading=_telemetry(),
        reading_time=datetime.now(UTC),
        result=_result(score, is_anomaly=is_anomaly),
        rule_fired=False,
    )


def _worker(mode: str, **overrides) -> CloudForwarderWorker:
    settings = Settings(cloud_forward_mode=mode, **overrides)
    return CloudForwarderWorker(metrics=MetricsService(), settings=settings)


def test_disabled_in_off_mode() -> None:
    worker = _worker("off")
    assert not worker.enabled
    assert not worker.should_escalate(_result(0.9, is_anomaly=True))


def test_gated_mode_escalates_only_flagged_readings() -> None:
    worker = _worker("gated")
    assert worker.enabled
    assert worker.should_escalate(_result(0.60, is_anomaly=True))
    assert not worker.should_escalate(_result(0.40, is_anomaly=False))


def test_gated_mode_threshold_override() -> None:
    worker = _worker("gated", cloud_escalation_threshold=0.7)
    # Flagged by the model but below the stricter escalation threshold.
    assert not worker.should_escalate(_result(0.60, is_anomaly=True))
    assert worker.should_escalate(_result(0.75, is_anomaly=True))


def test_all_mode_escalates_everything() -> None:
    worker = _worker("all")
    assert worker.should_escalate(_result(0.10, is_anomaly=False))


def test_invalid_mode_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(cloud_forward_mode="sometimes")


@pytest.mark.asyncio
async def test_forwards_batch_and_counts_bytes() -> None:
    received: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(json.loads(request.content))
        return httpx.Response(200, json={"accepted": 1})

    metrics = MetricsService()
    settings = Settings(
        cloud_forward_mode="gated",
        cloud_endpoint_url="http://cloud-tier/api/v1/escalations",
        cloud_forward_batch_window_ms=10,
    )
    worker = CloudForwarderWorker(metrics=metrics, settings=settings)
    worker._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    worker.enqueue(_job(0.62, is_anomaly=True))
    worker.enqueue(_job(0.58, is_anomaly=True))
    await worker.start()
    await worker.stop()

    assert sum(len(env["readings"]) for env in received) == 2
    envelope = received[0]
    assert envelope["mode"] == "gated"
    reading = envelope["readings"][0]
    assert reading["device_id"] == "house_0001"
    assert reading["anomaly_score"] == 0.62
    assert reading["model_version"] == "iforest_v1"
    counters = metrics.snapshot()["counters"]
    assert counters["cloud.forwarded"] == 2
    assert counters["cloud.bytes_sent"] > 0
    assert "cloud.forward_failed" not in counters


@pytest.mark.asyncio
async def test_failed_forward_is_counted_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    metrics = MetricsService()
    settings = Settings(cloud_forward_mode="all", cloud_forward_batch_window_ms=10)
    worker = CloudForwarderWorker(metrics=metrics, settings=settings)
    worker._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    worker.enqueue(_job(0.30, is_anomaly=False))
    await worker.start()
    await worker.stop()

    counters = metrics.snapshot()["counters"]
    assert counters.get("cloud.forward_failed", 0) >= 1
    assert "cloud.forwarded" not in counters
