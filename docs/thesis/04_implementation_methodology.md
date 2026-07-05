# Chapter 4: Implementation Methodology

## 4.1 Implementation Overview

This chapter describes how the proposed architecture was implemented. The
implementation uses Docker Compose to run Mosquitto, TimescaleDB, the FastAPI
edge gateway, Grafana, and the MQTT simulator. The gateway code is organized
around schemas, MQTT handlers, ingestion services, repositories, rule
evaluation, metrics collection, and background workers.

The current implementation and evaluation focus on the software pipeline. The
architecture supports STM32/ESP-based hardware nodes, but the repeatable
evaluation in Chapter 5 uses a synthetic MQTT simulator to generate controlled
high-throughput and anomaly scenarios.

## 4.2 Hardware and Device Setup

The intended hardware node contains:

- STM32 microcontroller
- voltage sensing circuit
- current sensing circuit
- ESP8266 or ESP32 network module
- power supply
- optional temperature sensor

The device layer is responsible for sampling electrical measurements,
calculating power, creating a timestamped payload, and publishing it through
MQTT. A practical hardware implementation can publish to the same topic
structure used by the simulator.

For controlled thesis evaluation, the simulator replaces physical devices. It
generates multiple virtual devices, publishes telemetry and status messages,
and can inject abnormal values or malformed payloads. This gives repeatable
test data for throughput, latency, validation, and rule-detection experiments.

## 4.3 Firmware and Publisher Workflow

The firmware or simulator publisher follows the same logical workflow:

1. Read voltage and current measurements.
2. Calculate instantaneous power.
3. Optionally read temperature and signal strength.
4. Build a JSON payload with device ID and timestamp.
5. Publish telemetry to `energy/{device_id}/telemetry`.
6. Publish status or heartbeat messages to `energy/{device_id}/status`.
7. Optionally publish device-originated events to `energy/{device_id}/events`.

The gateway expects telemetry fields such as:

```json
{
  "device_id": "house_0001",
  "timestamp": "2026-06-28T10:00:00+00:00",
  "voltage_v": 220.5,
  "current_a": 4.2,
  "power_w": 926.1,
  "temperature_c": 32.4,
  "sequence_no": 1024,
  "firmware_version": "0.1.0",
  "rssi_dbm": -55.0
}
```

The exact physical sampling method is outside the measured scope of this
software-focused evaluation. The important implementation contract is that
hardware or simulated publishers produce the same MQTT topic and payload
format.

## 4.4 MQTT Topic and Payload Design

The MQTT topic convention is:

```text
energy/{device_id}/{message_type}
```

The implemented message types are:

| Topic | Purpose |
| --- | --- |
| `energy/{device_id}/telemetry` | Voltage, current, power, temperature, and sequence data |
| `energy/{device_id}/status` | Device health, firmware, IP address, RSSI, and reason |
| `energy/{device_id}/events` | Optional events published by the device |

The gateway subscribes to wildcard topics:

```text
energy/+/telemetry
energy/+/status
energy/+/events
```

Topic parsing is implemented in the MQTT topic helper. Invalid topic shapes
are ignored or rejected before they reach the ingestion path. This prevents
unstructured MQTT messages from being stored as valid energy telemetry.

## 4.5 Backend API and MQTT Consumer

The backend is implemented with FastAPI. It starts the MQTT consumer and
background workers during application lifespan startup. The MQTT consumer
receives broker messages and passes them to the appropriate handler based on
topic type.

The REST API exposes:

| API group | Examples | Purpose |
| --- | --- | --- |
| Health | `/health`, `/ready`, `/version` | Service and dependency status |
| Devices | `/api/v1/devices`, `/api/v1/devices/{device_id}/status` | Device metadata and status history |
| Readings | `/api/v1/readings`, `/api/v1/readings/{device_id}/latest` | Telemetry query and latest reading access |
| Events | `/api/v1/events`, `/api/v1/events/{event_id}/acknowledge` | Event timeline and acknowledgement |
| Rules | `/api/v1/rules`, `/api/v1/rules/reload` | Rule inspection and reload |
| Metrics | `/api/v1/metrics/summary`, `/api/v1/metrics/throughput` | Gateway counters, latency, quality, and event summaries |

The API supports both dashboard usage and result export. The evaluation
scripts use the metrics and report export paths to generate the evidence used
in Chapter 6.

## 4.6 Validation and Ingestion Implementation

