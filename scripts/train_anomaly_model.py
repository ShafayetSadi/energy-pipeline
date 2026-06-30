#!/usr/bin/env python3
"""Train and evaluate the edge Isolation Forest anomaly detector (Phase 1).

The detector scores telemetry readings and flags points whose anomaly score
exceeds a threshold derived from the training distribution (a quantile of the
normal-data scores) -- the same threshold framing used in Mofidul et al.
(Isolation Forest) and Sathupadi et al. (score > mu + alpha*sigma).

It scores *physics-informed* features (paper 4's edge feature-extraction idea):

    [ voltage_v, current_a, power_w, temperature_c,
      |voltage_v - V_nominal|,            # voltage excursion
      power_w - voltage_v*current_a ]     # P vs implied apparent power (consistency)

The two engineered features let the model flag voltage excursions and
voltage/current/power inconsistencies that the raw values alone dilute across
Isolation Forest's random splits. The same transform is applied in the gateway
detector (gateway/app/services/anomaly_detector.py).

Training/eval data mirrors simulator/mqtt_publisher.py so the offline model
matches what the live gateway receives, including the simulator's behaviour of
overriding *only* the anomaly field (leaving other features at normal values).

Usage:
    uv run python scripts/train_anomaly_model.py            # train + save artifact
    uv run python scripts/train_anomaly_model.py --evaluate # also report metrics
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from joblib import dump
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

# Base features pulled directly from each telemetry reading.
FEATURES = ["voltage_v", "current_a", "power_w", "temperature_c"]
ENGINEERING = "physics_v1"  # transform tag shared with the gateway detector
NOMINAL_VOLTAGE = 220.0
BASE_VOLTAGE = 220.0

# Usage bands (kW range by hour), copied from simulator/mqtt_publisher.py.
_BANDS = [
    (0, 6, 0.15, 0.8),
    (6, 12, 0.8, 2.3),
    (12, 17, 0.6, 1.8),
    (17, 23, 2.0, 5.8),
    (23, 24, 0.3, 1.0),
]


def _band(hour: int) -> tuple[float, float]:
    for lo, hi, mn, mx in _BANDS:
        if lo <= hour < hi:
            return mn, mx
    return 0.3, 1.0


def engineer(x: np.ndarray, nominal_voltage: float = NOMINAL_VOLTAGE) -> np.ndarray:
    """Append physics-informed features. ``x`` cols: [v, i, p, t]."""
    v, i, p, _t = x[:, 0], x[:, 1], x[:, 2], x[:, 3]
    voltage_dev = np.abs(v - nominal_voltage)
    power_discrepancy = p - (v * i)
    return np.column_stack([x, voltage_dev, power_discrepancy])


def generate_normal(n: int, rng: np.random.Generator) -> np.ndarray:
    """Generate ``n`` normal telemetry feature vectors [v, i, p, t]."""
    hours = rng.integers(0, 24, size=n)
    device_scale = rng.uniform(0.75, 1.25, size=n)
    power_w = np.empty(n)
    for k in range(n):
        mn, mx = _band(int(hours[k]))
        power_w[k] = rng.uniform(mn, mx) * device_scale[k] * 1000.0
    voltage = BASE_VOLTAGE + rng.uniform(-3.5, 3.5, size=n)
    pf = rng.uniform(0.92, 0.99, size=n)
    current = power_w / (voltage * pf)
    temperature = rng.uniform(25.0, 45.0, size=n)
    return np.column_stack([voltage, current, power_w, temperature])


def generate_anomalies(n: int, rng: np.random.Generator) -> tuple[np.ndarray, list[str]]:
    """Generate labeled anomalies the way the simulator does: override *only*
    the anomaly field on top of an otherwise-normal reading."""
    base = generate_normal(n, rng)
    kinds_pool = ["overload", "undervoltage", "overvoltage", "power_spike"]
    labels: list[str] = []
    for k in range(n):
        kind = str(rng.choice(kinds_pool))
        labels.append(kind)
        if kind == "overload":  # sim: current_a=12.5, power_w=2800
            base[k, 1] = rng.uniform(12.0, 15.0)
            base[k, 2] = 2800.0
        elif kind == "undervoltage":  # sim: voltage_v=180, power_w=1500
            base[k, 0] = rng.uniform(175.0, 190.0)
            base[k, 2] = 1500.0
        elif kind == "overvoltage":  # sim: voltage_v=260, power_w=1500
            base[k, 0] = rng.uniform(255.0, 265.0)
            base[k, 2] = 1500.0
        else:  # power_spike: sim overrides power_w only, current left as-is
            base[k, 2] = rng.uniform(4500.0, 6000.0)
    return base, labels


def score_raw(model: IsolationForest, scaler: StandardScaler, x: np.ndarray) -> np.ndarray:
    """Anomaly score for raw [v,i,p,t] rows. Higher == more anomalous."""
    return -model.score_samples(scaler.transform(engineer(x)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="models/anomaly_iforest.joblib")
    parser.add_argument("--report-dir", default="results/anomaly_model")
    parser.add_argument("--version", default="iforest_v1")
    parser.add_argument("--train-size", type=int, default=50_000)
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--max-samples", type=int, default=1024)
    parser.add_argument("--contamination", type=float, default=0.01)
    # Detection threshold = this quantile of normal-data anomaly scores.
    # Lower -> higher recall + higher false-positive rate (see tradeoff table).
    parser.add_argument("--threshold-quantile", type=float, default=0.90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    print(f"Generating {args.train_size} normal training samples...")
    x_train = generate_normal(args.train_size, rng)
    f_train = engineer(x_train)

    scaler = StandardScaler().fit(f_train)
    model = IsolationForest(
        n_estimators=args.n_estimators,
        max_samples=args.max_samples,
        contamination=args.contamination,
        random_state=args.seed,
    )
    model.fit(scaler.transform(f_train))

    train_scores = score_raw(model, scaler, x_train)
    threshold = float(np.quantile(train_scores, args.threshold_quantile))
    print(
        f"Derived anomaly threshold (q={args.threshold_quantile}): {threshold:.6f}"
    )

    bundle = {
        "model": model,
        "scaler": scaler,
        "features": FEATURES,
        "engineering": ENGINEERING,
        "nominal_voltage": NOMINAL_VOLTAGE,
        "threshold": threshold,
        "version": args.version,
        "metadata": {
            "trained_at": datetime.now(UTC).isoformat(),
            "train_size": args.train_size,
            "n_estimators": args.n_estimators,
            "max_samples": args.max_samples,
            "contamination": args.contamination,
            "threshold_quantile": args.threshold_quantile,
            "seed": args.seed,
        },
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump(bundle, out)
    print(f"Saved model artifact -> {out}")

    if not args.evaluate:
        return 0

    print("Building labeled test set for evaluation...")
    n_normal, n_anom = 10_000, 2_000
    x_norm = generate_normal(n_normal, rng)
    x_anom, anom_labels = generate_anomalies(n_anom, rng)
    labels_arr = np.array(anom_labels)

    s_norm = score_raw(model, scaler, x_norm)
    s_anom = score_raw(model, scaler, x_anom)

    # Operating-point tradeoff table across training-score quantiles.
    tradeoff = []
    for q in (0.90, 0.95, 0.975, 0.99):
        thr_q = float(np.quantile(train_scores, q))
        tradeoff.append(
            {
                "quantile": q,
                "threshold": round(thr_q, 4),
                "fpr": round(float((s_norm > thr_q).mean()), 4),
                "recall": round(float((s_anom > thr_q).mean()), 4),
            }
        )

    y_pred_norm = s_norm > threshold
    y_pred_anom = s_anom > threshold
    y_true = np.concatenate(
        [np.zeros(n_normal, dtype=int), np.ones(n_anom, dtype=int)]
    )
    y_pred = np.concatenate([y_pred_norm, y_pred_anom]).astype(int)

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    tp = int(y_pred_anom.sum())
    fn = int(n_anom - tp)
    fp = int(y_pred_norm.sum())
    tn = int(n_normal - fp)

    per_type = {
        kind: {
            "count": int((labels_arr == kind).sum()),
            "recall": round(float(y_pred_anom[labels_arr == kind].mean()), 4),
        }
        for kind in sorted(set(anom_labels))
    }

    report = {
        "model_version": args.version,
        "threshold": round(threshold, 6),
        "threshold_quantile": args.threshold_quantile,
        "test_normal": n_normal,
        "test_anomalies": n_anom,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "false_positive_rate": round(float(fp / max(tn + fp, 1)), 4),
        "recall_by_type": per_type,
        "operating_point_tradeoff": tradeoff,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "offline_evaluation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== Offline detection quality (Isolation Forest) ===")
    print(f"  operating point: q={args.threshold_quantile} threshold={threshold:.4f}")
    print(f"  precision : {precision:.4f}")
    print(f"  recall    : {recall:.4f}")
    print(f"  f1        : {f1:.4f}")
    print(f"  confusion : tn={tn} fp={fp} fn={fn} tp={tp}")
    print(f"  FPR       : {report['false_positive_rate']:.4f}")
    print("  recall by type:")
    for kind, stats in per_type.items():
        print(f"    {kind:14s} n={stats['count']:5d}  recall {stats['recall']:.4f}")
    print("  operating-point tradeoff (threshold quantile -> FPR / recall):")
    for row in tradeoff:
        print(
            f"    q={row['quantile']:<5} thr={row['threshold']:<7} "
            f"FPR={row['fpr']:.4f}  recall={row['recall']:.4f}"
        )
    print(f"Report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
