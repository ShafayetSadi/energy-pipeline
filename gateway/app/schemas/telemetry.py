"""Telemetry payload schema (energy/{device_id}/telemetry)."""
from __future__ import annotations

from pydantic import Field

from .common import BaseMessage


class TelemetryPayload(BaseMessage):
    """Voltage, current, power, optional temperature from a node."""

    voltage_v: float = Field(..., ge=0, description="RMS voltage in volts")
    current_a: float = Field(..., ge=0, description="RMS current in amperes")
    power_w: float = Field(..., ge=0, description="Instantaneous real power in watts")
    temperature_c: float | None = Field(default=None, description="Optional temperature")
    sequence_no: int | None = Field(default=None, description="Monotonic sequence number")
    firmware_version: str | None = None
    rssi_dbm: float | None = None
