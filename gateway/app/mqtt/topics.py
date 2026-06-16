"""MQTT topic parsing for the energy/{device_id}/{type} convention."""
from __future__ import annotations

import re
from dataclasses import dataclass

_TOPIC_RE = re.compile(
    r"^energy/(?P<device_id>[^/]+)/(?P<message_type>[^/]+)$"
)


@dataclass(frozen=True)
class TopicParts:
    device_id: str
    message_type: str


def parse_topic(topic: str) -> TopicParts | None:
    """Return parsed device_id/message_type or None for non-matching topics."""
    if not topic:
        return None
    match = _TOPIC_RE.match(topic)
    if not match:
        return None
    return TopicParts(
        device_id=match.group("device_id"),
        message_type=match.group("message_type"),
    )


def is_supported_message_type(message_type: str) -> bool:
    return message_type in {"telemetry", "status", "events"}
