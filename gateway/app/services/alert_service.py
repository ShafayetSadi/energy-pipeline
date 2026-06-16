"""Alert manager: delivers CRITICAL/WARNING events to configured channels."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from ..config import get_settings
from ..db.models import AlertDelivery
from ..db.session import session_scope
from ..logging_config import get_logger
from .rule_engine import RuleHit

logger = get_logger(__name__)


@dataclass
class AlertMessage:
    event_id: int
    device_id: str | None
    event_type: str
    severity: str
    time: datetime
    message: str
    value: float | None
    threshold: float | None


class AlertService:
    """Dispatches alerts to console and webhook channels with cooldown dedup."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._dedup_keys: dict[tuple[str, str, str], float] = {}
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._settings.alert_webhook_url and self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_dedup_key(self, hit: RuleHit, device_id: str | None) -> tuple[str, str, str]:
        return (
            device_id or "unknown",
            hit.event_type,
            hit.severity,
        )

    def _cooldown_active(self, key: tuple[str, str, str]) -> bool:
        last = self._dedup_keys.get(key)
        if last is None:
            return False
        return (time.monotonic() - last) < self._settings.alert_cooldown_seconds

    def _mark_sent(self, key: tuple[str, str, str]) -> None:
        self._dedup_keys[key] = time.monotonic()

    async def maybe_alert(
        self,
        hit: RuleHit,
        event_id: int,
        device_id: str | None,
        event_time: datetime,
    ) -> bool:
        """Send an alert if the rule severity passes policy and is past cooldown."""
        settings = self._settings
        if not settings.enable_alerts:
            return False
        if settings.alert_critical_only and hit.severity != "CRITICAL":
            return False
        key = self._build_dedup_key(hit, device_id)
        async with self._lock:
            if self._cooldown_active(key):
                logger.info(
                    "alert_suppressed_cooldown",
                    key="|".join(key),
                    event_id=event_id,
                )
                return False
            self._mark_sent(key)

        message = AlertMessage(
            event_id=event_id,
            device_id=device_id,
            event_type=hit.event_type,
            severity=hit.severity,
            time=event_time,
            message=hit.message,
            value=hit.event_value,
            threshold=hit.threshold_value,
        )

        deliveries: list[tuple[str, str, str | None]] = []
        if settings.alert_console_enabled:
            deliveries.append(("console", "ok", None))
            logger.warning(
                "alert_console",
                event_id=event_id,
                device_id=device_id,
                event_type=hit.event_type,
                severity=hit.severity,
                message=hit.message,
                value=hit.event_value,
                threshold=hit.threshold_value,
            )
        if settings.alert_webhook_url:
            status, response = await self._send_webhook(message)
            deliveries.append(("webhook", status, response))

        await self._record_deliveries(event_id, deliveries)
        return True

    async def _send_webhook(self, message: AlertMessage) -> tuple[str, str | None]:
        if self._client is None:
            return ("error", "client_not_initialized")
        url = self._settings.alert_webhook_url
        payload: dict[str, Any] = {
            "event_id": message.event_id,
            "device_id": message.device_id,
            "event_type": message.event_type,
            "severity": message.severity,
            "time": message.time.isoformat(),
            "message": message.message,
            "value": message.value,
            "threshold": message.threshold,
        }
        try:
            resp = await self._client.post(
                url, json=payload, timeout=5.0
            )
            return (
                "ok" if resp.is_success else "error",
                f"status={resp.status_code} body={resp.text[:200]}",
            )
        except Exception as exc:
            return ("error", f"exception: {exc}")

    async def _record_deliveries(
        self, event_id: int, deliveries: list[tuple[str, str, str | None]]
    ) -> None:
        if not deliveries:
            return
        try:
            async with session_scope() as session:
                session.add_all(
                    [
                        AlertDelivery(event_id=event_id, channel=ch, status=st, response=resp)
                        for ch, st, resp in deliveries
                    ]
                )
        except Exception as exc:
            logger.warning("alert_delivery_record_failed", error=str(exc))


def event_time_for_storage(value: datetime) -> datetime:
    """Ensure tz-aware UTC datetime for storage."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def serialize_alert_payload(message: AlertMessage) -> str:
    return json.dumps(
        {
            "event_id": message.event_id,
            "device_id": message.device_id,
            "event_type": message.event_type,
            "severity": message.severity,
            "time": message.time.isoformat(),
            "message": message.message,
            "value": message.value,
            "threshold": message.threshold,
        }
    )
