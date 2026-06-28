"""Device-originated event ingestion flow."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ...db.repositories import events as event_repo
from ...db.session import session_scope
from ...schemas.events import DeviceEventPayload
from ..rule_engine import RuleHit
from .helpers import json_dumps, topic_device_id

if TYPE_CHECKING:
    from .service import IngestionService


async def handle_device_event(
    service: IngestionService,
    topic: str,
    data: dict[str, Any],
    received_at: float,
) -> None:
    result = service.validator.validate_device_event(
        data, topic_device_id=topic_device_id(topic)
    )
    if not result.valid or not isinstance(result.payload, DeviceEventPayload):
        service.metrics.incr("validation.failures")
        service.metrics.incr("validation.event.failures")
        await service.log_quality(
            topic=topic,
            device_id=data.get("device_id"),
            error_type=result.error_type or "event_invalid",
            error_message=result.error_message,
            raw_payload=json_dumps(data),
        )
        return

    service.metrics.incr("validation.event.success")
    service.metrics.incr("messages.events")
    payload: DeviceEventPayload = result.payload

    async with session_scope() as session:
        event = await event_repo.insert_event(
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

    service.metrics.incr(f"events.{payload.severity.lower()}")
    service.metrics.incr(f"events.type.{payload.event_type.lower()}")
    service.metrics.record_latency("event", (time.monotonic() - received_at) * 1000.0)

    if payload.severity == "CRITICAL":
        hit = RuleHit(
            rule_name="device_event",
            event_type=payload.event_type,
            severity="CRITICAL",
            message=payload.message or payload.event_type,
        )
        await service.alert_service.maybe_alert(
            hit,
            event_id=event_id,
            device_id=payload.device_id,
            event_time=event_time,
        )
