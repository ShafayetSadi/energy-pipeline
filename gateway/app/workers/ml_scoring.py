"""Async micro-batch worker for edge ML anomaly scoring.

Scoring is moved off the inline telemetry ingestion path into this worker so
that (a) ML inference does not inflate telemetry processing latency, and
(b) readings are scored in batches, which amortizes scikit-learn's large
per-call overhead (per-sample scoring is ~700x slower per row than batched).

The telemetry handler enqueues a lightweight job per reading; this worker
drains the queue in batches (bounded by size or a short time window), scores
the batch in one model call, persists each score to ``model_predictions``, and
raises ``ML_ANOMALY`` events for flagged readings (subject to the per-device
cooldown), exactly as the inline path did.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime

from ..config import get_settings
from ..db.repositories import events as event_repo
from ..db.repositories import predictions as prediction_repo
from ..db.session import session_scope
from ..logging_config import get_logger
from ..schemas.telemetry import TelemetryPayload
from ..services.alert_service import AlertService
from ..services.anomaly_detector import AnomalyDetector
from ..services.metrics_service import MetricsService
from ..services.rule_engine import RuleEngine, RuleHit

logger = get_logger(__name__)


@dataclass
class ScoringJob:
    reading: TelemetryPayload
    reading_time: datetime
    rule_fired: bool
    enqueued_at: float  # time.monotonic() at enqueue


class MLScoringWorker:
    """Drains a queue of readings and scores them in micro-batches."""

    def __init__(
        self,
        *,
        detector: AnomalyDetector,
        rule_engine: RuleEngine,
        alert_service: AlertService,
        metrics: MetricsService,
    ) -> None:
        self._settings = get_settings()
        self._detector = detector
        self._rule_engine = rule_engine
        self._alert_service = alert_service
        self._metrics = metrics
        self._queue: asyncio.Queue[ScoringJob] = asyncio.Queue(
            maxsize=self._settings.ml_queue_max_size
        )
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    @property
    def enabled(self) -> bool:
        return (
            self._settings.enable_ml
            and self._settings.ml_async_scoring
            and self._detector.available
        )

    def enqueue(self, job: ScoringJob) -> None:
        """Non-blocking enqueue; drops (and counts) if the queue is full."""
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            self._metrics.incr("ml.dropped")

    def enqueue_reading(
        self, reading: TelemetryPayload, reading_time: datetime, *, rule_fired: bool
    ) -> None:
        """Enqueue a reading for async scoring (called from the telemetry path)."""
        self.enqueue(
            ScoringJob(
                reading=reading,
                reading_time=reading_time,
                rule_fired=rule_fired,
                enqueued_at=time.monotonic(),
            )
        )

    async def start(self) -> None:
        if not self.enabled:
            return
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
        # Best-effort drain of anything still queued.
        await self._drain_remaining()

    async def _loop(self) -> None:
        while not self._stop.is_set():
            batch = await self._collect_batch()
            if batch:
                try:
                    await self._process_batch(batch)
                except Exception as exc:  # pragma: no cover - best effort
                    logger.warning("ml_scoring_batch_failed", error=str(exc))

    async def _collect_batch(self) -> list[ScoringJob]:
        try:
            first = await asyncio.wait_for(self._queue.get(), timeout=0.5)
        except TimeoutError:
            return []
        batch = [first]
        window = self._settings.ml_batch_window_ms / 1000.0
        deadline = time.monotonic() + window
        while len(batch) < self._settings.ml_batch_max_size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                batch.append(await asyncio.wait_for(self._queue.get(), timeout=remaining))
            except TimeoutError:
                break
        return batch

    async def _drain_remaining(self) -> None:
        leftover: list[ScoringJob] = []
        while True:
            try:
                leftover.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if leftover:
            try:
                await self._process_batch(leftover)
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning("ml_scoring_drain_failed", error=str(exc))

    async def _process_batch(self, batch: list[ScoringJob]) -> None:
        process_start = time.monotonic()
        results = self._detector.score_many([job.reading for job in batch])
        batch_ms = (time.monotonic() - process_start) * 1000.0
        per_row_ms = batch_ms / max(len(batch), 1)
        self._metrics.incr("ml.batches")

        emit = self._settings.ml_emit_events
        pending_alerts: list[tuple[RuleHit, int, str, datetime]] = []
        async with session_scope() as session:
            for job, result in zip(batch, results, strict=True):
                # Per-reading amortized inference + queue-wait latency.
                self._metrics.record_latency("ml_inference", per_row_ms)
                self._metrics.record_latency(
                    "ml_queue", (process_start - job.enqueued_at) * 1000.0
                )
                if result is None:
                    continue
                self._metrics.incr("ml.scored")
                payload = job.reading
                await prediction_repo.insert_prediction(
                    session,
                    time=job.reading_time,
                    device_id=payload.device_id,
                    model_version=result.model_version,
                    prediction_type="anomaly",
                    anomaly_score=result.anomaly_score,
                    predicted_label="anomaly" if result.is_anomaly else "normal",
                    metadata={
                        "threshold": result.threshold,
                        "features": self._settings.ml_feature_list,
                        "rule_triggered": job.rule_fired,
                    },
                )
                if not result.is_anomaly:
                    continue
                self._metrics.incr("ml.anomalies")
                dedup = (payload.device_id, self._settings.ml_event_type)
                if not emit or self._rule_engine.is_cooldown_active(dedup):
                    continue
                self._rule_engine.mark_alert_sent(dedup)
                hit = RuleHit(
                    rule_name="ml_isolation_forest",
                    event_type=self._settings.ml_event_type,
                    severity=self._settings.ml_event_severity,
                    message=(
                        f"ML anomaly score {result.anomaly_score:.4f} "
                        f"> {result.threshold:.4f} (model={result.model_version})"
                    ),
                    event_value=result.anomaly_score,
                    threshold_value=result.threshold,
                    metadata={
                        "detector": "isolation_forest",
                        "model_version": result.model_version,
                        "features": self._settings.ml_feature_list,
                    },
                )
                event = await event_repo.insert_event(
                    session,
                    time=job.reading_time,
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
                pending_alerts.append(
                    (hit, event.event_id, payload.device_id, job.reading_time)
                )

        for hit, event_id, device_id, event_time in pending_alerts:
            await self._alert_service.maybe_alert(
                hit, event_id=event_id, device_id=device_id, event_time=event_time
            )
