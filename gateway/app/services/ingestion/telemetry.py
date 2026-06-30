"""Telemetry ingestion flow."""
from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ...db.repositories import devices as device_repo
from ...db.repositories import events as event_repo
from ...db.repositories import predictions as prediction_repo
from ...db.repositories import readings as reading_repo
from ...db.session import session_scope
from ...schemas.telemetry import TelemetryPayload
from ..rule_engine import RuleHit
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

    reading_time = (
        payload.timestamp
        if payload.timestamp.tzinfo
        else payload.timestamp.replace(tzinfo=gateway_received_at.tzinfo)
    )

    # Edge ML anomaly scoring (Phase 1: Isolation Forest). Independent of the
    # rule engine so the A/B harness can run rules-only, ml-only, or hybrid.
    # When async scoring is enabled the reading is handed to the micro-batch
    # worker (keeping ML off the ingestion hot path); otherwise it is scored
    # inline here. ``ml_result`` is only set for the inline path, which is the
    # only path that writes the prediction row in this transaction.
    ml_result = None
    ml_enabled = (
        service.settings.is_proposed
        and service.settings.enable_ml
        and service.anomaly_detector.available
    )
    if ml_enabled and service.settings.ml_async_scoring and service.ml_scoring_worker:
        service.ml_scoring_worker.enqueue_reading(
            payload, reading_time, rule_fired=bool(hits)
        )
    elif ml_enabled:
        ml_start = time.monotonic()
        ml_result = service.anomaly_detector.score(payload)
        service.metrics.record_latency(
            "ml_inference", (time.monotonic() - ml_start) * 1000.0
        )
        if ml_result is not None:
            service.metrics.incr("ml.scored")
            if ml_result.is_anomaly:
                service.metrics.incr("ml.anomalies")
            # In hybrid/ml-only detection, an ML anomaly becomes an event and
            # flows through the same storage/alert path as a rule hit.
            if (
                ml_result.is_anomaly
                and service.settings.ml_emit_events
                and not service.rule_engine.is_cooldown_active(
                    (payload.device_id, service.settings.ml_event_type)
                )
            ):
                service.rule_engine.mark_alert_sent(
                    (payload.device_id, service.settings.ml_event_type)
                )
                hits.append(
                    RuleHit(
                        rule_name="ml_isolation_forest",
                        event_type=service.settings.ml_event_type,
                        severity=service.settings.ml_event_severity,
                        message=(
                            f"ML anomaly score {ml_result.anomaly_score:.4f} "
                            f"> {ml_result.threshold:.4f} "
                            f"(model={ml_result.model_version})"
                        ),
                        event_value=ml_result.anomaly_score,
                        threshold_value=ml_result.threshold,
                        metadata={
                            "detector": "isolation_forest",
                            "model_version": ml_result.model_version,
                            "features": service.settings.ml_feature_list,
                        },
                    )
                )

    async with session_scope() as session:
        await device_repo.upsert_device(
            session,
            device_id=payload.device_id,
            firmware_version=payload.firmware_version,
        )
        inserted = False
        attempted_raw_insert = False
        decision = service.storage_policy.decide_reading_storage(
            event_triggering=bool(hits)
        )
        if decision.store_raw:
            attempted_raw_insert = True
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
        else:
            service.metrics.incr("readings.skipped_by_policy")

        if attempted_raw_insert and not inserted:
            service.metrics.incr("readings.duplicates")

        if ml_result is not None:
            await prediction_repo.insert_prediction(
                session,
                time=reading_time,
                device_id=payload.device_id,
                model_version=ml_result.model_version,
                prediction_type="anomaly",
                anomaly_score=ml_result.anomaly_score,
                predicted_label="anomaly" if ml_result.is_anomaly else "normal",
                metadata={
                    "threshold": ml_result.threshold,
                    "features": service.settings.ml_feature_list,
                    "rule_triggered": bool(
                        [h for h in hits if h.event_type != service.settings.ml_event_type]
                    ),
                },
            )

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
