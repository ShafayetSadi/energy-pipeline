"""Shared pytest fixtures."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gateway.app.schemas.telemetry import TelemetryPayload


@pytest.fixture
def now_utc() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def sample_telemetry(now_utc: datetime) -> TelemetryPayload:
    return TelemetryPayload(
        schema_version="1.0",
        device_id="house_0001",
        timestamp=now_utc,
        voltage_v=220.0,
        current_a=2.0,
        power_w=440.0,
        temperature_c=30.0,
        sequence_no=1,
    )
