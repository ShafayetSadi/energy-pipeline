# Chapter 3: Proposed System Architecture

## 3.1 System Overview

The proposed system is an edge-first, event-driven architecture for IoT-based
smart energy monitoring. Energy monitoring nodes publish measurements through
MQTT. A local broker receives those messages and forwards them to a FastAPI
edge gateway. The gateway validates the payloads, applies rule-based event
detection, classifies abnormal conditions, stores readings and events in
PostgreSQL/TimescaleDB, and exposes the data through REST APIs and Grafana
dashboards.

The main architectural contribution is the edge gateway layer. Instead of
treating the backend as only a database writer, the gateway acts as a local
intelligence layer between energy devices and long-term storage. This allows
the system to reject malformed data, detect abnormal conditions early, and
record event evidence before the information is viewed on a dashboard.

The high-level flow is:

```text
Energy node or simulator
        |
        | MQTT telemetry/status/events
        v
Mosquitto MQTT broker
        |
        | energy/+/telemetry
        | energy/+/status
        | energy/+/events
        v
FastAPI edge gateway
        |
        | validation
        | rule evaluation
        | ML anomaly scoring (Isolation Forest, Phase 1)
        | event classification
        | metrics collection
        v
PostgreSQL/TimescaleDB
        |
        |  score-gated escalation of flagged readings (Phase 2)
        v ----------------------------------> Cloud tier (receiver + LSTM-AE
        |                                      verifier, Phase 3)
        v
Grafana dashboards and REST API clients
```

The architecture follows five principles:

1. Process telemetry at the edge before treating it as stored history.
2. Separate normal readings from abnormal events.
3. Store time-series data in a database designed for time-window queries.
4. Make validation, latency, throughput, and event counts observable.
5. Add edge intelligence incrementally — rule-based detection first, then a
   lightweight ML detector at the edge (Phase 1), then score-gated escalation
   to a cloud tier (Phase 2), then a cloud-side LSTM-autoencoder verifier on
   the escalated stream (Phase 3).

## 3.2 Energy Monitoring Node Layer

The energy monitoring node is responsible for measuring electrical parameters
and publishing structured telemetry. The implemented firmware targets a
Nucleo-F429ZI and uses the microcontroller's Ethernet MAC with LwIP/MQTT. The
intended physical setup connects it to the isolated voltage/current sensing
front end documented under `firmware/hardware/`.

The node is expected to measure:

- voltage in volts
- current in amperes
- instantaneous power in watts
- optional temperature
- device status and signal metadata

The basic local calculation is:

```text
power_w = voltage_v * current_a
```

Each node uses a stable device identifier such as `house_0001` or
`lab_node_001`. The device identifier appears both in the MQTT topic and in
the message body, allowing the gateway to associate readings, status messages,
and events with the correct source.

For the controlled benchmark evaluation, synthetic devices are produced by the
MQTT simulator. Separately, the compiled STM32F429ZI firmware has published the
same contract through Renode into the unmodified pipeline. Renode uses
synthetic ADC waveforms, while the analog front end is validated independently
in SPICE; a physically integrated and calibrated node remains future work.

## 3.3 MQTT Broker Layer

The MQTT broker decouples publishers from consumers. Energy nodes publish
messages to topic names, and the edge gateway subscribes to topic patterns.
This allows devices and backend services to evolve independently.

The broker used in the implementation is Eclipse Mosquitto. The topic design
separates telemetry, status, and events:

```text
energy/{device_id}/telemetry
energy/{device_id}/status
energy/{device_id}/events
energy/{device_id}/commands
energy/{device_id}/config
```

The gateway subscribes to:

```text
energy/+/telemetry
energy/+/status
energy/+/events
```

This topic structure is simple enough for a prototype but still expressive
enough to distinguish measurement data, device health, and device-originated
events. It also allows the gateway to route messages to different validation
and ingestion paths based on topic type.

## 3.4 FastAPI Edge Gateway

The FastAPI edge gateway is the main contribution of the thesis. It combines
an MQTT consumer, validation pipeline, rule engine, persistence layer,
metrics collector, alert workflow, and REST API.

The gateway responsibilities are:

