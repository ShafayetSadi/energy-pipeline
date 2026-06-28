"""Device heartbeat monitor: detects devices that have stopped reporting."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from ..config import get_settings
from ..db.repositories import devices as device_repo
from ..db.repositories import events as event_repo
from ..db.repositories import status as status_repo
from ..db.session import session_scope
from ..logging_config import get_logger
from ..services.alert_service import AlertService
from ..services.metrics_service import MetricsService
from ..services.rule_engine import RuleEngine, RuleHit

logger = get_logger(__name__)


class DeviceHeartbeatWorker:
    """Periodically marks devices offline if no telemetry has arrived within
    the configured timeout window. Triggers a CRITICAL DEVICE_FAILURE event.
    """

    def __init__(
        self,
        *,
        rule_engine: RuleEngine,
        alert_service: AlertService,
        metrics: MetricsService,
    ) -> None:
        self._rule_engine = rule_engine
        self._alert_service = alert_service
        self._metrics = metrics
        self._settings = get_settings()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        interval = self._settings.heartbeat_check_interval_seconds
        timeout = self._settings.heartbeat_timeout_seconds
        while not self._stop.is_set():
            try:
                await self._check_once(timeout)
            except Exception as exc:  # pragma: no cover
                logger.warning("heartbeat_check_failed", error=str(exc))
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except TimeoutError:
                continue
        logger.info("heartbeat_worker_stopped")

    async def _check_once(self, timeout_seconds: int) -> None:
        async with session_scope() as session:
            devices = await device_repo.list_devices(session, limit=10_000)
        now = datetime.now(UTC)
        for device in devices:
            last_seen = device.last_seen_at
            if last_seen is None:
                continue
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=UTC)
            if device.status in {"offline", "maintenance"}:
                continue
            age = (now - last_seen).total_seconds()
            if age < timeout_seconds:
                continue
            await self._mark_offline(device.device_id, age, last_seen)

    async def _mark_offline(
        self, device_id: str, age: float, last_seen: datetime
    ) -> None:
        dedup_key = (device_id, "DEVICE_FAILURE")
        if self._rule_engine.is_cooldown_active(dedup_key):
            return
        logger.warning("device_offline_detected", device_id=device_id, age_s=age)
        async with session_scope() as session:
            await device_repo.update_device_status(
                session, device_id=device_id, status="offline", last_seen_at=last_seen
            )
            await status_repo.record_status_history(
                session,
                time=datetime.now(UTC),
                device_id=device_id,
                status="offline",
                firmware_version=None,
                ip_address=None,
                rssi_dbm=None,
                metadata={"reason": "heartbeat_timeout", "last_seen": last_seen.isoformat()},
            )
            event = await event_repo.insert_event(
                session,
                time=datetime.now(UTC),
                device_id=device_id,
                event_type="DEVICE_FAILURE",
                severity="CRITICAL",
                rule_name="device_offline_heartbeat",
                message=f"Device {device_id} silent for {age:.0f}s (timeout={self._settings.heartbeat_timeout_seconds}s)",
                reading_time=None,
                event_value=None,
                threshold_value=float(self._settings.heartbeat_timeout_seconds),
                metadata={"last_seen": last_seen.isoformat(), "age_seconds": age},
            )
            event_id = event.event_id  # type: ignore[attr-defined]
            event_time = event.time  # type: ignore[attr-defined]
        self._rule_engine.mark_alert_sent(dedup_key)
        self._metrics.incr("events.critical")
        self._metrics.incr("events.type.device_failure")
        self._metrics.incr("devices.offline_detected")
        hit = RuleHit(
            rule_name="device_offline_heartbeat",
            event_type="DEVICE_FAILURE",
            severity="CRITICAL",
            message=f"Device {device_id} heartbeat timeout",
            event_value=age,
            threshold_value=float(self._settings.heartbeat_timeout_seconds),
            metadata={"last_seen": last_seen.isoformat()},
        )
        await self._alert_service.maybe_alert(
            hit, event_id=event_id, device_id=device_id, event_time=event_time
        )
        self._rule_engine.forget_device(device_id)
