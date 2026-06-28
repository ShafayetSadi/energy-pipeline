"""Worker lifecycle tests."""
from __future__ import annotations

from typing import Any, cast

import pytest
from gateway.app.services.alert_service import AlertService
from gateway.app.services.metrics_service import MetricsService
from gateway.app.services.rule_engine import RuleEngine
from gateway.app.workers.aggregation_worker import AggregationWorker
from gateway.app.workers.alert_outbox import AlertOutboxWorker
from gateway.app.workers.device_heartbeat import DeviceHeartbeatWorker
from gateway.app.workers.mqtt_consumer import MQTTConsumerWorker


async def _wait_forever(worker) -> None:
    await worker._stop.wait()


async def test_aggregation_worker_start_stop_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = AggregationWorker()
    worker._settings.enable_aggregation = True
    monkeypatch.setattr(worker, "_loop", lambda: _wait_forever(worker))

    await worker.start()
    first_task = worker._task
    await worker.start()

    assert worker._task is first_task
    await worker.stop()
    await worker.stop()
    assert worker._task is None


async def test_heartbeat_worker_start_stop_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = DeviceHeartbeatWorker(
        rule_engine=RuleEngine(), alert_service=AlertService(), metrics=MetricsService()
    )
    monkeypatch.setattr(worker, "_loop", lambda: _wait_forever(worker))

    await worker.start()
    first_task = worker._task
    await worker.start()

    assert worker._task is first_task
    await worker.stop()
    await worker.stop()
    assert worker._task is None


async def test_mqtt_worker_start_stop_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    worker = MQTTConsumerWorker(ingestion=cast(Any, object()), metrics=MetricsService())
    monkeypatch.setattr(worker, "_run", lambda: _wait_forever(worker))

    await worker.start()
    first_task = worker._task
    await worker.start()

    assert worker._task is first_task
    await worker.stop()
    await worker.stop()
    assert worker._task is None


async def test_alert_outbox_worker_start_stop_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = AlertOutboxWorker(alert_service=AlertService())
    worker._settings.alert_outbox_enabled = True
    monkeypatch.setattr(worker, "_loop", lambda: _wait_forever(worker))

    await worker.start()
    first_task = worker._task
    await worker.start()

    assert worker._task is first_task
    await worker.stop()
    await worker.stop()
    assert worker._task is None
