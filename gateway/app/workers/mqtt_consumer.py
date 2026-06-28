"""Background worker that consumes MQTT messages and dispatches them."""
from __future__ import annotations

import asyncio

from ..logging_config import get_logger
from ..mqtt.client import mqtt_client
from ..mqtt.handlers import handle_mqtt_message
from ..services.ingestion import IngestionService
from ..services.metrics_service import MetricsService

logger = get_logger(__name__)


class MQTTConsumerWorker:
    """Subscribes to MQTT topics and feeds the ingestion pipeline."""

    def __init__(
        self,
        *,
        ingestion: IngestionService,
        metrics: MetricsService,
    ) -> None:
        self._ingestion = ingestion
        self._metrics = metrics
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with mqtt_client() as client:
                    async for message in client.messages:
                        try:
                            payload = bytes(message.payload) if message.payload else b""
                            self._metrics.incr("messages.received")
                            await handle_mqtt_message(
                                self._ingestion, str(message.topic), payload
                            )
                        except Exception as exc:
                            self._metrics.incr("messages.handler_errors")
                            logger.exception(
                                "mqtt_handler_error", topic=str(message.topic), error=str(exc)
                            )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(
                    "mqtt_consumer_error", error=str(exc), retry_in_s=round(backoff, 2)
                )
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                except TimeoutError:
                    pass
                backoff = min(backoff * 2, 30.0)
                continue
        logger.info("mqtt_consumer_stopped")
