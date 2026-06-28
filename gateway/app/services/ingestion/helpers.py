"""Shared ingestion helpers."""
from __future__ import annotations

from typing import Any


def safe_text(raw: bytes | str | bytearray) -> str:
    if isinstance(raw, (bytes, bytearray)):
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return repr(raw)
    return str(raw)


def json_dumps(data: dict[str, Any]) -> str:
    import json

    try:
        return json.dumps(data, default=str)
    except Exception:
        return repr(data)


def topic_device_id(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) >= 3 and parts[0] == "energy":
        return parts[1]
    return None
