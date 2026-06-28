"""Telemetry ingestion flow."""
from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ...db.repositories import devices as device_repo
from ...db.repositories import events as event_repo
from ...db.repositories import readings as reading_repo
from ...db.session import session_scope
from ...schemas.telemetry import TelemetryPayload
from ..validation_service import ValidationResult
from .helpers import json_dumps, topic_device_id

if TYPE_CHECKING:
    from .service import IngestionService


async def handle_telemetry(
    service: IngestionService,
    topic: str,
    data: dict[str, Any],
    received_at: float,
) -> None:
    result: ValidationResult = service.validator.validate_telemetry(
        data, topic_device_id=topic_device_id(topic)
    )
    if not result.valid or not isinstance(result.payload, TelemetryPayload):
        service.metrics.incr("validation.failures")
        service.metrics.incr("validation.telemetry.failures")
        await service.log_quality(
            topic=topic,
            device_id=data.get("device_id"),
            error_type=result.error_type or "telemetry_invalid",
            error_message=result.error_message,
            raw_payload=json_dumps(data),
        )
        return

    service.metrics.incr("validation.telemetry.success")
    service.metrics.incr("messages.telemetry")
    payload: TelemetryPayload = result.payload
    gateway_received_at = datetime.now(UTC)

    if service.settings.is_proposed and service.settings.enable_rule_engine:
        hits = await service.rule_engine.evaluate(payload, received_at)
    else:
        hits = []

    async with session_scope() as session:
        inserted = False
        if service.settings.is_proposed and not service.settings.store_raw_readings:
            inserted = False
        elif service.settings.store_raw_readings:
            await device_repo.upsert_device(
                session,
                device_id=payload.device_id,
                firmware_version=payload.firmware_version,
            )
            inserted = await reading_repo.insert_reading(
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
            service.metrics.incr("readings.duplicates")

        created_events: list[tuple[int, datetime]] = []
        for hit in hits:
            event_time = payload.timestamp
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=gateway_received_at.tzinfo)
            event = await event_repo.insert_event(
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
            service.metrics.incr(f"events.{hit.severity.lower()}")
            service.metrics.incr(f"events.type.{hit.event_type.lower()}")
            created_events.append((event.event_id, event_time))

    service.metrics.record_latency("telemetry", (time.monotonic() - received_at) * 1000.0)
    if inserted:
        service.metrics.incr("readings.stored")

    for hit, (event_id, event_time) in zip(hits, created_events, strict=True):
        await service.alert_service.maybe_alert(
            hit, event_id=event_id, device_id=payload.device_id, event_time=event_time
        )
