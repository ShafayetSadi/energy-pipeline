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
  detection-quality measurement, not a field result.

## Online A/B result (operational cost, 2026-06-30)

`run_detection_ab_test.sh`, three modes over the labeled scenarios (~1,375–1,379
telemetry msgs each):

| Mode | Telemetry avg / p99 | ML inference avg / p99 | Rule events | ML_ANOMALY | predictions | DB growth |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| rules | 6.72 / 9.71 ms | – | 642 | 0 | 0 | 1.97 MB |
| ml | 19.30 / 24.98 ms | 11.85 / 16.28 ms | 0 | 9 | 1376 | 2.03 MB |
| hybrid | 19.63 / 24.83 ms | 11.90 / 16.50 ms | 660 | 7 | 1375 | 2.53 MB |

**Headline finding:** per-sample scikit-learn `score_samples` adds ~12 ms avg /
~15 ms p99 to telemetry latency (vs sub-ms for rules), because it is called one
sample at a time, synchronously, in the async ingestion path. sklearn is
batch-optimized; this is an optimization target (batch / thread-offload /
lighter model), not a fundamental limit. p99 still < 25 ms at the tested rate.
ml-only flagged 104 readings but emitted only 9 events (per-device cooldown
collapses anomaly-window bursts). Hybrid = union of rule + ML events. Storage:
hybrid grows most (a prediction row per reading + events). Written into thesis
Section 6.7.1; cross-mode counts are indicative (scenario randomness), not
exact like-for-like.

## Reproduce

```bash
uv run python scripts/train_anomaly_model.py --evaluate   # artifact + offline metrics
ENABLE_ML=true ML_EMIT_EVENTS=true bash scripts/run_detection_ab_test.sh  # online A/B
```

## Inference optimization (2026-06-30, post-A/B)

The inline A/B exposed ~12 ms per-reading ML latency. Profiling: single-sample
`score_samples` ~10 ms vs ~0.014 ms/row batched (sklearn per-call overhead;
linear in n_estimators ~0.05 ms/tree, so fewer trees alone is insufficient).

Fix: moved scoring into an async micro-batch worker
(`gateway/app/workers/ml_scoring.py`). Telemetry handler enqueues each reading
and returns; worker drains the queue in batches (`ML_BATCH_MAX_SIZE`=128,
`ML_BATCH_WINDOW_MS`=50), scores in one call via `AnomalyDetector.score_many`,
then writes predictions + ML events (same cooldown/alert path). `ML_ASYNC_SCORING`
(default true) toggles inline vs batched for the comparison. Also doubles as the
queue substrate for Phase 2's escalation gate. 50 tests pass, lint clean.

**After-measurement (2026-07-03).** A first re-run was invalid: the compose
image predated the async-worker commit (app code is baked into the image; only
`config/` and `models/` are bind-mounted), so it silently re-ran inline
scoring. `run_detection_ab_test.sh` now does `docker compose build
edge-gateway` up front. The rebuilt run confirms the fix:

| Mode (async) | Telemetry avg / p99 | ML inference avg / p99 | ml_queue avg / p99 |
| --- | --- | --- | --- |
| rules | 6.72 / 9.61 ms | – | – |
| ml | 6.35 / 10.35 ms | 10.42 / 15.63 ms | 48.75 / 54.97 ms |
| hybrid | 6.65 / 9.96 ms | 10.41 / 13.82 ms | 49.02 / 54.87 ms |

Telemetry is back at the rules baseline; the scoring cost moved off the hot
path into a ~49 ms enqueue-to-score delay dominated by the 50 ms batch window.
Caveat: at ~2.3 msg/s the average batch was only ~1.1 readings (1,256–1,268
batches for ~1,376 scored), so this run demonstrates the decoupling, not the
batch amortisation — that needs a higher-rate test. Written into Section 6.7.1
as the before/after pair; `results/detection_ab/` now holds this run.

## Next phases

2. Threshold-gated edge→cloud escalation + bandwidth measurement.
3. Cloud-tier LSTM failure prediction / forecasting.
4. Storage optimization (selective retention / downsampling).
