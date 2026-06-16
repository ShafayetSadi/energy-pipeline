"""Rule engine: load rules from YAML, evaluate against readings, return triggered events."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..config import get_settings
from ..logging_config import get_logger
from ..schemas.telemetry import TelemetryPayload

logger = get_logger(__name__)


@dataclass
class RuleHit:
    rule_name: str
    event_type: str
    severity: str
    message: str
    event_value: float | None = None
    threshold_value: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


_OPERATOR_MAP = {
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}


class RuleEngine:
    """Evaluates incoming readings against configured rules.

    Supports three rule types:
      * ``threshold`` - simple comparison on a single field.
      * ``percentage_increase`` - rolling-window spike detection.
      * ``heartbeat_timeout`` - device-level liveness check (handled separately
        by the heartbeat worker; kept here for unified config reload).
    """

    def __init__(self, rules_path: str | Path | None = None) -> None:
        self._settings = get_settings()
        self._rules_path = (
            Path(rules_path) if rules_path is not None else self._settings.rules_path
        )
        self._rules: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        # (device_id, field) -> deque[(ts_epoch, value)]
        self._window_state: dict[tuple[str, str], deque[tuple[float, float]]] = defaultdict(
            deque
        )
        self._last_alert_sent: dict[tuple[str, str], float] = {}
        self.load()

    def load(self) -> None:
        """Synchronously load rules from the configured YAML file."""
        path = self._rules_path
        if not path.exists():
            logger.warning("rules_file_missing", path=str(path))
            self._rules = {}
            return
        try:
            with path.open("r", encoding="utf-8") as f:
                payload = yaml.safe_load(f) or {}
        except Exception as exc:
            logger.error("rules_file_load_failed", path=str(path), error=str(exc))
            return
        rules = payload.get("rules", {}) if isinstance(payload, dict) else {}
        if not isinstance(rules, dict):
            logger.error("rules_file_invalid", path=str(path))
            return
        self._rules = rules
        logger.info("rules_loaded", count=len(self._rules), path=str(path))

    async def reload(self) -> None:
        async with self._lock:
            self.load()

    @property
    def rule_names(self) -> list[str]:
        return sorted(self._rules.keys())

    def get_rule(self, name: str) -> dict[str, Any] | None:
        return self._rules.get(name)

    def is_cooldown_active(
        self, dedup_key: tuple[str, str], *, cooldown_seconds: int | None = None
    ) -> bool:
        cooldown = (
            cooldown_seconds
            if cooldown_seconds is not None
            else self._settings.alert_cooldown_seconds
        )
        last = self._last_alert_sent.get(dedup_key)
        if last is None:
            return False
        return (time.monotonic() - last) < cooldown

    def mark_alert_sent(self, dedup_key: tuple[str, str]) -> None:
        self._last_alert_sent[dedup_key] = time.monotonic()

    async def evaluate(
        self, reading: TelemetryPayload, reading_received_at: float
    ) -> list[RuleHit]:
        """Evaluate a reading against all enabled rules."""
        async with self._lock:
            hits: list[RuleHit] = []
            for rule_name, rule_cfg in self._rules.items():
                if not rule_cfg.get("enabled", True):
                    continue
                condition = rule_cfg.get("condition", {}) or {}
                ctype = condition.get("type", "threshold")
                if ctype == "threshold":
                    hit = self._eval_threshold(rule_name, rule_cfg, reading)
                elif ctype == "percentage_increase":
                    hit = self._eval_percentage_increase(
                        rule_name, rule_cfg, reading, reading_received_at
                    )
                else:
                    continue
                if hit is not None:
                    hits.append(hit)
            return hits

    def _eval_threshold(
        self,
        rule_name: str,
        rule_cfg: dict[str, Any],
        reading: TelemetryPayload,
    ) -> RuleHit | None:
        condition = rule_cfg.get("condition", {}) or {}
        field_name = condition.get("field")
        operator = condition.get("operator")
        threshold = condition.get("value")
        if field_name is None or operator not in _OPERATOR_MAP or threshold is None:
            return None
        actual = getattr(reading, field_name, None)
        if actual is None:
            return None
        try:
            triggered = _OPERATOR_MAP[operator](float(actual), float(threshold))
        except (TypeError, ValueError):
            return None
        if not triggered:
            return None
        return RuleHit(
            rule_name=rule_name,
            event_type=rule_cfg.get("event_type", rule_name.upper()),
            severity=rule_cfg.get("severity", "WARNING"),
            message=(
                f"{field_name}={actual} {operator} {threshold} "
                f"(rule={rule_name})"
            ),
            event_value=float(actual),
            threshold_value=float(threshold),
            metadata={"field": field_name, "operator": operator},
        )

    def _eval_percentage_increase(
        self,
        rule_name: str,
        rule_cfg: dict[str, Any],
        reading: TelemetryPayload,
        received_at: float,
    ) -> RuleHit | None:
        condition = rule_cfg.get("condition", {}) or {}
        field_name = condition.get("field")
        percent = condition.get("percent")
        window = condition.get("window_seconds")
        if field_name is None or percent is None or window is None:
            return None
        actual = getattr(reading, field_name, None)
        if actual is None:
            return None
        key = (reading.device_id, field_name)
        state = self._window_state[key]
        # Prune old samples.
        cutoff = received_at - float(window)
        while state and state[0][0] < cutoff:
            state.popleft()
        if not state:
            state.append((received_at, float(actual)))
            return None
        baseline = state[0][1]
        if baseline <= 0:
            state.append((received_at, float(actual)))
            return None
        change = ((float(actual) - baseline) / baseline) * 100.0
        state.append((received_at, float(actual)))
        if change >= float(percent):
            return RuleHit(
                rule_name=rule_name,
                event_type=rule_cfg.get("event_type", rule_name.upper()),
                severity=rule_cfg.get("severity", "WARNING"),
                message=(
                    f"{field_name} jumped {change:.1f}% in {window}s "
                    f"(rule={rule_name})"
                ),
                event_value=float(actual),
                threshold_value=float(percent),
                metadata={
                    "field": field_name,
                    "window_seconds": int(window),
                    "percent_change": round(change, 2),
                    "baseline": baseline,
                },
            )
        return None

    def forget_device(self, device_id: str) -> None:
        """Drop rolling-window state for a device (e.g. on offline)."""
        for key in list(self._window_state.keys()):
            if key[0] == device_id:
                del self._window_state[key]
