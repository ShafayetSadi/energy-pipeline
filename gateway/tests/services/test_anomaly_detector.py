"""Tests for the edge Isolation Forest anomaly detector."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from gateway.app.config import Settings
from gateway.app.schemas.telemetry import TelemetryPayload
from gateway.app.services.anomaly_detector import AnomalyDetector

# Path to the artifact produced by scripts/train_anomaly_model.py.
_ARTIFACT = Path(__file__).resolve().parents[3] / "models" / "anomaly_iforest.joblib"


def _telemetry(voltage: float, current: float, power: float, temp: float = 30.0) -> TelemetryPayload:
    return TelemetryPayload(
        schema_version="1.0",
        device_id="house_0001",
        timestamp=datetime.now(UTC),
        voltage_v=voltage,
        current_a=current,
        power_w=power,
        temperature_c=temp,
    )


def test_detector_disabled_when_ml_off() -> None:
    detector = AnomalyDetector(Settings(enable_ml=False))
    assert not detector.available
    assert detector.score(_telemetry(220.0, 2.0, 440.0)) is None


def test_detector_disables_gracefully_when_artifact_missing(tmp_path: Path) -> None:
    detector = AnomalyDetector(
        Settings(enable_ml=True, ml_model_path=str(tmp_path / "does_not_exist.joblib"))
    )
    assert not detector.available
    assert detector.score(_telemetry(220.0, 2.0, 440.0)) is None


@pytest.mark.skipif(not _ARTIFACT.exists(), reason="model artifact not trained")
def test_detector_flags_voltage_anomaly_not_normal() -> None:
    detector = AnomalyDetector(Settings(enable_ml=True, ml_model_path=str(_ARTIFACT)))
    assert detector.available

    # Normal reading near the operating envelope.
    normal = detector.score(_telemetry(220.0, 2.0, 440.0))
    # Clear overvoltage excursion (out of the 220 +/- envelope).
    anomalous = detector.score(_telemetry(262.0, 6.8, 1500.0))

    assert normal is not None and anomalous is not None
    assert anomalous.anomaly_score > normal.anomaly_score
    assert anomalous.is_anomaly
