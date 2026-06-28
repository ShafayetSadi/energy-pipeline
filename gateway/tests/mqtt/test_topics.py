"""Tests for MQTT topic parsing."""
from __future__ import annotations

from gateway.app.mqtt.topics import is_supported_message_type, parse_topic


def test_parse_telemetry_topic() -> None:
    parts = parse_topic("energy/house_001/telemetry")
    assert parts is not None
    assert parts.device_id == "house_001"
    assert parts.message_type == "telemetry"


def test_parse_status_topic() -> None:
    parts = parse_topic("energy/house_001/status")
    assert parts is not None
    assert parts.message_type == "status"


def test_parse_invalid_topic() -> None:
    assert parse_topic("foo/bar") is None
    assert parse_topic("energy") is None
    assert parse_topic("") is None


def test_supported_message_types() -> None:
    assert is_supported_message_type("telemetry")
    assert is_supported_message_type("status")
    assert is_supported_message_type("events")
    assert not is_supported_message_type("commands")
    assert not is_supported_message_type("config")
