"""Common fields shared across telemetry, status, and event payloads."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseMessage(BaseModel):
    """Base class for all device-published MQTT payloads."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = Field(..., description="Schema version, e.g. '1.0'")
    device_id: str = Field(..., min_length=1, max_length=64)
    timestamp: datetime


class TopicInfo(BaseModel):
    """Result of parsing an MQTT topic into structured fields."""

    raw_topic: str
    device_id: str
    message_type: str  # telemetry | status | events | commands | config | unknown
