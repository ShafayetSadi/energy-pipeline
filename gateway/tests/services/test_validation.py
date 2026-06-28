"""Tests for ValidationService."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from gateway.app.services.validation_service import ValidationService


@pytest.fixture
def validator() -> ValidationService:
    return ValidationService()


def _payload(**overrides) -> dict:
    base = {
        "schema_version": "1.0",
        "device_id": "house_0001",
        "timestamp": datetime.now(UTC).isoformat(),
        "voltage_v": 220.0,
        "current_a": 2.0,
        "power_w": 440.0,
    }
    base.update(overrides)
    return base


def test_valid_telemetry(validator: ValidationService) -> None:
    result = validator.validate_telemetry(_payload())
    assert result.valid
    assert result.payload is not None
    assert result.payload.device_id == "house_0001"


def test_invalid_schema_version(validator: ValidationService) -> None:
    result = validator.validate_telemetry(_payload(schema_version="99.0"))
    assert not result.valid
    assert result.error_type == "unsupported_schema_version"


def test_voltage_out_of_range(validator: ValidationService) -> None:
    result = validator.validate_telemetry(_payload(voltage_v=999.0))
    assert not result.valid
    assert result.error_type == "voltage_out_of_range"


def test_current_out_of_range(validator: ValidationService) -> None:
    result = validator.validate_telemetry(_payload(current_a=200.0))
    assert not result.valid
    assert result.error_type == "current_out_of_range"


def test_power_out_of_range(validator: ValidationService) -> None:
    result = validator.validate_telemetry(_payload(power_w=99_999_999.0))
    assert not result.valid
    assert result.error_type == "power_out_of_range"


def test_temperature_out_of_range(validator: ValidationService) -> None:
    result = validator.validate_telemetry(_payload(temperature_c=300.0))
    assert not result.valid
    assert result.error_type == "temperature_out_of_range"


def test_topic_device_id_mismatch(validator: ValidationService) -> None:
    result = validator.validate_telemetry(_payload(device_id="house_0002"), topic_device_id="house_0001")
    assert not result.valid
    assert result.error_type == "device_id_mismatch"


def test_timestamp_too_far_in_future(validator: ValidationService) -> None:
    future = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    result = validator.validate_telemetry(_payload(timestamp=future))
    assert not result.valid
    assert result.error_type == "timestamp_future_skew"


def test_timestamp_too_far_in_past(validator: ValidationService) -> None:
    past = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    result = validator.validate_telemetry(_payload(timestamp=past))
    assert not result.valid
    assert result.error_type == "timestamp_past_skew"


def test_missing_required_field(validator: ValidationService) -> None:
    payload = _payload()
    payload.pop("power_w")
    result = validator.validate_telemetry(payload)
    assert not result.valid


def test_invalid_json(validator: ValidationService) -> None:
    ok, parsed, err = validator.validate_json(b"not json")
    assert not ok
    assert parsed is None
    assert err and "invalid_json" in err
