"""Cloud-tier LSTM autoencoder verifier (Phase 3), numpy-only inference.

The edge escalates readings its Isolation Forest flags; this verifier
re-examines them with a heavier model that learned normal telemetry dynamics
offline. A reading whose reconstruction error exceeds the trained threshold is
*confirmed* anomalous; a well-reconstructed reading is treated as a likely edge
false positive. Weights come from ``models/cloud_lstm_ae.npz`` exported by
``scripts/train_cloud_lstm.py``; the forward pass here is the parity-checked
twin of that script's numpy kernel, so no torch is needed in the container.

The verifier buffers readings per device and scores a window once it fills,
mirroring how the edge batches escalations. It disables itself cleanly if the
artifact or numpy is unavailable, so the receiver keeps working as in Phase 2.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

NOMINAL_VOLTAGE = 220.0


def _sigmoid(x: Any) -> Any:
    import numpy as np

    return 1.0 / (1.0 + np.exp(-x))


def _lstm_forward(seq, w_ih, w_hh, b_ih, b_hh, hidden):
    import numpy as np

    h = np.zeros(hidden)
    c = np.zeros(hidden)
    outs = np.empty((seq.shape[0], hidden))
    for t in range(seq.shape[0]):
        g = w_ih @ seq[t] + b_ih + w_hh @ h + b_hh
        i = _sigmoid(g[:hidden])
        f = _sigmoid(g[hidden : 2 * hidden])
        gg = np.tanh(g[2 * hidden : 3 * hidden])
        o = _sigmoid(g[3 * hidden :])
        c = f * c + i * gg
        h = o * np.tanh(c)
        outs[t] = h
    return outs


class CloudVerifier:
    """Windowed LSTM-AE reconstruction verifier over escalated readings."""

    def __init__(self, model_path: str = "models/cloud_lstm_ae.npz") -> None:
        self._ok = False
        self._buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=self._window))
        self._window = 8
        self.reason = ""
        self._load(model_path)

    @property
    def available(self) -> bool:
        return self._ok

    @property
    def version(self) -> str:
        return self._meta.get("version", "unknown") if self._ok else "disabled"

    def _load(self, model_path: str) -> None:
        path = Path(model_path)
        if not path.exists():
            self.reason = f"artifact_missing:{path}"
            return
        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - numpy always present
            self.reason = f"numpy_missing:{exc}"
            return
        try:
            data = np.load(path, allow_pickle=False)
            self._p = {k: data[k] for k in data.files if k not in ("meta",)}
            self._meta = json.loads(str(np.load(path, allow_pickle=True)["meta"]))
        except Exception as exc:  # pragma: no cover - corrupt artifact
            self.reason = f"load_failed:{exc}"
            return
        self._window = int(self._meta.get("window", 8))
        self._hidden = int(self._meta.get("hidden", self._p["hidden"]))
        self._threshold = float(self._meta.get("threshold", self._p["threshold"]))
        self._mean = self._p["mean"]
        self._std = self._p["std"]
        self._ok = True

    def _features(self, r: dict[str, Any]):
        import numpy as np

        v, i, p = float(r["voltage_v"]), float(r["current_a"]), float(r["power_w"])
        t = float(r.get("temperature_c") or 0.0)
        return np.array([v, i, p, t, abs(v - NOMINAL_VOLTAGE), p - v * i])

    def _reconstruct(self, z):
        p = self._p
        h = self._hidden
        enc = _lstm_forward(z, p["enc_w_ih"], p["enc_w_hh"], p["enc_b_ih"], p["enc_b_hh"], h)
        import numpy as np

        dec_in = np.tile(enc[-1], (z.shape[0], 1))
        dec = _lstm_forward(dec_in, p["dec_w_ih"], p["dec_w_hh"], p["dec_b_ih"], p["dec_b_hh"], h)
        return dec @ p["out_w"].T + p["out_b"]

    def add(self, reading: dict[str, Any]) -> list[dict[str, Any]]:
        """Buffer one escalated reading; return verdicts when a window fills.

        Each verdict is ``{device_id, recon_error, threshold, confirmed}``.
        Returns an empty list until the device has ``window`` readings.
        """
        if not self._ok:
            return []
        import numpy as np

        buf = self._buffers[reading["device_id"]]
        buf.append(reading)
        if len(buf) < self._window:
            return []
        window = list(buf)
        buf.clear()
        feats = np.stack([self._features(r) for r in window])
        z = (feats - self._mean) / self._std
        recon = self._reconstruct(z)
        errs = np.mean((recon - z) ** 2, axis=1)
        return [
            {
                "device_id": r["device_id"],
                "recon_error": float(e),
                "threshold": self._threshold,
                "confirmed": bool(e > self._threshold),
            }
            for r, e in zip(window, errs, strict=True)
        ]
