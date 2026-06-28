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
from ..db.repositories import alert_outbox as outbox_repo
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
    """Applies alert policy and enqueues durable alert delivery work."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._dedup_keys: dict[tuple[str, str, str], float] = {}
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        has_channel = self._settings.alert_webhook_url or self._settings.alert_slack_webhook_url
        if has_channel and self._client is None:
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
        """Enqueue alert deliveries if severity passes policy and is past cooldown."""
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

        channels = self._configured_channels()
        if not channels:
            return False

        if not settings.alert_outbox_enabled:
            deliveries = await self._send_to_channels(message, channels)
            await self._record_deliveries(event_id, deliveries)
            return True

        payload = self._payload(message)
        try:
            async with session_scope() as session:
                for channel in channels:
                    await outbox_repo.enqueue_alert(
                        session,
                        event_id=event_id,
                        channel=channel,
                        payload=payload,
                    )
        except Exception as exc:
            logger.warning("alert_outbox_enqueue_failed", event_id=event_id, error=str(exc))
            return False
        return True

    def _configured_channels(self) -> list[str]:
        channels: list[str] = []
        if self._settings.alert_console_enabled:
            channels.append("console")
        if self._settings.alert_webhook_url:
            channels.append("webhook")
        if self._settings.alert_slack_webhook_url:
            channels.append("slack")
        return channels

    async def deliver_outbox_message(
        self, channel: str, payload: dict[str, Any]
    ) -> tuple[str, str | None]:
        message = AlertMessage(
            event_id=int(payload["event_id"]),
            device_id=payload.get("device_id"),
            event_type=str(payload["event_type"]),
            severity=str(payload["severity"]),
            time=datetime.fromisoformat(str(payload["time"])),
            message=str(payload["message"]),
            value=payload.get("value"),
            threshold=payload.get("threshold"),
        )
        if channel == "console":
            logger.warning(
                "alert_console",
                event_id=message.event_id,
                device_id=message.device_id,
                event_type=message.event_type,
                severity=message.severity,
                message=message.message,
                value=message.value,
                threshold=message.threshold,
            )
            return ("ok", None)
        if channel == "webhook":
            return await self._send_webhook(message)
        if channel == "slack":
            return await self._send_slack(message)
        return ("error", f"unknown_channel={channel}")

    def _payload(self, message: AlertMessage) -> dict[str, Any]:
        return {
            "event_id": message.event_id,
            "device_id": message.device_id,
            "event_type": message.event_type,
            "severity": message.severity,
            "time": message.time.isoformat(),
            "message": message.message,
            "value": message.value,
            "threshold": message.threshold,
        }

    async def _record_deliveries(
        self, event_id: int, deliveries: list[tuple[str, str, str | None]]
    ) -> None:
        if not deliveries:
            return
        try:
            async with session_scope() as session:
                for channel, status, response in deliveries:
                    await outbox_repo.record_delivery(
                        session,
                        event_id=event_id,
                        channel=channel,
                        status=status,
                        response=response,
                    )
        except Exception as exc:
            logger.warning("alert_delivery_record_failed", error=str(exc))

    async def _send_to_channels(
        self, message: AlertMessage, channels: list[str]
    ) -> list[tuple[str, str, str | None]]:
        deliveries: list[tuple[str, str, str | None]] = []
        if "console" in channels:
            deliveries.append(("console", "ok", None))
            logger.warning(
                "alert_console",
                event_id=message.event_id,
                device_id=message.device_id,
                event_type=message.event_type,
                severity=message.severity,
                message=message.message,
                value=message.value,
                threshold=message.threshold,
            )
        if "webhook" in channels:
            status, response = await self._send_webhook(message)
            deliveries.append(("webhook", status, response))
        if "slack" in channels:
            status, response = await self._send_slack(message)
            deliveries.append(("slack", status, response))
        return deliveries

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

    async def _send_slack(self, message: AlertMessage) -> tuple[str, str | None]:
        if self._client is None:
            return ("error", "client_not_initialized")
        url = self._settings.alert_slack_webhook_url
        text = (
            f":rotating_light: *{message.severity}* `{message.event_type}` "
            f"on `{message.device_id or 'unknown'}`\n"
            f"{message.message}"
        )
        if message.value is not None and message.threshold is not None:
            text += f"\nvalue=`{message.value}` threshold=`{message.threshold}`"
        text += f"\n_event_id={message.event_id} time={message.time.isoformat()}_"
        try:
            resp = await self._client.post(url, json={"text": text}, timeout=5.0)
            return (
                "ok" if resp.is_success else "error",
                f"status={resp.status_code} body={resp.text[:200]}",
            )
        except Exception as exc:
            return ("error", f"exception: {exc}")


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
