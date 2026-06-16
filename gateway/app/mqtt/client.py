"""Async MQTT client wrapper using aiomqtt."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

import aiomqtt

from ..config import get_settings
from ..logging_config import get_logger

logger = get_logger(__name__)


MessageHandler = Callable[[str, str, bytes], Awaitable[None]]


@asynccontextmanager
async def mqtt_client():
    """Yield a connected aiomqtt.Client, reconnecting on errors."""
    settings = get_settings()
    backoff = 1.0
    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_username or None,
                password=settings.mqtt_password or None,
                identifier=settings.mqtt_client_id,
                keepalive=settings.mqtt_keepalive,
            ) as client:
                topics = [
                    (settings.mqtt_telemetry_topic, settings.mqtt_qos_telemetry),
                    (settings.mqtt_status_topic, settings.mqtt_qos_status),
                    (settings.mqtt_events_topic, settings.mqtt_qos_events),
                ]
                await client.subscribe(topics)
                logger.info(
                    "mqtt_connected",
                    host=settings.mqtt_host,
                    port=settings.mqtt_port,
                    topics=[t for t, _ in topics],
                )
                backoff = 1.0
                yield client
                return
        except aiomqtt.MqttError as exc:
            logger.warning(
                "mqtt_connection_failed", error=str(exc), retry_in_s=round(backoff, 2)
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("mqtt_unexpected_error", error=str(exc))
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
