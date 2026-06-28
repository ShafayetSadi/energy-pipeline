"""Status ingestion flow."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ...db.repositories import devices as device_repo
from ...db.repositories import events as event_repo
from ...db.repositories import status as status_repo
from ...db.session import session_scope
from ...schemas.status import StatusPayload
from ..rule_engine import RuleHit
from .helpers import json_dumps, topic_device_id

if TYPE_CHECKING:
    from .service import IngestionService


async def handle_status(
    service: IngestionService,
    topic: str,
    data: dict[str, Any],
    received_at: float,
) -> None:
    result = service.validator.validate_status(data, topic_device_id=topic_device_id(topic))
    if not result.valid or not isinstance(result.payload, StatusPayload):
        service.metrics.incr("validation.failures")
        service.metrics.incr("validation.status.failures")
        await service.log_quality(
            topic=topic,
            device_id=data.get("device_id"),
            error_type=result.error_type or "status_invalid",
            error_message=result.error_message,
            raw_payload=json_dumps(data),
        )
        return

    service.metrics.incr("validation.status.success")
    service.metrics.incr("messages.status")
    payload: StatusPayload = result.payload

    async with session_scope() as session:
        await device_repo.upsert_device(
            session,
            device_id=payload.device_id,
            firmware_version=payload.firmware_version,
        )
        await device_repo.update_device_status(
            session,
            device_id=payload.device_id,
            status=payload.status,
            last_seen_at=payload.timestamp,
        )
        await status_repo.record_status_history(
            session,
            time=payload.timestamp,
            device_id=payload.device_id,
            status=payload.status,
            firmware_version=payload.firmware_version,
            ip_address=payload.ip_address,
            rssi_dbm=payload.rssi_dbm,
            metadata={"reason": payload.reason} if payload.reason else None,
        )

    if payload.status == "offline" and service.settings.is_proposed:
        await record_device_offline_event(service, payload)

    service.metrics.record_latency("status", (time.monotonic() - received_at) * 1000.0)


async def record_device_offline_event(
    service: IngestionService, payload: StatusPayload
) -> None:
    async with session_scope() as session:
        event = await event_repo.insert_event(
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
    service.metrics.incr("events.critical")
    service.metrics.incr("events.type.device_failure")
    hit = RuleHit(
        rule_name="device_offline_status",
        event_type="DEVICE_FAILURE",
        severity="CRITICAL",
        message=f"Device {payload.device_id} reported offline",
        metadata={"reason": payload.reason},
    )
    await service.alert_service.maybe_alert(
        hit, event_id=event_id, device_id=payload.device_id, event_time=event_time
    )
