"""Device-originated event payload schema (energy/{device_id}/events)."""
from __future__ import annotations

from typing import Literal

from .common import BaseMessage

SeverityValue = Literal["NORMAL", "INFO", "WARNING", "CRITICAL"]


class DeviceEventPayload(BaseMessage):
    """Optional event published by the device itself."""

    event_type: str
    severity: SeverityValue = "INFO"
    message: str | None = None