Incoming payloads are validated with Pydantic schemas before persistence.
Telemetry, status, and device-originated event messages have separate schema
types. The telemetry schema requires non-negative voltage, current, and power
values and accepts optional temperature, sequence number, firmware version,
and RSSI.

The ingestion path performs these steps:

1. Parse the MQTT topic.
2. Decode the JSON payload.
3. Validate the payload against the expected schema.
4. Upsert or update device metadata.
5. Store valid readings or status history.
6. Evaluate telemetry against rules when proposed processing is enabled.
7. Store generated events.
8. Record counters and latency metrics.

If payload parsing or validation fails, the gateway increments validation
failure counters and writes a `data_quality_logs` record containing the topic,
error type, error message, and raw payload. This behavior is important because
invalid data becomes measurable evidence instead of disappearing silently.

## 4.7 Database Schema and Persistence

The database schema is managed through Alembic migrations under
`database/migrations`. The schema contains operational tables, time-series
tables, and future extension tables.

The main tables are:

| Table | Implementation purpose |
| --- | --- |
| `devices` | Current device state and metadata |
| `energy_readings` | Valid telemetry readings |
| `events` | Rule-generated and device-originated events |
| `data_quality_logs` | Invalid payload and validation failure evidence |
| `device_status_history` | Device online/offline/status history |
| `system_metrics` | Persisted counters and latency summaries |
| `rule_definitions` | Future path for database/API-driven rule management |
| `alert_outbox` | Pending alert notifications |
| `alert_deliveries` | Delivery result history |
| `model_predictions` | Edge ML anomaly scores and labels (Phase 1); extensible to forecasts |

The `energy_readings` table uses `(time, device_id)` as its primary key and
has an index on `(device_id, time)` for device time-series queries. The
`events` table stores severity, rule name, event value, threshold value, and
acknowledgement state. The `system_metrics` table stores gateway counters and
latency summaries that are later visualized in Grafana.

TimescaleDB is used because the dominant queries are time-range queries:
recent readings, per-device trends, event timelines, and metric history.
Hypertables and continuous aggregates provide a future path for efficient
longer-term time-series analysis.

## 4.8 Rule Engine Implementation

Rules are configured in `gateway/config/rules.yaml` and loaded by the rule
engine at gateway startup. The implemented rule engine supports:

- threshold rules
- percentage-increase rules
- reload through the rules API
- rolling window state for spike detection
- event severity and event type mapping

Example rules include:

| Rule | Type | Condition | Event |
| --- | --- | --- | --- |
| `undervoltage` | Threshold | `voltage_v < 200` | `UNDER_VOLTAGE`, warning |
| `overvoltage` | Threshold | `voltage_v > 250` | `OVER_VOLTAGE`, warning |
| `overload` | Threshold | `current_a > 10` | `OVERLOAD`, critical |
| `power_spike` | Percentage increase | `power_w` rises 30% within 60s | `POWER_SPIKE`, warning |
| `voltage_anomaly_low` | Threshold | `voltage_v < 210` | `VOLTAGE_ANOMALY`, info |
| `over_temperature` | Threshold | `temperature_c > 60` | `OVER_TEMPERATURE`, warning |

When a rule triggers, the engine returns a rule hit. The ingestion service
turns that hit into a stored event with a device ID, event type, severity,
rule name, message, event value, threshold value, and metadata. This provides
traceability between raw telemetry and the generated event.

## 4.9 Edge ML Anomaly Detector Implementation

The edge ML detector is implemented in
`gateway/app/services/anomaly_detector.py` and trained by
`scripts/train_anomaly_model.py`. It uses an Isolation Forest from
scikit-learn, persisted as a joblib artifact and mounted read-only into the
gateway container at `/app/models`.

**Feature engineering (`physics_v1`).** Each reading is mapped to a six-element
vector: the four raw fields `[voltage_v, current_a, power_w, temperature_c]`
plus two physics-informed features — the voltage excursion
`|voltage_v - 220|` and the power consistency residual
`power_w - voltage_v*current_a`. The same transform is implemented in both the
training script (`engineer()`) and the gateway (`_apply_engineering`) under the
`physics_v1` tag. These features are needed because a global Isolation Forest
over raw whole-house load dilutes single-axis anomalies across its random
splits and does not isolate out-of-range values quickly; the engineered
features make voltage excursions and voltage/current/power inconsistencies
separable.

**Training and threshold.** The training script generates data that mirrors the
simulator's telemetry distribution, including the simulator's behaviour of
overriding only the anomaly field on top of an otherwise-normal reading. It
fits a `StandardScaler` and an `IsolationForest` (n_estimators = 200,
max_samples = 1024, contamination = 0.01), then defines the anomaly score as
`-model.score_samples(x)` so that higher means more anomalous. The detection
threshold is the q-th quantile of the normal-data scores (default q = 0.90),
which exposes an explicit recall/false-positive operating point.

