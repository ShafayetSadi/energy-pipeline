"""Dispatches MQTT messages to the ingestion service based on topic type."""
from __future__ import annotations

from ..logging_config import get_logger
from ..services.ingestion_service import IngestionService
from .topics import is_supported_message_type, parse_topic

logger = get_logger(__name__)


async def handle_mqtt_message(
    ingestion: IngestionService,
    topic: str,
    payload: bytes,
) -> None:
    """Route one MQTT message into the ingestion pipeline."""
    parts = parse_topic(topic)
    if parts is None:
        logger.warning("mqtt_topic_unparseable", topic=topic)
        return
    if not is_supported_message_type(parts.message_type):
        logger.debug("mqtt_message_type_skipped", topic=topic, type=parts.message_type)
        return
    await ingestion.handle(topic=topic, message_type=parts.message_type, raw_payload=payload)
