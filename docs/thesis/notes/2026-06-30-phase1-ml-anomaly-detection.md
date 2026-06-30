# Phase 1: Edge ML Anomaly Detection (Isolation Forest)

Date: 2026-06-30

## Decision

The thesis is being extended from the rule-based edge gateway into a hybrid
edge↔cloud ML system, built in independently-defensible phases. **Phase 1**
adds an unsupervised **Isolation Forest** anomaly detector that scores each
telemetry reading at the edge, alongside (or instead of) the rule engine.

Scope decisions (see also the paper analysis that motivated them):

- **Full hybrid edge↔cloud** is the target; Phase 1 ships the edge ML tier.
- **Simulator-only** (no STM32/ESP hardware this thesis; hardware is future work).
- **Isolation Forest** for the edge model (unsupervised, no labels, lightweight),
  following Mofidul et al. (Sensors 2022).

## What was implemented

- `gateway/app/services/anomaly_detector.py` — loads a joblib artifact, scores
  a reading, returns `(anomaly_score, is_anomaly, threshold, model_version)`.
  Degrades gracefully (disables itself) if ML is off, the artifact is missing,
  or sklearn/joblib are unavailable, so the default/baseline path is untouched.
- `gateway/app/db/repositories/predictions.py` — writes scores to the
  pre-existing `model_predictions` table (idempotent on its composite PK).
- `gateway/app/services/ingestion/telemetry.py` — scores each reading when
  `ENABLE_ML=true`, records `ml.scored` / `ml.anomalies` counters and an
  `ml_inference` latency series, and (when `ML_EMIT_EVENTS=true`) raises an
  `ML_ANOMALY` event through the same storage/alert path as a rule hit.
- `gateway/app/config.py` — `ml_model_path`, `ml_model_version`, `ml_features`,
  `ml_score_threshold`, `ml_emit_events`, `ml_event_type/severity`
  (`enable_ml` already existed).
- `scripts/train_anomaly_model.py` — offline training + evaluation. Generates
  data that mirrors `simulator/mqtt_publisher.py` (including the simulator's
  habit of overriding *only* the anomaly field), fits `StandardScaler` +
  `IsolationForest`, derives a threshold from a quantile of the normal-data
  scores, and reports precision/recall/F1, per-type recall, and an operating-
  point tradeoff table.
- `scripts/run_detection_ab_test.sh` — online A/B over the labeled anomaly
  scenarios in three modes: `rules`, `ml`, `hybrid`.
- `models/anomaly_iforest.joblib` — trained artifact (mounted read-only into
  the gateway container at `/app/models`).
- Tests: `gateway/tests/services/test_anomaly_detector.py` (disabled path,
  missing-artifact path, live scoring). Full suite: 48 passed.

## Feature engineering (physics_v1)

Raw `[voltage_v, current_a, power_w, temperature_c]` plus two physics-informed
features:

- `|voltage_v - 220|` — voltage excursion (under/overvoltage).
- `power_w - voltage_v*current_a` — P vs implied apparent power (consistency).

Reason: a global Isolation Forest over raw whole-house load dilutes single-axis
anomalies across its random splits, and IF does **not** isolate values far
*outside* the training range quickly (all splits push such a point down one
branch). The engineered features make voltage excursions and v/i/p
inconsistencies separable. The same transform is implemented in both the
training script (`engineer()`) and the gateway detector (`_apply_engineering`)
under the `physics_v1` tag.

## Offline result (reproducible)

`uv run python scripts/train_anomaly_model.py --evaluate`, seed 42, 50k train,
10k normal + 2k anomalies test, operating point q=0.90:

| Metric | Value |
| --- | ---: |
| Precision | 0.612 |
| Recall | 0.780 |
| F1 | 0.686 |
| FPR | 0.099 |

Per-type recall: overvoltage 0.99, power_spike 0.86, undervoltage 0.83,
overload 0.44.

Operating-point tradeoff (threshold = quantile of normal-data scores):

| q | threshold | FPR | recall |
| ---: | ---: | ---: | ---: |
| 0.90 | 0.545 | 0.099 | 0.780 |
| 0.95 | 0.573 | 0.052 | 0.387 |
| 0.975 | 0.602 | 0.025 | 0.242 |
| 0.99 | 0.634 | 0.019 | 0.188 |

## Honest interpretation

- **Voltage anomalies and power spikes** are detected well — they leave the
  normal operating envelope.
- **Overload** stays weak (recall 0.44). This is correct, not a bug: the
  simulator's normal evening load already drives current up to ~35 A, so the
  rule's `current > 10 A` is within the normal envelope and is a threshold
  artifact rather than a statistical anomaly. This is itself a useful finding
  for the rules-vs-ML discussion.
- Result is **offline** on synthetic-but-simulator-faithful data. It is a
  detection-quality measurement, not a field result. The **online A/B**
  (`run_detection_ab_test.sh`) measures the *operational* cost (latency,
  counts, DB growth) in the live gateway and is pending a run.

## Reproduce

```bash
uv run python scripts/train_anomaly_model.py --evaluate   # artifact + offline metrics
ENABLE_ML=true ML_EMIT_EVENTS=true bash scripts/run_detection_ab_test.sh  # online A/B
```

## Next phases

2. Threshold-gated edge→cloud escalation + bandwidth measurement.
3. Cloud-tier LSTM failure prediction / forecasting.
4. Storage optimization (selective retention / downsampling).
