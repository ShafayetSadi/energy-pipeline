"""API smoke tests with repository dependencies patched out."""
from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from gateway.app.db.session import get_db
from gateway.app.main import _build_app
from gateway.app.services.metrics_service import MetricsService


async def _dummy_db() -> AsyncIterator[object]:
    yield object()


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch):
    app = _build_app()
    app.dependency_overrides[get_db] = _dummy_db
    app.state.metrics = MetricsService()

    from gateway.app.api import devices, events, metrics, readings

    monkeypatch.setattr(devices.device_repo, "list_devices", _empty)
    monkeypatch.setattr(devices.status_repo, "device_status_history", _empty)
    monkeypatch.setattr(readings.reading_repo, "readings_for_device", _empty)
    monkeypatch.setattr(events.event_repo, "list_events", _empty)
    monkeypatch.setattr(metrics.event_repo, "count_events_by_severity", _empty_counts)
    monkeypatch.setattr(metrics.quality_repo, "count_quality_logs_by_type", _empty_counts)
    return app


async def _empty(*args, **kwargs) -> list:
    return []


async def _empty_counts(*args, **kwargs) -> dict[str, int]:
    return {}


async def test_health_and_metrics_summary(app) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        summary = await client.get("/api/v1/metrics/summary")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert summary.status_code == 200
    assert "counters" in summary.json()


async def test_empty_collection_routes(app) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        devices = await client.get("/api/v1/devices")
        readings = await client.get("/api/v1/readings", params={"device_id": "house_1"})
        events = await client.get("/api/v1/events")

    assert devices.status_code == 200
    assert devices.json() == []
    assert readings.status_code == 200
    assert readings.json() == []
    assert events.status_code == 200
    assert events.json() == []


async def test_readings_requires_device_id(app) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/readings")

    assert response.status_code == 400
    assert response.json()["detail"] == "device_id query parameter is required"
