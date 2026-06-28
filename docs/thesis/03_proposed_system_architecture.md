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
        | event classification
        | metrics collection
        v
PostgreSQL/TimescaleDB
        |
        v
Grafana dashboards and REST API clients
```

The architecture follows five principles:

1. Process telemetry at the edge before treating it as stored history.
2. Separate normal readings from abnormal events.
3. Store time-series data in a database designed for time-window queries.
4. Make validation, latency, throughput, and event counts observable.
5. Keep future AI/ML anomaly detection as an extension point, not as a current claim.

## 3.2 Energy Monitoring Node Layer

The energy monitoring node is responsible for measuring electrical parameters
and publishing structured telemetry. In the intended physical setup, this
layer can be implemented using an STM32 microcontroller with voltage and
current sensing hardware and an ESP8266 or ESP32 module for Wi-Fi/MQTT
communication.

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

For the current thesis evaluation, synthetic devices are produced by the MQTT
simulator. This allows repeatable high-throughput and anomaly tests without
depending on field hardware timing. Real STM32/ESP hardware can be connected
to the same MQTT topic structure in future hardware validation.

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
| Event classification | Convert rule hits into typed events with severity |
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
| `model_predictions` | Future AI/ML prediction extension point |

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

## 3.9 AI/ML-Ready Extension Points

The current thesis uses rule-based detection, not machine-learning anomaly
detection. However, the architecture contains extension points for future
AI/ML work.

Future model-based modules could use:

- historical `energy_readings` as model input
- `events` as weak labels or evaluation labels
- `data_quality_logs` to filter malformed inputs
- `device_status_history` to distinguish device faults from electrical anomalies
- `model_predictions` to store future anomaly scores or forecast results

A future ML module could run after ingestion or as a background worker. It
could read recent time windows, calculate anomaly scores, and write prediction
records without changing the MQTT topic contract or dashboard architecture.
This keeps the current thesis honest: AI/ML is a planned extension point, not
a measured result.

## 3.10 Chapter Summary

The proposed architecture combines MQTT communication, an event-driven edge
gateway, TimescaleDB storage, rule-based event detection, alert workflow, and
Grafana dashboards. The key design decision is to move validation and event
detection into the gateway layer before data becomes only historical storage.
This enables the evaluation in later chapters: the baseline path measures raw
ingestion behavior, while the proposed path measures the cost and value of
adding edge intelligence.
