"""Score-gated edge->cloud escalation worker (Phase 2).

The hybrid architecture's bandwidth claim rests on the gate implemented here:
instead of streaming every reading to the cloud, the edge forwards only the
readings whose anomaly score crosses the escalation threshold. The naive
baseline ("all" mode) forwards every scored reading through the exact same
path, so a gated-versus-all run isolates the gate as the only variable.

The ML scoring worker enqueues candidate readings after scoring; this worker
drains them in batches and POSTs a JSON envelope to the cloud tier. Payload
bytes are counted on send (``cloud.bytes_sent``) so bandwidth can be compared
against the cloud tier's own received counters. Failures are counted and the
batch dropped (no retry queue) — detection at the edge never depends on the
cloud being reachable.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime

import httpx

from ..config import Settings, get_settings
from ..logging_config import get_logger
from ..schemas.telemetry import TelemetryPayload
from ..services.anomaly_detector import AnomalyResult
from ..services.metrics_service import MetricsService

logger = get_logger(__name__)


@dataclass
class EscalationJob:
    reading: TelemetryPayload
    reading_time: datetime
    result: AnomalyResult
    rule_fired: bool


class CloudForwarderWorker:
    """Forwards escalated readings to the cloud tier in batches."""

    def __init__(
        self, *, metrics: MetricsService, settings: Settings | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._metrics = metrics
        self._queue: asyncio.Queue[EscalationJob] = asyncio.Queue(
            maxsize=self._settings.cloud_forward_queue_max_size
        )
        self._client: httpx.AsyncClient | None = None
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    @property
    def enabled(self) -> bool:
        return self._settings.cloud_forward_mode != "off"

    def should_escalate(self, result: AnomalyResult) -> bool:
        """Apply the escalation gate to a scored reading."""
        mode = self._settings.cloud_forward_mode
        if mode == "all":
            return True
        if mode != "gated":
            return False
        override = self._settings.cloud_escalation_threshold
        if override is not None:
            return result.anomaly_score >= override
        return result.is_anomaly

    def enqueue(self, job: EscalationJob) -> None:
        """Non-blocking enqueue; drops (and counts) if the queue is full."""
        if not self.enabled:
            return
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            self._metrics.incr("cloud.dropped")

    async def start(self) -> None:
        if not self.enabled:
            return
        if self._task is None:
            if self._client is None:  # a test may inject its own client
                self._client = httpx.AsyncClient(
                    timeout=self._settings.cloud_forward_timeout_seconds
                )
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
        # Best-effort flush of anything still queued.
        leftover: list[EscalationJob] = []
        while True:
            try:
                leftover.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if leftover and self._client is not None:
            await self._send_batch(leftover)
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _loop(self) -> None:
        while not self._stop.is_set():
            batch = await self._collect_batch()
            if batch:
                await self._send_batch(batch)

    async def _collect_batch(self) -> list[EscalationJob]:
        try:
            first = await asyncio.wait_for(self._queue.get(), timeout=0.5)
        except TimeoutError:
            return []
        batch = [first]
        window = self._settings.cloud_forward_batch_window_ms / 1000.0
        deadline = time.monotonic() + window
        while len(batch) < self._settings.cloud_forward_batch_max_size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                batch.append(await asyncio.wait_for(self._queue.get(), timeout=remaining))
            except TimeoutError:
                break
        return batch

    def _serialize(self, batch: list[EscalationJob]) -> bytes:
        envelope = {
            "source": self._settings.service_name,
            "mode": self._settings.cloud_forward_mode,
            "readings": [
                {
                    "device_id": job.reading.device_id,
                    "timestamp": job.reading.timestamp.isoformat(),
                    "reading_time": job.reading_time.isoformat(),
                    "voltage_v": job.reading.voltage_v,
                    "current_a": job.reading.current_a,
                    "power_w": job.reading.power_w,
                    "temperature_c": job.reading.temperature_c,
                    "anomaly_score": job.result.anomaly_score,
                    "threshold": job.result.threshold,
                    "model_version": job.result.model_version,
                    "rule_fired": job.rule_fired,
                }
                for job in batch
            ],
        }
        return json.dumps(envelope, separators=(",", ":")).encode("utf-8")

    async def _send_batch(self, batch: list[EscalationJob]) -> None:
        if self._client is None:  # pragma: no cover - defensive
            return
        body = self._serialize(batch)
        send_start = time.monotonic()
        try:
            response = await self._client.post(
                self._settings.cloud_endpoint_url,
                content=body,
                headers={"content-type": "application/json"},
            )
            response.raise_for_status()
        except Exception as exc:
            self._metrics.incr("cloud.forward_failed")
            logger.warning(
                "cloud_forward_failed", error=str(exc), readings=len(batch)
            )
            return
        self._metrics.record_latency(
            "cloud_forward", (time.monotonic() - send_start) * 1000.0
        )
        self._metrics.incr("cloud.batches")
        self._metrics.incr("cloud.forwarded", len(batch))
        self._metrics.incr("cloud.bytes_sent", len(body))
