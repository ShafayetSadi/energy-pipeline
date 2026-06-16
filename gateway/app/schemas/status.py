"""Device status payload schema (energy/{device_id}/status)."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import BaseMessage

StatusValue = Literal["online", "offline", "maintenance", "error"]


class StatusPayload(BaseMessage):
    """Device health and connection metadata."""

    status: StatusValue
    firmware_version: str | None = None
    ip_address: str | None = None
    rssi_dbm: float | None = Field(default=None, description="Wi-Fi signal strength in dBm")
    reason: str | None = None
