"""Tests for RuleEngine."""
from __future__ import annotations

import asyncio
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

from gateway.app.schemas.telemetry import TelemetryPayload
from gateway.app.services.rule_engine import RuleEngine


def _telemetry(device_id: str, voltage: float, current: float, power: float) -> TelemetryPayload:
    return TelemetryPayload(
        schema_version="1.0",
        device_id=device_id,
        timestamp=datetime.now(UTC),
        voltage_v=voltage,
        current_a=current,
        power_w=power,
    )


def _make_engine(rules: dict) -> tuple[RuleEngine, Path]:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump({"rules": rules}, f)
        path = Path(f.name)
    return RuleEngine(rules_path=path), path


def test_threshold_lt_triggers() -> None:
    engine, _ = _make_engine(
        {
            "undervoltage": {
                "enabled": True,
                "event_type": "UNDER_VOLTAGE",
                "severity": "WARNING",
                "condition": {"type": "threshold", "field": "voltage_v", "operator": "lt", "value": 200},
            }
        }
    )
    hits = asyncio.run(engine.evaluate(_telemetry("d1", voltage=180.0, current=1.0, power=100.0), 0.0))
    assert len(hits) == 1
    assert hits[0].event_type == "UNDER_VOLTAGE"


def test_threshold_disabled_skipped() -> None:
    engine, _ = _make_engine(
        {
            "undervoltage": {
                "enabled": False,
                "event_type": "UNDER_VOLTAGE",
                "severity": "WARNING",
                "condition": {"type": "threshold", "field": "voltage_v", "operator": "lt", "value": 200},
            }
        }
    )
    hits = asyncio.run(engine.evaluate(_telemetry("d1", voltage=180.0, current=1.0, power=100.0), 0.0))
    assert hits == []


def test_percentage_increase_triggers() -> None:
    engine, _ = _make_engine(
        {
            "spike": {
                "enabled": True,
                "event_type": "POWER_SPIKE",
                "severity": "WARNING",
                "condition": {
                    "type": "percentage_increase",
                    "field": "power_w",
                    "percent": 30,
                    "window_seconds": 60,
                },
            }
        }
    )
    now = 100.0
    asyncio.run(engine.evaluate(_telemetry("d1", voltage=220, current=1.0, power=200.0), now))
    hits = asyncio.run(engine.evaluate(_telemetry("d1", voltage=220, current=1.5, power=400.0), now + 5))
    assert len(hits) == 1
    assert hits[0].event_type == "POWER_SPIKE"


def test_percentage_increase_no_trigger_below_threshold() -> None:
    engine, _ = _make_engine(
        {
            "spike": {
                "enabled": True,
                "event_type": "POWER_SPIKE",
                "severity": "WARNING",
                "condition": {
                    "type": "percentage_increase",
                    "field": "power_w",
                    "percent": 50,
                    "window_seconds": 60,
                },
            }
        }
    )
    asyncio.run(engine.evaluate(_telemetry("d1", voltage=220, current=1.0, power=200.0), 100.0))
    hits = asyncio.run(engine.evaluate(_telemetry("d1", voltage=220, current=1.1, power=240.0), 105.0))
    assert hits == []


def test_reload_picks_up_changes(tmp_path: Path) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "rules": {
                    "u": {
                        "enabled": True,
                        "event_type": "U",
                        "severity": "WARNING",
                        "condition": {"type": "threshold", "field": "voltage_v", "operator": "lt", "value": 200},
                    }
                }
            }
        )
    )
    engine = RuleEngine(rules_path=path)
    assert "u" in engine.rule_names

    path.write_text(
        yaml.safe_dump(
            {
                "rules": {
                    "o": {
                        "enabled": True,
                        "event_type": "O",
                        "severity": "CRITICAL",
                        "condition": {"type": "threshold", "field": "current_a", "operator": "gt", "value": 5},
                    }
                }
            }
        )
    )
    asyncio.run(engine.reload())
    assert "o" in engine.rule_names
    assert "u" not in engine.rule_names
