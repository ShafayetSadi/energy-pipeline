"""Edge ML anomaly detector (Isolation Forest).

Phase 1 of the hybrid edge/cloud direction: a lightweight unsupervised anomaly
detector that scores each telemetry reading at the edge, alongside (or instead
of) the rule engine. The model is trained offline by
``scripts/train_anomaly_model.py`` and loaded here from a joblib artifact.

The detector is intentionally defensive: if ML is disabled, the artifact is
missing, or the scientific stack is not installed, it disables itself and the
ingestion pipeline continues unchanged. This keeps the default/baseline path
free of any ML dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..config import Settings, get_settings
from ..logging_config import get_logger

if TYPE_CHECKING:
    from ..schemas.telemetry import TelemetryPayload

logger = get_logger(__name__)


@dataclass(frozen=True)
class AnomalyResult:
    """Outcome of scoring a single reading."""

    anomaly_score: float
    is_anomaly: bool
    model_version: str
    threshold: float


class AnomalyDetector:
    """Loads an Isolation Forest artifact and scores readings.

    The artifact is a dict bundled by the training script::

        {
            "model": IsolationForest,
            "scaler": StandardScaler | None,
            "features": ["voltage_v", "current_a", "power_w", "temperature_c"],
            "threshold": float,      # anomaly_score above this == anomaly
            "version": "iforest_v1",
            "metadata": {...},
        }

    ``anomaly_score`` is defined as ``-model.score_samples(x)`` so that higher
    means more anomalous (matches the intuition in Sathupadi et al. and the
    threshold framing in Mofidul et al.).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._model: Any = None
        self._scaler: Any = None
        self._features: list[str] = self._settings.ml_feature_list
        self._engineering: str = "none"
        self._nominal_voltage: float = 220.0
        self._threshold: float = 0.0
        self._version: str = self._settings.ml_model_version
        self._loaded = False
        self._disabled = not self._settings.enable_ml
        if not self._disabled:
            self._load()

    @property
    def available(self) -> bool:
        return self._loaded and not self._disabled

    @property
    def version(self) -> str:
        return self._version

    def _disable(self, reason: str, **kw: Any) -> None:
        self._disabled = True
        logger.warning("ml_detector_disabled", reason=reason, **kw)

    def _load(self) -> None:
        path = Path(self._settings.ml_model_path)
        if not path.exists():
            self._disable("model_artifact_missing", path=str(path))
            return
        try:
            import joblib  # lazy: only needed when ML is enabled
        except ImportError as exc:
            self._disable("joblib_not_installed", error=str(exc))
            return
        try:
            bundle = joblib.load(path)
        except Exception as exc:  # pragma: no cover - corrupt artifact
            self._disable("model_load_failed", path=str(path), error=str(exc))
            return

        self._model = bundle.get("model")
        if self._model is None:
            self._disable("model_artifact_invalid", path=str(path))
            return
        self._scaler = bundle.get("scaler")
        self._features = bundle.get("features") or self._features
        self._engineering = bundle.get("engineering") or "none"
        self._nominal_voltage = float(bundle.get("nominal_voltage", 220.0))
        self._version = bundle.get("version") or self._version
        # Config threshold overrides the artifact threshold when provided.
        if self._settings.ml_score_threshold is not None:
            self._threshold = float(self._settings.ml_score_threshold)
        else:
            self._threshold = float(bundle.get("threshold", 0.0))
        self._loaded = True
        logger.info(
            "ml_detector_loaded",
            path=str(path),
            version=self._version,
            features=self._features,
            engineering=self._engineering,
            threshold=self._threshold,
        )

    def _feature_vector(self, reading: TelemetryPayload) -> list[float] | None:
        values: list[float] = []
        for name in self._features:
            val = getattr(reading, name, None)
            if val is None:
                return None  # cannot score readings with missing features
            try:
                values.append(float(val))
            except (TypeError, ValueError):
                return None
        return values

    def _apply_engineering(self, vector: list[float]) -> list[float]:
        """Append physics-informed features. Must match scripts/train_anomaly_model.py
        ``engineer()`` for the ``physics_v1`` tag. Assumes the base feature order
        ``[voltage_v, current_a, power_w, temperature_c]``."""
        if self._engineering != "physics_v1":
            return vector
        voltage, current, power = vector[0], vector[1], vector[2]
        voltage_dev = abs(voltage - self._nominal_voltage)
        power_discrepancy = power - (voltage * current)
        return [*vector, voltage_dev, power_discrepancy]

    def score(self, reading: TelemetryPayload) -> AnomalyResult | None:
        """Score one reading. Returns ``None`` when the detector is unavailable
        or the reading lacks the required features."""
        if not self.available:
            return None
        vector = self._feature_vector(reading)
        if vector is None:
            return None
        vector = self._apply_engineering(vector)
        try:
            x: Any = [vector]
            if self._scaler is not None:
                x = self._scaler.transform(x)
            # score_samples: higher == more normal. Negate so higher == anomalous.
            anomaly_score = float(-self._model.score_samples(x)[0])
        except Exception as exc:  # pragma: no cover - runtime scoring guard
            logger.warning("ml_score_failed", error=str(exc))
            return None
        return AnomalyResult(
            anomaly_score=anomaly_score,
            is_anomaly=anomaly_score > self._threshold,
            model_version=self._version,
            threshold=self._threshold,
        )
