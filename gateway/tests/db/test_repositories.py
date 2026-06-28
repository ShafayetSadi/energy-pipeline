"""Focused repository behavior tests with fake async sessions."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from gateway.app.db.repositories.devices import update_device_status
from gateway.app.db.repositories.events import acknowledge_event


class FakeSession:
    def __init__(self, entity=None) -> None:
        self.entity = entity
        self.added: list[Any] = []
        self.get_calls: list[tuple[Any, Any]] = []

    async def get(self, model, key):
        self.get_calls.append((model, key))
        return self.entity

    def add(self, entity) -> None:
        self.added.append(entity)


async def test_update_device_status_creates_missing_device() -> None:
    session = FakeSession()

    await update_device_status(cast(Any, session), device_id="house_1", status="online")

    assert len(session.added) == 1
    assert session.added[0].device_id == "house_1"
    assert session.added[0].status == "online"


async def test_update_device_status_updates_existing_device() -> None:
    device = SimpleNamespace(status="unknown", last_seen_at=None)
    session = FakeSession(device)

    await update_device_status(cast(Any, session), device_id="house_1", status="offline")

    assert device.status == "offline"
    assert session.added == []


async def test_acknowledge_event_returns_false_when_missing() -> None:
    session = FakeSession()

    assert await acknowledge_event(cast(Any, session), 123) is False


async def test_acknowledge_event_marks_existing_event() -> None:
    event = SimpleNamespace(acknowledged=False)
    session = FakeSession(event)

    assert await acknowledge_event(cast(Any, session), 123) is True
    assert event.acknowledged is True
