"""Tests for the cloud-tier LSTM-AE verifier (Phase 3)."""
from __future__ import annotations

from pathlib import Path

import pytest

from cloud.app.verifier import CloudVerifier

_ARTIFACT = Path(__file__).resolve().parents[2] / "models" / "cloud_lstm_ae.npz"

pytestmark = pytest.mark.skipif(
    not _ARTIFACT.exists(),
    reason="cloud_lstm_ae.npz not built (run scripts/train_cloud_lstm.py)",
)


def _reading(v: float = 220.0, i: float = 5.0, p: float = 1100.0, t: float = 30.0) -> dict:
    return {
        "device_id": "house_0001",
        "voltage_v": v,
        "current_a": i,
        "power_w": p,
        "temperature_c": t,
    }


def test_verifier_loads() -> None:
    v = CloudVerifier(str(_ARTIFACT))
    assert v.available, v.reason
    assert v.version.startswith("lstm_ae")


def test_no_verdict_until_window_fills() -> None:
    v = CloudVerifier(str(_ARTIFACT))
    window = v._window
    for _ in range(window - 1):
        assert v.add(_reading()) == []
    verdicts = v.add(_reading())
    assert len(verdicts) == window
    for verdict in verdicts:
        assert set(verdict) == {"device_id", "recon_error", "threshold", "confirmed"}
        assert verdict["recon_error"] >= 0.0


def test_windows_are_per_device() -> None:
    v = CloudVerifier(str(_ARTIFACT))
    window = v._window
    # Interleave two devices; neither reaches a full window individually.
    for _ in range(window - 1):
        assert v.add(_reading()) == []
        assert v.add({**_reading(), "device_id": "house_0002"}) == []
    assert v.add(_reading()) != []  # house_0001 completes first
    assert v.add(_reading()) == []  # its buffer reset


def test_anomalous_window_confirmed() -> None:
    v = CloudVerifier(str(_ARTIFACT))
    window = v._window
    # A strongly anomalous window (undervoltage) should be confirmed.
    verdicts: list = []
    for _ in range(window):
        verdicts = v.add(_reading(v=180.0, p=1500.0)) or verdicts
    assert any(x["confirmed"] for x in verdicts)


def test_missing_artifact_disables_cleanly() -> None:
    v = CloudVerifier("models/does_not_exist.npz")
    assert not v.available
    assert v.add(_reading()) == []
