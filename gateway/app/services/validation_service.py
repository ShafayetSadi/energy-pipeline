"""Payload validation: schema parsing + physical range + timestamp checks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from ..config import get_settings
from ..logging_config import get_logger
from ..schemas.events import DeviceEventPayload
from ..schemas.status import StatusPayload
from ..schemas.telemetry import TelemetryPayload

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    valid: bool
    payload: TelemetryPayload | StatusPayload | DeviceEventPayload | None = None
    error_type: str | None = None
    error_message: str | None = None
    error_field: str | None = None


class ValidationService:
    """Validates incoming MQTT messages against schema and physical ranges."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def validate_json(self, raw: bytes | str | bytearray) -> tuple[bool, dict[str, Any] | None, str | None]:
        """Parse JSON payload. Returns (ok, dict, error_message)."""
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8", errors="replace")
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            return False, None, f"invalid_json: {exc.msg}"
        except UnicodeDecodeError as exc:
            return False, None, f"invalid_encoding: {exc.reason}"
        if not isinstance(data, dict):
            return False, None, "payload_not_object"
        return True, data, None

    def validate_telemetry(
        self, data: dict[str, Any], *, topic_device_id: str | None = None
    ) -> ValidationResult:
        """Validate a parsed telemetry dict and return a typed payload."""
        settings = self._settings
        supported = settings.supported_schema_version_set
        schema_version = str(data.get("schema_version", ""))
        if schema_version not in supported:
            return ValidationResult(
                valid=False,
                error_type="unsupported_schema_version",
                error_message=f"schema_version={schema_version!r} not in {supported}",
            )
        try:
            payload = TelemetryPayload.model_validate(data)
        except ValidationError as exc:
            err: Any = exc.errors()[0] if exc.errors() else {}
            return ValidationResult(
                valid=False,
                error_type="schema_validation_error",
                error_message=str(exc),
                error_field=".".join(str(p) for p in err.get("loc", [])),
            )

        if topic_device_id and payload.device_id != topic_device_id:
            return ValidationResult(
                valid=False,
                error_type="device_id_mismatch",
                error_message=(
                    f"topic device_id={topic_device_id!r} != payload device_id="
                    f"{payload.device_id!r}"
                ),
            )

        if not (settings.voltage_min <= payload.voltage_v <= settings.voltage_max):
            return ValidationResult(
                valid=False,
                error_type="voltage_out_of_range",
                error_message=(
                    f"voltage_v={payload.voltage_v} outside "
                    f"[{settings.voltage_min}, {settings.voltage_max}]"
                ),
            )
        if not (settings.current_min <= payload.current_a <= settings.current_max):
            return ValidationResult(
                valid=False,
                error_type="current_out_of_range",
                error_message=(
                    f"current_a={payload.current_a} outside "
                    f"[{settings.current_min}, {settings.current_max}]"
                ),
            )
        if not (settings.power_min <= payload.power_w <= settings.power_max):
            return ValidationResult(
                valid=False,
                error_type="power_out_of_range",
                error_message=(
                    f"power_w={payload.power_w} outside "
                    f"[{settings.power_min}, {settings.power_max}]"
                ),
            )
        if payload.temperature_c is not None and not (
            settings.temperature_min <= payload.temperature_c <= settings.temperature_max
        ):
            return ValidationResult(
                valid=False,
                error_type="temperature_out_of_range",
                error_message=(
                    f"temperature_c={payload.temperature_c} outside "
                    f"[{settings.temperature_min}, {settings.temperature_max}]"
                ),
            )

        skew = _timestamp_skew_seconds(payload.timestamp)
        if skew is None:
            return ValidationResult(
                valid=False, error_type="invalid_timestamp", error_message="timestamp_unparseable"
            )
        if skew < -settings.max_future_skew_seconds:
            return ValidationResult(
                valid=False,
                error_type="timestamp_future_skew",
                error_message=f"timestamp {-skew:.1f}s in the future",
            )
        if skew > settings.max_past_skew_seconds:
            return ValidationResult(
                valid=False,
                error_type="timestamp_past_skew",
                error_message=f"timestamp {skew:.1f}s in the past",
            )

        return ValidationResult(valid=True, payload=payload)

    def validate_status(
        self, data: dict[str, Any], *, topic_device_id: str | None = None
    ) -> ValidationResult:
        settings = self._settings
        supported = settings.supported_schema_version_set
        schema_version = str(data.get("schema_version", ""))
        if schema_version not in supported:
            return ValidationResult(
                valid=False,
                error_type="unsupported_schema_version",
                error_message=f"schema_version={schema_version!r} not in {supported}",
            )
        try:
            payload = StatusPayload.model_validate(data)
        except ValidationError as exc:
            return ValidationResult(
                valid=False,
                error_type="schema_validation_error",
                error_message=str(exc),
            )
        if topic_device_id and payload.device_id != topic_device_id:
            return ValidationResult(
                valid=False,
                error_type="device_id_mismatch",
                error_message=(
                    f"topic device_id={topic_device_id!r} != payload device_id="
                    f"{payload.device_id!r}"
                ),
            )
        skew = _timestamp_skew_seconds(payload.timestamp)
        if skew is None:
            return ValidationResult(
                valid=False, error_type="invalid_timestamp", error_message="timestamp_unparseable"
            )
        if skew < -settings.max_future_skew_seconds:
            return ValidationResult(
                valid=False,
                error_type="timestamp_future_skew",
                error_message=f"timestamp {-skew:.1f}s in the future",
            )
        if skew > settings.max_past_skew_seconds:
            return ValidationResult(
                valid=False,
                error_type="timestamp_past_skew",
                error_message=f"timestamp {skew:.1f}s in the past",
            )
        return ValidationResult(valid=True, payload=payload)

    def validate_device_event(
        self, data: dict[str, Any], *, topic_device_id: str | None = None
    ) -> ValidationResult:
        settings = self._settings
        supported = settings.supported_schema_version_set
        schema_version = str(data.get("schema_version", ""))
        if schema_version not in supported:
            return ValidationResult(
                valid=False,
                error_type="unsupported_schema_version",
                error_message=f"schema_version={schema_version!r} not in {supported}",
            )
        try:
            payload = DeviceEventPayload.model_validate(data)
        except ValidationError as exc:
            return ValidationResult(
                valid=False,
                error_type="schema_validation_error",
                error_message=str(exc),
            )
        if topic_device_id and payload.device_id != topic_device_id:
            return ValidationResult(
                valid=False,
                error_type="device_id_mismatch",
                error_message=(
                    f"topic device_id={topic_device_id!r} != payload device_id="
                    f"{payload.device_id!r}"
                ),
            )
        return ValidationResult(valid=True, payload=payload)


def _timestamp_skew_seconds(value: datetime) -> float | None:
    """Seconds between now (UTC) and a device timestamp. None if unparseable."""
    try:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        return (now - value).total_seconds()
    except Exception:
        return None