| Responsibility | Description |
| --- | --- |
| MQTT consumption | Subscribe to energy topics and receive telemetry, status, and event messages |
| Topic parsing | Extract device ID and message type from `energy/{device_id}/{type}` |
| Payload validation | Validate telemetry/status/event schemas before storage |
| Data-quality logging | Record invalid payloads and validation failure reasons |
| Rule evaluation | Apply threshold and percentage-increase rules to valid telemetry |
| ML anomaly scoring | Score each reading with an Isolation Forest detector (Phase 1) and persist scores to `model_predictions` |
| Event classification | Convert rule hits and ML anomalies into typed events with severity |
| Persistence | Store devices, readings, events, status history, metrics, and quality logs |
| Metrics | Track counters and latency summaries for evaluation |
| REST API | Expose health, readings, devices, events, rules, and metrics endpoints |
| Alert workflow | Queue critical-event notifications through an alert outbox |

The gateway is implemented as a modular service. MQTT handlers, ingestion
services, repositories, schemas, rule evaluation, metrics, and background
workers are separated into different modules. This separation makes the
gateway easier to test and easier to extend.

## 3.5 Data Validation Pipeline

The validation pipeline protects the database and dashboards from malformed
or incomplete input. Each incoming MQTT message is routed by topic type and
validated against the expected schema.

Telemetry payloads include:

| Field | Meaning |
| --- | --- |
| `device_id` | Stable device identifier |
| `timestamp` | Device-side timestamp |
| `voltage_v` | RMS voltage in volts |
| `current_a` | RMS current in amperes |
| `power_w` | Instantaneous real power in watts |
| `temperature_c` | Optional temperature |
| `sequence_no` | Optional monotonic sequence number |
| `firmware_version` | Optional firmware version |
| `rssi_dbm` | Optional Wi-Fi signal strength |

Status payloads include online/offline/maintenance/error status and optional
metadata such as firmware version, IP address, RSSI, and reason.

When validation succeeds, telemetry can be stored and evaluated by the rule
engine. When validation fails, the gateway does not silently discard the
problem. It increments validation counters and writes a row to
`data_quality_logs`. This makes data quality part of the observable system.

## 3.6 Rule Engine and Event Classifier

The rule engine converts raw readings into meaningful events. Rules are
configured in YAML and loaded by the gateway. The current rules include
threshold-based checks and percentage-increase checks.

Implemented rule examples:

| Rule | Condition | Event type | Severity |
| --- | --- | --- | --- |
| `undervoltage` | `voltage_v < 200` | `UNDER_VOLTAGE` | `WARNING` |
| `overvoltage` | `voltage_v > 250` | `OVER_VOLTAGE` | `WARNING` |
| `overload` | `current_a > 10` | `OVERLOAD` | `CRITICAL` |
| `power_spike` | `power_w` increases by 30% in 60s | `POWER_SPIKE` | `WARNING` |
| `voltage_anomaly_low` | `voltage_v < 210` | `VOLTAGE_ANOMALY` | `INFO` |
| `over_temperature` | `temperature_c > 60` | `OVER_TEMPERATURE` | `WARNING` |

When a rule triggers, the gateway creates an event containing:

- event type
- severity
- rule name
- message
- event value
- threshold value
- related device
- related reading time
- metadata

This event model allows the dashboard and API to explain not only that an
event occurred, but also why it occurred.

## 3.7 PostgreSQL/TimescaleDB Storage Layer

The storage layer uses PostgreSQL with TimescaleDB features for time-series
data. TimescaleDB is appropriate because most queries are time-window queries:
latest readings, readings in a period, per-device trends, event timelines,
and system metrics over time.

The main tables are:

| Table | Purpose |
| --- | --- |
| `devices` | Current device metadata and status |
| `energy_readings` | Time-series telemetry readings |
| `events` | Rule-generated and device-originated events |
| `data_quality_logs` | Validation errors and malformed payload evidence |
| `device_status_history` | Device status timeline |
| `system_metrics` | Gateway counters and latency summaries |
| `rule_definitions` | Future database-backed rule management |
| `alert_outbox` | Pending or processed alert notifications |
| `alert_deliveries` | Alert delivery history |
| `model_predictions` | Edge ML anomaly scores and labels (Phase 1); extensible to forecasts |

The important indexes support device/time lookup and event filtering. The
time-series tables can be converted into TimescaleDB hypertables, allowing
efficient time-window queries and future retention policies. The architecture
also supports aggregated views such as one-minute reading summaries.

