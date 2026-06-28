"""Public ingestion service."""
from __future__ import annotations

import time

from ...config import get_settings
from ...db.repositories import quality as quality_repo
from ...db.session import session_scope
from ...logging_config import get_logger
from ..alert_service import AlertService
from ..metrics_service import MetricsService
from ..rule_engine import RuleEngine
from ..validation_service import ValidationService
from .device_events import handle_device_event
from .helpers import safe_text
from .status import handle_status
from .telemetry import handle_telemetry

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
        self.validator = validator
        self.rule_engine = rule_engine
        self.alert_service = alert_service
        self.metrics = metrics
        self.settings = get_settings()

    async def handle(
        self,
        *,
        topic: str,
        message_type: str,
        raw_payload: bytes | str,
    ) -> None:
        received_at = time.monotonic()
        ok, parsed, parse_err = self.validator.validate_json(raw_payload)
        if not ok or parsed is None:
            self.metrics.incr("validation.failures")
            await self.log_quality(
                topic=topic,
                device_id=None,
                error_type="invalid_json",
                error_message=parse_err,
                raw_payload=safe_text(raw_payload),
            )
            return

        if message_type == "telemetry":
            await handle_telemetry(self, topic, parsed, received_at)
        elif message_type == "status":
            await handle_status(self, topic, parsed, received_at)
        elif message_type == "events":
            await handle_device_event(self, topic, parsed, received_at)
        else:
            self.metrics.incr("messages.unsupported_type")
            logger.warning("unsupported_message_type", topic=topic, type=message_type)

    async def log_quality(
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
                await quality_repo.log_data_quality(
                    session,
                    topic=topic,
                    device_id=device_id,
                    error_type=error_type,
                    error_message=error_message,
                    raw_payload=raw_payload,
                )
        except Exception as exc:
            logger.warning("quality_log_write_failed", error=str(exc))
