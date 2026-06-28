"""Tests for alert outbox worker processing."""
from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, cast

import pytest
from gateway.app.workers import alert_outbox as worker_module
from gateway.app.workers.alert_outbox import AlertOutboxWorker


@asynccontextmanager
async def _fake_session_scope():
    yield object()


class FakeAlertService:
    async def deliver_outbox_message(
        self, channel: str, payload: dict[str, Any]
    ) -> tuple[str, str | None]:
        if channel == "webhook":
            return ("error", "status=500")
        if channel == "slack":
            raise RuntimeError("slack down")
        return ("ok", None)


async def test_alert_outbox_worker_records_success_failure_and_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        SimpleNamespace(
            outbox_id=1,
            event_id=10,
            channel="console",
            payload={"event_id": 10},
            attempts=0,
        ),
        SimpleNamespace(
            outbox_id=2,
            event_id=20,
            channel="webhook",
            payload={"event_id": 20},
            attempts=1,
        ),
        SimpleNamespace(
            outbox_id=3,
            event_id=30,
            channel="slack",
            payload={"event_id": 30},
            attempts=4,
        ),
    ]
    deliveries: list[tuple[int, str, str, str | None]] = []
    sent: list[int] = []
    failed: list[tuple[int, int, str]] = []

    async def claim_due_alerts(session, *, batch_size: int):
        assert batch_size == 50
        return rows

    async def record_delivery(session, *, event_id, channel, status, response):
        deliveries.append((event_id, channel, status, response))

    async def mark_sent(session, *, outbox_id: int):
        sent.append(outbox_id)

    async def mark_failed(session, *, outbox_id: int, attempts: int, error: str, max_attempts: int):
        assert max_attempts == 5
        failed.append((outbox_id, attempts, error))
        return "failed"

    monkeypatch.setattr(worker_module, "session_scope", _fake_session_scope)
    monkeypatch.setattr(worker_module.outbox_repo, "claim_due_alerts", claim_due_alerts)
    monkeypatch.setattr(worker_module.outbox_repo, "record_delivery", record_delivery)
    monkeypatch.setattr(worker_module.outbox_repo, "mark_sent", mark_sent)
    monkeypatch.setattr(worker_module.outbox_repo, "mark_failed", mark_failed)

    worker = AlertOutboxWorker(alert_service=cast(Any, FakeAlertService()))

    await worker._tick()

    assert deliveries == [
        (10, "console", "ok", None),
        (20, "webhook", "error", "status=500"),
        (30, "slack", "error", "exception: slack down"),
    ]
    assert sent == [1]
    assert failed == [(2, 2, "status=500"), (3, 5, "exception: slack down")]