**Scoring in the pipeline.** When `ENABLE_ML=true`, each valid reading is
scored, the score and label are written to `model_predictions`, the
`ml.scored` / `ml.anomalies` counters are updated, and (when
`ML_EMIT_EVENTS=true`) a flagged reading raises an `ML_ANOMALY` event through
the same storage and alert path as a rule hit, with a per-device cooldown to
bound event volume. The detector is independent of the rule engine, enabling
rules-only, ml-only, and hybrid configurations. If ML is disabled or the
artifact is missing, the detector disables itself and the gateway runs exactly
as the rule-based system, so the baseline path carries no ML dependency.

**Async micro-batch scoring.** The first online A/B (Section 6.7.1) showed that
calling scikit-learn's `score_samples` once per message, synchronously inside
the ingestion path, added roughly 12 ms of latency per reading — scikit-learn
is optimised for batched inference, so per-call overhead dominates single-sample
scoring (profiling measured ~10 ms per single sample versus ~0.014 ms per row
when batched). To remove this from the hot path, scoring was moved into an
asynchronous micro-batch worker (`gateway/app/workers/ml_scoring.py`). The
telemetry handler enqueues a lightweight job per reading and returns
immediately; the worker drains the queue in batches (bounded by
`ML_BATCH_MAX_SIZE` or `ML_BATCH_WINDOW_MS`), scores each batch in a single
model call, and persists predictions and ML events. This keeps telemetry
latency at rule-engine levels while amortising inference cost across the batch.
The `ML_ASYNC_SCORING` flag (default true) switches between this worker and the
original inline path, which allows the inline-versus-batched comparison in
Section 6.7.1.

## 4.10 Edge-to-Cloud Escalation Gate (Phase 2)

The hybrid architecture's second phase adds a score-gated escalation path from
the edge gateway to a cloud tier, implemented in
`gateway/app/workers/cloud_forwarder.py` and a minimal receiver service in
`cloud/app/main.py`.

**Escalation gate.** After the ML scoring worker scores a batch, each scored
reading is offered to the cloud forwarder, which applies the gate configured
by `CLOUD_FORWARD_MODE`:

- `off` (default) — nothing leaves the edge; the gateway behaves exactly as in
  Phase 1.
- `gated` — only readings whose anomaly score crosses the escalation threshold
  are forwarded. By default the gate reuses the model's own anomaly threshold
  (escalating exactly the flagged set); `CLOUD_ESCALATION_THRESHOLD` can set a
  stricter score cut-off independently of event emission.
- `all` — every scored reading is forwarded. This is the naive
  all-data-to-cloud baseline: both modes run the identical pipeline, so a
  gated-versus-all comparison isolates the gate as the only variable.

**Forwarding worker.** Escalated readings are queued and sent in batches
(bounded by `CLOUD_FORWARD_BATCH_MAX_SIZE` or `CLOUD_FORWARD_BATCH_WINDOW_MS`)
as a compact JSON envelope over HTTP POST. Each forwarded reading carries the
measurement fields plus its anomaly score, threshold, model version, and
whether a rule also fired — enough context for a cloud-side model to act
without a follow-up query. The gateway counts forwarded readings, batches, and
payload bytes (`cloud.forwarded`, `cloud.batches`, `cloud.bytes_sent`) and
records a `cloud_forward` latency series. Failures are counted
(`cloud.forward_failed`) and the batch is dropped rather than retried: edge
detection never depends on cloud reachability, preserving the edge-first
principle.

**Cloud tier.** The receiver (`cloud-tier` in Docker Compose) is deliberately
minimal for the Phase 2 bandwidth measurement: it validates the envelope,
counts batches, readings, and received bytes, and keeps a bounded in-memory
buffer of recent escalations for inspection. Its role there is to terminate the
escalation path so bandwidth can be measured end to end
(`scripts/run_escalation_bandwidth_test.sh`, Section 5.6). Phase 3 extends the
same service with an LSTM-autoencoder verifier (`cloud/app/verifier.py`) that
scores escalated readings by reconstruction error using a numpy-only kernel, so
the container still needs no deep-learning runtime (Section 6.7.3).

## 4.11 Metrics and Alert Workflow

