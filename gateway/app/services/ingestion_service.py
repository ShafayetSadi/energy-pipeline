"""Telemetry/status/event ingestion pipeline.

Single entry point for every MQTT message. Performs:
  1. Schema + range validation
  2. Device upsert
  3. Reading/status storage
  4. Rule engine evaluation
  5. Event persistence
  6. Alert dispatch
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from ..config import get_settings
from ..db import repositories as repo
from ..db.session import session_scope
from ..logging_config import get_logger
from ..schemas.events import DeviceEventPayload
from ..schemas.status import StatusPayload
from ..schemas.telemetry import TelemetryPayload
from .alert_service import AlertService
from .metrics_service import MetricsService
from .rule_engine import RuleEngine
from .validation_service import ValidationResult, ValidationService

logger = get_logger(__name__)


class IngestionService:
    """Orchestrates the edge-processing pipeline for one MQTT message."""

    def __init__(
        self,
        *,
        validator: ValidationService,
        rule_engine: RuleEngine,
        alert_service: AlertService,
        metrics: MetricsService,
    ) -> None:
        self._validator = validator
        self._rule_engine = rule_engine
        self._alert_service = alert_service
        self._metrics = metrics
        self._settings = get_settings()

    async def handle(
        self,
        *,
        topic: str,
        message_type: str,
        raw_payload: bytes | str,
    ) -> None:
        received_at = time.monotonic()
        ok, parsed, parse_err = self._validator.validate_json(raw_payload)
        if not ok or parsed is None:
            self._metrics.incr("validation.failures")
            await self._log_quality(
                topic=topic,
                device_id=None,
                error_type="invalid_json",
                error_message=parse_err,
                raw_payload=_safe_text(raw_payload),
            )
            return

        if message_type == "telemetry":
            await self._handle_telemetry(topic, parsed, received_at)
        elif message_type == "status":
            await self._handle_status(topic, parsed, received_at)
        elif message_type == "events":
            await self._handle_device_event(topic, parsed, received_at)
        else:
            self._metrics.incr("messages.unsupported_type")
            logger.warning("unsupported_message_type", topic=topic, type=message_type)

    # -----------------------------------------------------------------
    # Telemetry
    # -----------------------------------------------------------------

    async def _handle_telemetry(
        self,
        topic: str,
        data: dict[str, Any],
        received_at: float,
    ) -> None:
        result: ValidationResult = self._validator.validate_telemetry(data, topic_device_id=_topic_device_id(topic))
        if not result.valid or not isinstance(result.payload, TelemetryPayload):
            self._metrics.incr("validation.failures")
            self._metrics.incr("validation.telemetry.failures")
            await self._log_quality(
                topic=topic,
                device_id=data.get("device_id"),
                error_type=result.error_type or "telemetry_invalid",
                error_message=result.error_message,
                raw_payload=_json_dumps(data),
            )
            return

        self._metrics.incr("validation.telemetry.success")
        self._metrics.incr("messages.telemetry")
        payload: TelemetryPayload = result.payload
        gateway_received_at = datetime.utcnow()

        if self._settings.is_proposed and self._settings.enable_rule_engine:
            hits = await self._rule_engine.evaluate(payload, received_at)
        else:
            hits = []

        async with session_scope() as session:
            inserted = False
            if self._settings.is_proposed and not self._settings.store_raw_readings:
                # Proposed mode without raw storage: skip insertion, keep events.
                inserted = False
            elif self._settings.store_raw_readings:
                await repo.upsert_device(
                    session,
                    device_id=payload.device_id,
                    firmware_version=payload.firmware_version,
                )
                inserted = await repo.insert_reading(
                    session,
                    time=payload.timestamp.astimezone(tz=payload.timestamp.tzinfo)
                    if payload.timestamp.tzinfo
                    else payload.timestamp,
                    device_id=payload.device_id,
                    voltage_v=payload.voltage_v,
                    current_a=payload.current_a,
                    power_w=payload.power_w,
                    temperature_c=payload.temperature_c,
                    sequence_no=payload.sequence_no,
                    raw_payload=data,
                )
            if not inserted:
                self._metrics.incr("readings.duplicates")

            created_events: list[tuple[int, datetime]] = []
            for hit in hits:
                event_time = payload.timestamp
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=gateway_received_at.tzinfo)
                event = await repo.insert_event(
                    session,
                    time=event_time,
                    device_id=payload.device_id,
                    event_type=hit.event_type,
                    severity=hit.severity,
                    rule_name=hit.rule_name,
                    message=hit.message,
                    reading_time=payload.timestamp,
                    event_value=hit.event_value,
                    threshold_value=hit.threshold_value,
                    metadata=hit.metadata,
                )
                self._metrics.incr(f"events.{hit.severity.lower()}")
                self._metrics.incr(f"events.type.{hit.event_type.lower()}")
                created_events.append((event.event_id, event_time))

        self._metrics.record_latency("telemetry", (time.monotonic() - received_at) * 1000.0)
        if inserted:
            self._metrics.incr("readings.stored")

        for hit, (event_id, event_time) in zip(hits, created_events, strict=True):
            await self._alert_service.maybe_alert(
                hit, event_id=event_id, device_id=payload.device_id, event_time=event_time
            )

    # -----------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------

    async def _handle_status(
        self,
        topic: str,
        data: dict[str, Any],
        received_at: float,
    ) -> None:
        result = self._validator.validate_status(data, topic_device_id=_topic_device_id(topic))
        if not result.valid or not isinstance(result.payload, StatusPayload):
            self._metrics.incr("validation.failures")
            self._metrics.incr("validation.status.failures")
            await self._log_quality(
                topic=topic,
                device_id=data.get("device_id"),
                error_type=result.error_type or "status_invalid",
                error_message=result.error_message,
                raw_payload=_json_dumps(data),
            )
            return

        self._metrics.incr("validation.status.success")
        self._metrics.incr("messages.status")
        payload: StatusPayload = result.payload

        async with session_scope() as session:
            await repo.upsert_device(
                session,
                device_id=payload.device_id,
                firmware_version=payload.firmware_version,
            )
            await repo.update_device_status(
                session,
                device_id=payload.device_id,
                status=payload.status,
                last_seen_at=payload.timestamp,
            )
            await repo.record_status_history(
                session,
                time=payload.timestamp,
                device_id=payload.device_id,
                status=payload.status,
                firmware_version=payload.firmware_version,
                ip_address=payload.ip_address,
                rssi_dbm=payload.rssi_dbm,
                metadata={"reason": payload.reason} if payload.reason else None,
            )

        if payload.status == "offline" and self._settings.is_proposed:
            await self._record_device_offline_event(payload)

        self._metrics.record_latency("status", (time.monotonic() - received_at) * 1000.0)

    async def _record_device_offline_event(self, payload: StatusPayload) -> None:
        async with session_scope() as session:
            event = await repo.insert_event(
                session,
                time=payload.timestamp,
                device_id=payload.device_id,
                event_type="DEVICE_FAILURE",
                severity="CRITICAL",
                rule_name="device_offline_status",
                message=f"Device {payload.device_id} reported offline",
                reading_time=None,
                event_value=None,
                threshold_value=None,
                metadata={"reason": payload.reason},
            )
            event_id = event.event_id
            event_time = event.time
        self._metrics.incr("events.critical")
        self._metrics.incr("events.type.device_failure")
        from .rule_engine import RuleHit

        hit = RuleHit(
            rule_name="device_offline_status",
            event_type="DEVICE_FAILURE",
            severity="CRITICAL",
            message=f"Device {payload.device_id} reported offline",
            metadata={"reason": payload.reason},
        )
        await self._alert_service.maybe_alert(
            hit, event_id=event_id, device_id=payload.device_id, event_time=event_time
        )

    # -----------------------------------------------------------------
    # Device-originated events
    # -----------------------------------------------------------------

    async def _handle_device_event(
        self,
        topic: str,
        data: dict[str, Any],
        received_at: float,
    ) -> None:
        result = self._validator.validate_device_event(
            data, topic_device_id=_topic_device_id(topic)
        )
        if not result.valid or not isinstance(result.payload, DeviceEventPayload):
            self._metrics.incr("validation.failures")
            self._metrics.incr("validation.event.failures")
            await self._log_quality(
                topic=topic,
                device_id=data.get("device_id"),
                error_type=result.error_type or "event_invalid",
                error_message=result.error_message,
                raw_payload=_json_dumps(data),
            )
            return

        self._metrics.incr("validation.event.success")
        self._metrics.incr("messages.events")
        payload: DeviceEventPayload = result.payload

        async with session_scope() as session:
            event = await repo.insert_event(
                session,
                time=payload.timestamp,
                device_id=payload.device_id,
                event_type=payload.event_type,
                severity=payload.severity,
                rule_name="device_event",
                message=payload.message,
                reading_time=None,
                event_value=None,
                threshold_value=None,
                metadata={"source": "device"},
            )
            event_id = event.event_id
            event_time = event.time

        self._metrics.incr(f"events.{payload.severity.lower()}")
        self._metrics.incr(f"events.type.{payload.event_type.lower()}")
        self._metrics.record_latency("event", (time.monotonic() - received_at) * 1000.0)

        if payload.severity == "CRITICAL":
            from .rule_engine import RuleHit

            hit = RuleHit(
                rule_name="device_event",
                event_type=payload.event_type,
                severity="CRITICAL",
                message=payload.message or payload.event_type,
            )
            await self._alert_service.maybe_alert(
                hit,
                event_id=event_id,
                device_id=payload.device_id,
                event_time=event_time,
            )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    async def _log_quality(
        self,
        *,
        topic: str,
        device_id: str | None,
        error_type: str,
        error_message: str | None,
        raw_payload: str | None,
    ) -> None:
        try:
            async with session_scope() as session:
                await repo.log_data_quality(
                    session,
                    topic=topic,
                    device_id=device_id,
                    error_type=error_type,
                    error_message=error_message,
                    raw_payload=raw_payload,
                )
        except Exception as exc:
            logger.warning("quality_log_write_failed", error=str(exc))


def _safe_text(raw: bytes | str | bytearray) -> str:
    if isinstance(raw, (bytes, bytearray)):
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return repr(raw)
    return str(raw)


def _json_dumps(data: dict[str, Any]) -> str:
    import json

    try:
        return json.dumps(data, default=str)
    except Exception:
        return repr(data)


def _topic_device_id(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) >= 3 and parts[0] == "energy":
        return parts[1]
    return None