Storage reduction is not claimed as a measured result in this thesis version.
The current implementation stores raw readings and event evidence so the
evaluation can compare behavior clearly. Future work may add selective raw
retention, downsampling, or event-only long-term storage.

## 3.8 Grafana Dashboard and Alerting

Grafana provides the visual observability layer. The dashboards are
provisioned from JSON files and connected to TimescaleDB through a configured
PostgreSQL datasource.

The implemented dashboard set is:

| Dashboard | Purpose |
| --- | --- |
| Energy Overview | System-level view of devices, readings, load, voltage, and events |
| Device Detail | Per-device measurements, thresholds, event markers, and status history |
| Event Timeline | Recent events, severity counts, event types, and affected devices |
| System Observability | Message rate, validation rate, latency percentiles, and alert queue state |
| Thesis Evaluation | A/B result summary, anomaly evidence, database-size observation, and interpretation boundaries |

The alert workflow is represented through an alert outbox. Critical events can
be queued for delivery through configured channels such as webhook, email, or
Slack-style integrations. The outbox pattern separates event creation from
notification delivery so that detection is not blocked by a temporary
external notification failure.

## 3.9 Edge ML Anomaly Detection (Phase 1)

The architecture is extended with an unsupervised machine-learning detector
that runs at the edge alongside the rule engine. The detector is an **Isolation
Forest** trained offline on normal operating data and loaded by the gateway as
a model artifact (following Mofidul et al. [15]; see Chapter 2.7).

The detector scores a physics-informed feature vector derived from each
reading:

```text
[ voltage_v, current_a, power_w, temperature_c,
  |voltage_v - V_nominal|,          # voltage excursion
  power_w - voltage_v*current_a ]   # P vs implied apparent power
```

It returns an anomaly score (higher = more anomalous) and flags the reading
when the score exceeds a threshold derived from the training distribution. The
score and label are written to `model_predictions` for every reading; when
event emission is enabled, a flagged reading also raises an `ML_ANOMALY` event
through the same storage and alert path as a rule hit.

To keep machine-learning inference off the ingestion hot path, scoring runs in
an asynchronous micro-batch worker: the telemetry handler enqueues each reading
and returns immediately, and the worker scores readings in batches. This is
both a latency optimization (scikit-learn is far cheaper per reading when
scoring a batch than one sample at a time) and a structural stepping stone
toward the score-gated cloud escalation of a later phase, which consumes the
same queue.

The detector is independent of the rule engine, which lets the evaluation run
three configurations — **rules-only**, **ml-only**, and **hybrid** — and
compare detection quality and processing overhead directly. It also degrades
gracefully: if ML is disabled or the artifact is unavailable, the gateway
behaves exactly as the rule-based system, so the baseline path carries no ML
dependency.

This realises the edge-AI direction that Verde Romero et al. [14] named as
future work.

**Score-gated escalation (Phase 2).** The scoring worker's queue doubles as
the substrate for the hybrid design's escalation path (following the
edge-gates-cloud pattern of Sathupadi et al. [16]): scored readings are
offered to a cloud forwarder that, depending on `CLOUD_FORWARD_MODE`, forwards
nothing (`off`, the default), only readings whose anomaly score crosses the
escalation threshold (`gated`), or every scored reading (`all` — the naive
all-to-cloud baseline used for the bandwidth comparison). Forwarded readings
are batched into compact JSON envelopes carrying the measurements plus score,
threshold, and model version, and POSTed to a minimal cloud-tier receiver that
counts what it receives. Forward failures are counted and dropped rather than
retried, so edge detection never depends on cloud reachability. The cloud-side
verification stage is implemented in Phase 3 (Section 6.7.3): an LSTM
autoencoder confirms or suppresses escalated readings by reconstruction error.
Edge-side storage optimization (Huang et al. [17]) remains staged as a later
phase and is not claimed as a result here.

## 3.10 Chapter Summary

The proposed architecture combines MQTT communication, an event-driven edge
gateway, TimescaleDB storage, rule-based event detection, alert workflow, and
Grafana dashboards. The key design decision is to move validation and event
detection into the gateway layer before data becomes only historical storage.
This enables the evaluation in later chapters: the baseline path measures raw
ingestion behavior, while the proposed path measures the cost and value of
adding edge intelligence.
