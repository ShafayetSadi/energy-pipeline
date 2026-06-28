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
| `model_predictions` | Future AI/ML prediction storage |

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

## 4.9 Metrics and Alert Workflow

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

## 4.10 Dashboard Implementation

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

## 4.11 Docker-Based Deployment

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
`ENABLE_AGGREGATION`, and `ENABLE_ALERTS`. This makes it possible to switch
between baseline and proposed modes for evaluation.

## 4.12 Testing Strategy

The testing strategy combines automated tests and scripted system experiments.

Automated tests cover:

- MQTT topic parsing
- payload validation
- rule engine behavior
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
| `scripts/export_results.py` | Export metrics snapshots and Markdown reports |

This strategy keeps the thesis evaluation reproducible. The automated tests
verify the implementation pieces, while the experiment scripts generate the
evidence used in Chapter 6.

## 4.13 Chapter Summary

The implementation follows the proposed architecture closely. MQTT messages
enter through Mosquitto, the FastAPI gateway validates and processes them,
TimescaleDB stores readings and events, Grafana visualizes the system state,
and scripts export reproducible evaluation evidence. The implementation is
rule-based and observable, with explicit extension points for future ML
prediction and storage optimization.