The metrics service keeps in-memory counters and latency samples, then
periodically flushes them to `system_metrics`. The exported metrics include
message counters, validation failures, readings stored, event counts, and
latency percentiles.

Latency summaries are reported as:

- average
- p50
- p95
- p99

These metrics are used by the evaluation scripts and Grafana dashboards. They
allow the thesis to compare baseline and proposed modes using measured
gateway behavior rather than only simulator output.

The alert workflow uses an outbox pattern. When critical events are created,
alert records can be queued in `alert_outbox`. A background worker can process
pending alerts and record delivery results. This separates detection from
delivery and prevents a notification failure from blocking event persistence.

## 4.12 Dashboard Implementation

Grafana is provisioned from files under `config/grafana`. The datasource is
configured to connect to TimescaleDB, and dashboard JSON files are loaded into
the `Energy Monitoring` folder.

The implemented dashboards are:

| Dashboard | Implementation role |
| --- | --- |
| `energy_overview.json` | System-level readings, load, voltage, and event summary |
| `device_detail.json` | Per-device status, readings, thresholds, events, and status history |
| `event_timeline.json` | Event table, event buckets, severity summary, affected devices |
| `system_observability.json` | Message rate, stored-reading rate, validation rate, latency, alert outbox |
| `thesis_evaluation.json` | A/B summary, latency overhead, anomaly evidence, and interpretation boundaries |

The dashboards are designed to support both operation and thesis evidence.
They do not replace the exported result files, but they visually confirm that
readings, events, data-quality behavior, and system metrics are observable.

## 4.13 Docker-Based Deployment

Docker Compose is used to run the local system. The main services are:

| Service | Container role | Exposed port |
| --- | --- | --- |
| `mosquitto` | MQTT broker | `18831 -> 1883` |
| `timescaledb` | PostgreSQL/TimescaleDB database | `54329 -> 5432` |
| `edge-gateway` | FastAPI gateway and MQTT consumer | `8001 -> 8000` |
| `grafana` | Dashboard UI | `3001 -> 3000` |
| `simulator` | MQTT workload generator | profile-based load-test service |

The gateway is configured through environment variables such as
`PROCESSING_MODE`, `STORE_RAW_READINGS`, `ENABLE_RULE_ENGINE`,
`ENABLE_AGGREGATION`, `ENABLE_ALERTS`, `ENABLE_ML`, and `ML_EMIT_EVENTS`. This
makes it possible to switch between baseline and proposed modes and between
rules-only, ml-only, and hybrid detection for evaluation. The trained model
artifact is mounted read-only at `/app/models/anomaly_iforest.joblib`.

## 4.14 Testing Strategy

The testing strategy combines automated tests and scripted system experiments.

Automated tests cover:

- MQTT topic parsing
- payload validation
- rule engine behavior
- ML anomaly detector behavior (disabled path, missing-artifact path, live scoring)
- repository operations
- metrics service behavior
- alert service and outbox worker behavior
- API smoke checks
- script syntax checks
- application lifecycle behavior

Scripted experiments cover:

- baseline high-throughput ingestion
- proposed high-throughput processing
- repeated clean A/B comparisons
- proposed-mode anomaly scenarios
- invalid payload handling
- report and snapshot export

The key scripts are:

| Script | Purpose |
| --- | --- |
| `scripts/run_baseline_test.sh` | Single baseline experiment |
| `scripts/run_proposed_test.sh` | Single proposed experiment |
| `scripts/run_high_throughput_ab_test.sh` | Clean repeated baseline/proposed comparison |
| `scripts/run_anomaly_detection_test.sh` | Proposed-mode anomaly and validation evidence |
| `scripts/train_anomaly_model.py` | Train + offline-evaluate the Isolation Forest detector |
| `scripts/run_detection_ab_test.sh` | Rules-only vs ml-only vs hybrid detection A/B |
| `scripts/export_results.py` | Export metrics snapshots and Markdown reports |

This strategy keeps the thesis evaluation reproducible. The automated tests
verify the implementation pieces, while the experiment scripts generate the
evidence used in Chapter 6.

## 4.15 Chapter Summary

The implementation follows the proposed architecture closely. MQTT messages
enter through Mosquitto, the FastAPI gateway validates and processes them,
applies rule-based detection and an edge Isolation Forest anomaly detector,
TimescaleDB stores readings, events, and model predictions, Grafana visualizes
the system state, and scripts export reproducible evaluation evidence. The
implementation now includes a trained, offline-evaluated edge ML detector
(Phase 1), with explicit extension points for the cloud tier, score-gated
escalation, and storage optimization in later phases.
