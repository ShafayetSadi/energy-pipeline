# Architecture: Edge-First Event-Driven Observability for Smart Energy Monitoring

> Repository document: `architecture.md`  
> Project type: ECE Thesis/Project implementation  
> Current scope: IoT + edge gateway + rule-based event processing + time-series observability  
> Future scope: AI/ML anomaly detection, load forecasting, and MLOps lifecycle

---

## 1. Project Summary

This project implements an edge-first, event-driven observability architecture for smart energy monitoring. STM32-based energy nodes measure electrical parameters such as voltage, current, and power, then publish telemetry through MQTT. A FastAPI-based edge gateway consumes the MQTT stream, validates payloads, detects rule-based events, classifies severity, stores time-series data in PostgreSQL/TimescaleDB, and exposes data to Grafana dashboards. Critical events trigger notifications.

The thesis contribution is the **edge gateway layer**, not only the sensor node or dashboard. The gateway acts as a local intelligence layer between IoT devices and long-term storage/cloud systems. The core architectural claim is an **edge-first, event-driven observability architecture for smart energy monitoring, with rule-based detection, time-series storage, and future ML extension points**.

---

## 2. Project Goals

### 2.1 Primary Goals

1. Build a working STM32/ESP-based energy monitoring node.
2. Publish voltage, current, power, and device status data using MQTT.
3. Use Mosquitto as the MQTT broker.
4. Build a FastAPI edge gateway that consumes MQTT messages.
5. Validate incoming telemetry data.
6. Detect abnormal conditions using a configurable rule engine.
7. Classify events as `NORMAL`, `WARNING`, or `CRITICAL`.
8. Store time-series readings and events in PostgreSQL/TimescaleDB.
9. Visualize measurements, device health, and events in Grafana.
10. Compare a baseline raw-ingestion system against the proposed event-driven edge-processing system.

### 2.2 Secondary Goals

1. Add Docker Compose for reproducible local deployment.
2. Add metrics collection for latency, throughput, validation failures, and event counts.
3. Add alert notifications through Slack, email, or webhook.
4. Prepare the schema for future AI/ML features.
5. Keep the architecture modular so AI agents/developers can work on different parts independently.

### 2.3 Non-Goals for Current Version

The following are intentionally outside the first implementation scope:

1. Full AI/ML anomaly detection.
2. LLM-based reasoning or chatbot interface.
3. National-scale smart-grid deployment.
4. Cloud-native Kubernetes deployment.
5. Commercial-grade billing/metering accuracy certification.
6. Production-grade electrical safety certification.
7. Complex user authentication/authorization.

These can be added later after the core system is stable.

---

## 3. High-Level Architecture

```text
┌─────────────────────────────┐
│     STM32 Energy Node       │
│  Voltage/Current Sensors    │
│  Local Power Calculation    │
└──────────────┬──────────────┘
               │
               │ MQTT telemetry/status/events
               ▼
┌─────────────────────────────┐
│        MQTT Broker          │
│        Mosquitto            │
└──────────────┬──────────────┘
               │
               │ Subscribed by Edge Gateway
               ▼
┌─────────────────────────────────────────────┐
│              Edge Gateway                   │
│              FastAPI Backend                │
├─────────────────────────────────────────────┤
│ MQTT Consumer                               │
│ Payload Validator                           │
│ Rule Engine                                 │
│ Event Classifier                            │
│ Aggregation/Downsampling                    │
│ Metrics Collector                           │
│ Alert Manager                               │
│ REST API                                    │
└──────────────┬──────────────────────────────┘
               │
      ┌────────┴─────────┐
      ▼                  ▼
┌──────────────┐   ┌────────  ──────────┐
│ TimescaleDB  │   │ Notification       │
│ PostgreSQL   │   │ Slack/Email/Webhook│
└──────┬───────┘   └────────────  ──────┘
       │
       ▼
┌─────────────────────────────┐
│       Grafana Dashboard     │
│ Real-Time Monitoring        │
│ Event Timeline              │
│ Device Health               │
│ Evaluation Metrics          │
└─────────────────────────────┘
```

---

## 4. Architectural Principles

1. **Edge-first processing:** The gateway performs validation and event detection before data is stored or forwarded.
2. **Event-driven design:** Critical events are detected and prioritized separately from normal telemetry.
3. **Time-series-first storage:** Sensor readings are stored as timestamped measurements optimized for time-window queries.
4. **Observability by design:** The system stores both energy data and operational metrics.
5. **Future ML extension points:** Rule-based events and historical readings can later be used as training data or weak labels.
6. **Modularity:** MQTT, gateway, database, dashboard, and notifications are separate services.
7. **Reproducibility:** The full backend stack should run through Docker Compose.
8. **Measurable thesis contribution:** Every major design decision should support measurable evaluation.

---

## 5. System Components

## 5.1 STM32 Energy Node

### Responsibility

The STM32 energy node is responsible for measuring electrical parameters and publishing telemetry to MQTT.

### Hardware Components

Minimum hardware:

```text
Voltage Sensor
Current Sensor
STM32 Microcontroller
ESP8266 or ESP32 Wi-Fi Module
Power Supply
Optional Temperature Sensor
```

Recommended practical setup:

```text
STM32 + ESP32
```

ESP8266 is acceptable for a prototype, but ESP32 is preferable if TLS, larger payloads, or future device-side processing are needed.

### Node Responsibilities

1. Sample voltage from voltage sensor.
2. Sample current from current sensor.
3. Optionally sample temperature.
4. Calculate instantaneous power.
5. Generate timestamped telemetry payload.
6. Publish telemetry to MQTT broker.
7. Publish device status such as online/offline/heartbeat.
8. Optionally receive configuration from MQTT command topics.

### Sampling Strategy

For thesis implementation, use a simple fixed interval.

Recommended initial interval:

```text
1 message every 1–5 seconds per device
```

Avoid very high-frequency streaming in the first version unless required for evaluation.

### Local Calculation

Basic calculation:

```text
power_w = voltage_v × current_a
```

Optional future calculations:

```text
energy_wh = cumulative(power_w × time_hours)
apparent_power_va = voltage_rms × current_rms
power_factor = real_power_w / apparent_power_va
```

### Device ID Convention

Use stable IDs:

```text
house_001
house_002
lab_node_001
```

Device IDs must be unique and should not contain spaces.

---

## 5.2 MQTT Broker: Mosquitto

### Responsibility

The MQTT broker decouples sensor publishers from backend subscribers. Devices publish data to topics; the edge gateway subscribes to the required topic patterns.

### Broker Service

Recommended broker:

```text
Eclipse Mosquitto
```

### MQTT Topic Design

Use separated topics for telemetry, status, events, and commands.

```text
energy/{device_id}/telemetry
energy/{device_id}/status
energy/{device_id}/events
energy/{device_id}/commands
energy/{device_id}/config
```

Examples:

```text
energy/house_001/telemetry
energy/house_001/status
energy/house_001/events
energy/house_001/commands
```

### Gateway Subscriptions

The edge gateway should subscribe to:

```text
energy/+/telemetry
energy/+/status
energy/+/events
```

Alternative broad subscription for early prototyping:

```text
energy/#
```

Use the more specific subscriptions once the topic structure is stable.

### QoS Policy

Recommended QoS:

| Message Type              | Recommended QoS | Reason                                           |
| ------------------------- | --------------: | ------------------------------------------------ |
| Frequent normal telemetry |               0 | Lower overhead; acceptable for periodic readings |
| Critical event            |               1 | At-least-once delivery is useful for alerts      |
| Device status             |               1 | Useful for health monitoring                     |
| Configuration command     |               1 | Should not be silently lost                      |

### Retained Messages

Use retained messages only for status/config topics, not high-frequency telemetry.

Recommended retained topics:

```text
energy/{device_id}/status
energy/{device_id}/config
```

Avoid retaining:

```text
energy/{device_id}/telemetry
```

### Last Will and Testament

Each device should register a Last Will message so the broker can publish offline status if the device disconnects unexpectedly.

Example Last Will topic:

```text
energy/house_001/status
```

Example Last Will payload:

```json
{
  "device_id": "house_001",
  "status": "offline",
  "reason": "unexpected_disconnect",
  "timestamp": "broker_time_or_device_time"
}
```

---

## 5.3 Edge Gateway: FastAPI Backend

### Responsibility

The edge gateway is the central processing layer. It consumes MQTT messages, validates payloads, runs rules, stores data, exposes REST APIs, collects metrics, and triggers alerts.

### Technology

```text
Python
FastAPI
Asyncio
Pydantic
SQLAlchemy or SQLModel
asyncpg or psycopg
paho-mqtt or gmqtt
```

### Internal Modules

```text
app/
  main.py
  config.py
  mqtt/
    client.py
    handlers.py
    topics.py
  schemas/
    telemetry.py
    status.py
    events.py
  services/
    validation_service.py
    rule_engine.py
    event_classifier.py
    aggregation_service.py
    alert_service.py
    metrics_service.py
  db/
    session.py
    models.py
    repositories.py
  api/
    health.py
    devices.py
    readings.py
    events.py
    metrics.py
  workers/
    mqtt_consumer.py
    device_heartbeat.py
    aggregation_worker.py
```

### Runtime Responsibilities

1. Connect to MQTT broker.
2. Subscribe to telemetry/status topics.
3. Parse JSON payloads.
4. Validate schema and physical ranges.
5. Store valid readings.
6. Store rejected/invalid readings in a data-quality log.
7. Apply rule engine to valid readings.
8. Create events if rules are triggered.
9. Classify event severity.
10. Trigger alert workflow for critical events.
11. Expose REST endpoints for devices/readings/events/metrics.
12. Export operational metrics for evaluation.

---

## 6. Data Flow

## 6.1 Normal Telemetry Flow

```text
STM32 Node
  ↓ publish telemetry
Mosquitto Broker
  ↓ gateway subscription
FastAPI MQTT Consumer
  ↓ parse JSON
Payload Validator
  ↓ valid payload
Rule Engine
  ↓ no critical condition
TimescaleDB/PostgreSQL
  ↓ query
Grafana Dashboard
```

## 6.2 Critical Event Flow

```text
STM32 Node
  ↓ publish telemetry
Mosquitto Broker
  ↓ gateway subscription
FastAPI MQTT Consumer
  ↓ parse JSON
Payload Validator
  ↓ valid payload
Rule Engine
  ↓ abnormal condition detected
Event Classifier
  ↓ WARNING or CRITICAL
Events Table
  ↓
Alert Manager
  ↓
Slack/Email/Webhook
  ↓
Grafana Event Timeline
```

## 6.3 Invalid Payload Flow

```text
Incoming MQTT Message
  ↓
Payload Validator
  ↓ invalid schema/range/timestamp
Data Quality Log
  ↓
Metrics Counter Increment
  ↓
Optional warning event if repeated invalid payloads occur
```

## 6.4 Device Offline Flow

```text
Device fails unexpectedly
  ↓
MQTT Broker publishes Last Will message
  ↓
Gateway receives offline status
  ↓
Device status updated
  ↓
DEVICE_FAILURE event created
  ↓
Grafana + Notification
```

---

## 7. Data Contracts

## 7.1 Telemetry Payload

Topic:

```text
energy/{device_id}/telemetry
```

Payload:

```json
{
  "schema_version": "1.0",
  "device_id": "house_001",
  "timestamp": "2026-06-15T12:00:00Z",
  "voltage_v": 221.4,
  "current_a": 2.3,
  "power_w": 509.2,
  "temperature_c": 33.5,
  "sequence_no": 1024
}
```

Required fields:

```text
schema_version
device_id
timestamp
voltage_v
current_a
power_w
```

Optional fields:

```text
temperature_c
sequence_no
firmware_version
rssi_dbm
```

## 7.2 Status Payload

Topic:

```text
energy/{device_id}/status
```

Payload:

```json
{
  "schema_version": "1.0",
  "device_id": "house_001",
  "status": "online",
  "timestamp": "2026-06-15T12:00:00Z",
  "firmware_version": "0.1.0",
  "ip_address": "192.168.1.50",
  "rssi_dbm": -62
}
```

Allowed status values:

```text
online
offline
maintenance
error
```

## 7.3 Event Payload from Device

Device-originated events are optional. Most events should be generated by the edge gateway.

Topic:

```text
energy/{device_id}/events
```

Payload:

```json
{
  "schema_version": "1.0",
  "device_id": "house_001",
  "timestamp": "2026-06-15T12:00:05Z",
  "event_type": "SENSOR_ERROR",
  "severity": "WARNING",
  "message": "Current sensor reading unavailable"
}
```

---

## 8. Validation Rules

## 8.1 Schema Validation

Reject payload if:

1. JSON is malformed.
2. Required fields are missing.
3. Field types are incorrect.
4. `device_id` in topic does not match `device_id` in payload.
5. Timestamp cannot be parsed.
6. Schema version is unsupported.

## 8.2 Physical Range Validation

Initial suggested ranges:

| Field           | Minimum |      Maximum | Action if outside range             |
| --------------- | ------: | -----------: | ----------------------------------- |
| `voltage_v`     |       0 |          300 | Reject or mark invalid              |
| `current_a`     |       0 | configurable | Reject or create warning            |
| `power_w`       |       0 | configurable | Reject or create warning            |
| `temperature_c` |     -20 |          100 | Warning/invalid depending on sensor |

For Bangladesh/South Asian household AC monitoring, voltage thresholds may be adapted based on the expected mains range and supervisor guidance.

## 8.3 Timestamp Validation

Rules:

1. Timestamp must be ISO-8601 format.
2. Timestamp should not be too far in the future.
3. Timestamp should not be older than a configurable limit unless replay mode is enabled.

Recommended defaults:

```text
MAX_FUTURE_SKEW_SECONDS=60
MAX_PAST_SKEW_SECONDS=86400
```

## 8.4 Duplicate Detection

Use `device_id + sequence_no` if available.

If `sequence_no` is not available, use:

```text
device_id + timestamp
```

Duplicate policy:

```text
Do not insert duplicate readings.
Increment duplicate counter.
Log duplicate for evaluation.
```

---

## 9. Rule Engine

## 9.1 Purpose

The rule engine detects abnormal conditions before the data is stored or forwarded. This is the main edge-processing contribution.

## 9.2 Rule Configuration

Rules must be configurable, not hardcoded only in Python.

Recommended configuration file:

```text
config/rules.yaml
```

Example:

```yaml
rules:
  undervoltage:
    enabled: true
    event_type: UNDER_VOLTAGE
    severity: WARNING
    condition:
      field: voltage_v
      operator: lt
      value: 200

  overvoltage:
    enabled: true
    event_type: OVER_VOLTAGE
    severity: WARNING
    condition:
      field: voltage_v
      operator: gt
      value: 250

  overload:
    enabled: true
    event_type: OVERLOAD
    severity: CRITICAL
    condition:
      field: current_a
      operator: gt
      value: 10

  power_spike:
    enabled: true
    event_type: POWER_SPIKE
    severity: WARNING
    condition:
      type: percentage_increase
      field: power_w
      percent: 30
      window_seconds: 60

  device_offline:
    enabled: true
    event_type: DEVICE_FAILURE
    severity: CRITICAL
    condition:
      type: heartbeat_timeout
      timeout_seconds: 30
```

## 9.3 Event Types

Required event types:

```text
UNDER_VOLTAGE
OVER_VOLTAGE
OVERLOAD
POWER_SPIKE
DEVICE_FAILURE
INVALID_PAYLOAD
SENSOR_ERROR
NORMAL_RECOVERY
```

Optional future event types:

```text
ANOMALY_DETECTED
FORECASTED_OVERLOAD
MODEL_DRIFT_DETECTED
```

## 9.4 Severity Levels

```text
NORMAL
INFO
WARNING
CRITICAL
```

Severity definitions:

| Severity | Meaning                                | Notification?              |
| -------- | -------------------------------------- | -------------------------- |
| NORMAL   | No abnormal condition                  | No                         |
| INFO     | Useful operational event               | Optional                   |
| WARNING  | Abnormal but not immediately dangerous | Optional or dashboard only |
| CRITICAL | Requires immediate attention           | Yes                        |

## 9.5 Rule Evaluation Order

Recommended order:

1. Data quality validation.
2. Device health/status rules.
3. Electrical safety rules.
4. Trend/window rules.
5. Recovery rules.

## 9.6 Event Deduplication

Avoid sending repeated alerts every second for the same condition.

Deduplication key:

```text
device_id + event_type + severity
```

Cooldown:

```text
ALERT_COOLDOWN_SECONDS=300
```

If the same event persists, update event count instead of creating infinite alerts.

---

## 10. Storage Design

## 10.1 Database Choice

Start with PostgreSQL. Use TimescaleDB when time-series performance and retention policies become important.

## 10.2 Tables Overview

```text
devices
energy_readings
events
data_quality_logs
device_status_history
system_metrics
rule_definitions
alert_deliveries
model_predictions        # future extension
```

## 10.3 SQL Schema Draft

```sql
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    location TEXT,
    device_type TEXT DEFAULT 'energy_node',
    firmware_version TEXT,
    status TEXT DEFAULT 'unknown',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS energy_readings (
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL REFERENCES devices(device_id),
    voltage_v DOUBLE PRECISION NOT NULL,
    current_a DOUBLE PRECISION NOT NULL,
    power_w DOUBLE PRECISION NOT NULL,
    temperature_c DOUBLE PRECISION,
    sequence_no BIGINT,
    raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, device_id)
);

CREATE INDEX IF NOT EXISTS idx_energy_readings_device_time
ON energy_readings (device_id, time DESC);

CREATE TABLE IF NOT EXISTS events (
    event_id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT REFERENCES devices(device_id),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    rule_name TEXT,
    message TEXT,
    reading_time TIMESTAMPTZ,
    event_value DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    metadata JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_device_time
ON events (device_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_events_type_severity
ON events (event_type, severity, time DESC);

CREATE TABLE IF NOT EXISTS data_quality_logs (
    log_id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    topic TEXT,
    device_id TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT,
    raw_payload TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS device_status_history (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL REFERENCES devices(device_id),
    status TEXT NOT NULL,
    firmware_version TEXT,
    ip_address TEXT,
    rssi_dbm DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_metrics (
    time TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    labels JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rule_definitions (
    rule_name TEXT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_deliveries (
    alert_id BIGSERIAL PRIMARY KEY,
    event_id BIGINT REFERENCES events(event_id),
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    response TEXT,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- Future AI/ML extension table. It can remain unused in v1.
CREATE TABLE IF NOT EXISTS model_predictions (
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL REFERENCES devices(device_id),
    model_version TEXT NOT NULL,
    prediction_type TEXT NOT NULL,
    anomaly_score DOUBLE PRECISION,
    predicted_label TEXT,
    input_window_start TIMESTAMPTZ,
    input_window_end TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, device_id, model_version, prediction_type)
);
```

## 10.4 TimescaleDB Hypertables

If TimescaleDB is enabled, convert time-series tables into hypertables.

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;

SELECT create_hypertable('energy_readings', 'time', if_not_exists => TRUE);
SELECT create_hypertable('events', 'time', if_not_exists => TRUE);
SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);
SELECT create_hypertable('device_status_history', 'time', if_not_exists => TRUE);
```

## 10.5 Retention Policy

Recommended retention strategy:

| Data                | Retention                       |
| ------------------- | ------------------------------- |
| Raw readings        | 7–30 days for prototype         |
| Aggregated readings | Several months                  |
| Critical events     | Permanent for thesis evaluation |
| Data quality logs   | 7–30 days                       |
| System metrics      | 7–30 days                       |

For thesis, keep enough data to produce evaluation charts.

## 10.6 Aggregated Data

Do not simply discard normal data. Instead:

```text
Raw data → short-term storage
Normal data → aggregated long-term storage
Critical events → permanent event log + notification
```

Potential continuous aggregates:

```sql
-- Example only; adjust after TimescaleDB setup.
CREATE MATERIALIZED VIEW IF NOT EXISTS energy_readings_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    device_id,
    AVG(voltage_v) AS avg_voltage_v,
    AVG(current_a) AS avg_current_a,
    AVG(power_w) AS avg_power_w,
    MAX(power_w) AS max_power_w,
    MIN(voltage_v) AS min_voltage_v,
    COUNT(*) AS sample_count
FROM energy_readings
GROUP BY bucket, device_id;
```

---

## 11. REST API Design

The REST API is for dashboard support, testing, data export, and AI agent integration.

## 11.1 Health Endpoints

```text
GET /health
GET /ready
GET /version
```

Example `/health` response:

```json
{
  "status": "ok",
  "service": "edge-gateway",
  "version": "0.1.0"
}
```

## 11.2 Device Endpoints

```text
GET /api/v1/devices
GET /api/v1/devices/{device_id}
POST /api/v1/devices
PATCH /api/v1/devices/{device_id}
GET /api/v1/devices/{device_id}/status
```

## 11.3 Reading Endpoints

```text
GET /api/v1/readings
GET /api/v1/readings/{device_id}
GET /api/v1/readings/{device_id}/latest
GET /api/v1/readings/{device_id}/aggregate
```

Query parameters:

```text
start_time
end_time
limit
interval
```

Example:

```text
GET /api/v1/readings/house_001?start_time=2026-06-15T00:00:00Z&end_time=2026-06-15T23:59:59Z
```

## 11.4 Event Endpoints

```text
GET /api/v1/events
GET /api/v1/events/{event_id}
GET /api/v1/devices/{device_id}/events
POST /api/v1/events/{event_id}/acknowledge
```

## 11.5 Metrics Endpoints

```text
GET /api/v1/metrics/summary
GET /api/v1/metrics/latency
GET /api/v1/metrics/throughput
GET /api/v1/metrics/data-reduction
```

## 11.6 Rule Endpoints

```text
GET /api/v1/rules
GET /api/v1/rules/{rule_name}
PATCH /api/v1/rules/{rule_name}
POST /api/v1/rules/reload
```

Rules may be file-based first. Database/API-based rule editing can be added later.

---

## 12. Grafana Dashboard Specification

## 12.1 Dashboard 1: Energy Overview

Panels:

1. Latest voltage per device.
2. Latest current per device.
3. Latest power per device.
4. Total active devices.
5. Total events in last 24 hours.
6. Critical events in last 24 hours.

## 12.2 Dashboard 2: Device Detail

Variable:

```text
device_id
```

Panels:

1. Voltage over time.
2. Current over time.
3. Power over time.
4. Temperature over time, if available.
5. Event annotations over power chart.
6. Device status timeline.
7. RSSI signal strength, if available.

## 12.3 Dashboard 3: Event Timeline

Panels:

1. Events table.
2. Event count by type.
3. Event count by severity.
4. Critical event timeline.
5. Unacknowledged events.

## 12.4 Dashboard 4: System Observability

Panels:

1. MQTT messages received per minute.
2. Validation failures per minute.
3. Database write latency.
4. End-to-end processing latency.
5. Gateway CPU/RAM, if exported.
6. MQTT connection status.

## 12.5 Dashboard 5: Thesis Evaluation

Panels:

1. Baseline storage growth.
2. Proposed storage growth.
3. Data reduction ratio.
4. Baseline latency.
5. Proposed latency.
6. Throughput comparison.
7. Alert latency distribution.

---

## 13. Alerting Design

## 13.1 Alert Channels

Initial recommended channels:

```text
Console log
Webhook
Slack webhook
Email, optional
```

## 13.2 Alert Trigger Policy

Send alert when:

```text
severity == CRITICAL
```

Optional alert when:

```text
severity == WARNING and repeated more than N times in M minutes
```

## 13.3 Alert Payload

```json
{
  "event_id": 123,
  "device_id": "house_001",
  "event_type": "OVERLOAD",
  "severity": "CRITICAL",
  "time": "2026-06-15T12:00:05Z",
  "message": "Current exceeded configured threshold",
  "value": 12.5,
  "threshold": 10.0
}
```

## 13.4 Alert Deduplication

Use cooldown to avoid alert spam.

```text
ALERT_COOLDOWN_SECONDS=300
```

If the same event remains active:

```text
Update existing event count
Do not send repeated notifications every sample
```

---

## 14. Baseline vs Proposed Evaluation

## 14.1 Mode A: Baseline Raw Ingestion

```text
STM32 Node
  ↓
MQTT Broker
  ↓
Database
  ↓
Grafana
```

Characteristics:

1. Every valid reading is stored directly.
2. No rule engine before storage.
3. Alerts may be generated only after database query/dashboard alerting.
4. Higher storage growth.
5. Less edge intelligence.

## 14.2 Mode B: Proposed Edge Processing

```text
STM32 Node
  ↓
MQTT Broker
  ↓
Edge Gateway
  ↓
Validation + Rule Engine + Aggregation
  ↓
Database + Alerts + Grafana
```

Characteristics:

1. Data is validated before storage.
2. Critical events are detected immediately.
3. Normal data can be downsampled/aggregated for long-term storage.
4. Invalid data is logged separately.
5. Lower long-term storage growth.
6. Faster alert response.

## 14.3 Metrics

### End-to-End Latency

```text
latency_ms = dashboard_or_db_insert_time - device_timestamp
```

Alternative if device timestamp is unreliable:

```text
latency_ms = gateway_processed_time - gateway_received_time
```

### Event Detection Latency

```text
event_detection_latency_ms = event_created_time - telemetry_received_time
```

### Alert Latency

```text
alert_latency_ms = alert_sent_time - event_created_time
```

### Throughput

```text
throughput = total_messages_processed / total_test_duration_seconds
```

### Validation Failure Rate

```text
validation_failure_rate = invalid_payload_count / total_payload_count
```

### Data Reduction Ratio

```text
data_reduction_ratio = 1 - (proposed_storage_rows / baseline_storage_rows)
```

or by storage size:

```text
storage_reduction_ratio = 1 - (proposed_storage_size_mb / baseline_storage_size_mb)
```

### Event Detection Accuracy

If synthetic ground-truth events are available:

```text
precision = true_positives / (true_positives + false_positives)
recall = true_positives / (true_positives + false_negatives)
f1_score = 2 * precision * recall / (precision + recall)
```

For rule-based implementation, ground truth can be generated using scripted test payloads.

---

## 15. Test Data and Simulation

## 15.1 Why Simulation Is Needed

If hardware availability is limited, generate MQTT messages using a simulator. The simulator should behave like multiple devices.

## 15.2 Simulator Responsibilities

1. Publish normal telemetry.
2. Publish undervoltage scenarios.
3. Publish overload scenarios.
4. Publish power spike scenarios.
5. Publish malformed payloads.
6. Simulate device offline by stopping heartbeat.
7. Generate configurable message rates for throughput tests.

## 15.3 Simulator Directory

```text
simulator/
  mqtt_publisher.py
  scenarios/
    normal.yaml
    undervoltage.yaml
    overload.yaml
    power_spike.yaml
    invalid_payloads.yaml
    high_throughput.yaml
```

## 15.4 Example Scenario

```yaml
scenario_name: overload_test
num_devices: 3
duration_seconds: 300
publish_interval_seconds: 1
anomalies:
  - device_id: house_001
    start_after_seconds: 60
    duration_seconds: 30
    type: overload
    current_a: 12.5
```

---

## 16. Docker Compose Architecture

## 16.1 Services

Required services:

```text
mosquitto
edge-gateway
postgres or timescaledb
grafana
pgadmin, optional
simulator, optional
```

## 16.2 Compose Service Relationships

```text
simulator → mosquitto → edge-gateway → timescaledb → grafana
```

## 16.3 Environment Variables

```env
APP_ENV=development
LOG_LEVEL=INFO

MQTT_HOST=mosquitto
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_CLIENT_ID=edge-gateway
MQTT_TELEMETRY_TOPIC=energy/+/telemetry
MQTT_STATUS_TOPIC=energy/+/status

DATABASE_URL=postgresql+asyncpg://energy:energy@timescaledb:5432/energy_monitoring

ALERT_WEBHOOK_URL=
ALERT_COOLDOWN_SECONDS=300

RULES_FILE=/app/config/rules.yaml

ENABLE_TIMESCALE=true
ENABLE_SIMULATOR=false
```

## 16.4 Suggested Repository Structure

```text
energy-edge-monitoring/
  architecture.md
  README.md
  docker-compose.yml
  .env.example
  docs/
    thesis-notes.md
    evaluation-plan.md
    api-contract.md
  firmware/
    stm32-energy-node/
      README.md
      src/
  gateway/
    Dockerfile
    pyproject.toml
    app/
      main.py
      config.py
      mqtt/
      schemas/
      services/
      db/
      api/
      workers/
    tests/
    alembic/
  config/
    mosquitto.conf
    rules.yaml
    grafana/
      dashboards/
      provisioning/
  database/
    init.sql
    migrations/
  simulator/
    mqtt_publisher.py
    scenarios/
  scripts/
    run_baseline_test.sh
    run_proposed_test.sh
    export_results.py
  results/
    README.md
```

---

## 17. Security Design

## 17.1 Current Prototype Security

For local prototype:

1. Run all services in a private Docker network.
2. Use MQTT username/password if possible.
3. Do not expose database ports publicly.
4. Do not commit secrets to GitHub.
5. Use `.env.example` and keep real `.env` ignored.

## 17.2 Future Security Enhancements

1. MQTT over TLS.
2. Client certificates for devices.
3. Per-device MQTT credentials.
4. Topic-level authorization.
5. FastAPI authentication.
6. Grafana user roles.
7. Secure alert webhooks.
8. Audit logs.

## 17.3 Practical TLS Note

If ESP8266 is used, TLS may be difficult due to memory constraints. For thesis prototype, first build local-network MQTT without TLS. Then document TLS as an enhancement, or use ESP32 if TLS becomes required.

---

## 18. Future AI/ML Extension

AI/ML is not part of the first implementation, but the architecture should prepare for it.

## 18.1 Future ML Features

Potential features:

1. Unsupervised anomaly detection.
2. Load forecasting.
3. Device behavior profiling.
4. Dynamic threshold learning.
5. Energy consumption pattern clustering.
6. Model drift monitoring.
7. Automated retraining pipeline.

## 18.2 Future ML Pipeline

```text
TimescaleDB Historical Data
  ↓
Dataset Export
  ↓
Feature Engineering
  ↓
Model Training
  ↓
Model Evaluation
  ↓
Model Registry
  ↓
Edge Deployment
  ↓
Prediction Logging
  ↓
Drift Monitoring
```

## 18.3 Future Feature Examples

```text
rolling_avg_power_1min
rolling_avg_power_5min
max_current_5min
voltage_stddev_5min
power_spike_count_1h
hour_of_day
day_of_week
```

## 18.4 Model Prediction Contract

Future prediction output:

```json
{
  "device_id": "house_001",
  "timestamp": "2026-06-15T12:00:00Z",
  "model_version": "iforest_v1",
  "prediction_type": "anomaly_detection",
  "anomaly_score": 0.91,
  "predicted_label": "ANOMALY"
}
```

## 18.5 Why Current Design Supports AI Later

The system stores:

1. Raw and aggregated time-series data.
2. Rule-triggered events.
3. Device metadata.
4. Data-quality logs.
5. Operational metrics.
6. Future model prediction table.

This makes it possible to build ML datasets later without redesigning the whole project.

---

## 19. AI Agent Build Instructions

This section is written for AI coding agents or future contributors.

## 19.1 Build Order

Implement in this order:

1. `docker-compose.yml` with Mosquitto, TimescaleDB/PostgreSQL, Grafana.
2. Database schema and migrations.
3. FastAPI health endpoint.
4. MQTT connection from gateway to broker.
5. Telemetry schema validation.
6. Insert valid telemetry into database.
7. MQTT simulator for test messages.
8. Rule engine with basic threshold rules.
9. Event table insertion.
10. Alert manager with console/webhook output.
11. Grafana dashboards.
12. Evaluation scripts for baseline vs proposed modes.
13. Documentation and thesis result export.

## 19.2 Coding Rules for Agents

1. Do not hardcode secrets.
2. Do not hardcode rule thresholds in multiple places; use `rules.yaml` or database-backed rules.
3. Validate every external MQTT payload with Pydantic or equivalent schema validation.
4. Keep MQTT handlers thin; put logic in services.
5. Store raw payload for debugging when possible.
6. Log invalid payloads; do not silently discard them.
7. Use structured logging.
8. Write tests for validation and rule engine.
9. Keep baseline mode and proposed mode switchable through configuration.
10. Do not add AI/ML dependencies in v1 unless explicitly requested.

## 19.3 Configuration Flags

Use flags to control behavior:

```env
PROCESSING_MODE=proposed
STORE_RAW_READINGS=true
ENABLE_AGGREGATION=true
ENABLE_ALERTS=true
ENABLE_RULE_ENGINE=true
ENABLE_ML=false
```

Allowed `PROCESSING_MODE` values:

```text
baseline
proposed
```

## 19.4 Minimum Acceptance Criteria

A build is acceptable when:

1. Docker Compose starts core services.
2. Simulator publishes MQTT telemetry.
3. Gateway receives telemetry.
4. Valid telemetry is stored in database.
5. Invalid telemetry is logged.
6. Rule engine creates at least four event types:
   - `UNDER_VOLTAGE`
   - `OVERLOAD`
   - `POWER_SPIKE`
   - `DEVICE_FAILURE`
7. Grafana shows voltage/current/power charts.
8. Grafana shows event timeline.
9. Alert manager triggers for `CRITICAL` events.
10. Evaluation script can compare baseline and proposed modes.

---

## 20. Development Milestones

## Milestone 1: Infrastructure

Deliverables:

1. Docker Compose stack.
2. Mosquitto running.
3. PostgreSQL/TimescaleDB running.
4. Grafana running.
5. FastAPI `/health` endpoint.

## Milestone 2: Data Ingestion

Deliverables:

1. MQTT simulator.
2. Gateway MQTT consumer.
3. Telemetry validation.
4. Database insertion.
5. Basic reading API.

## Milestone 3: Event Processing

Deliverables:

1. Rule engine.
2. Event classifier.
3. Event storage.
4. Device offline detection.
5. Alert manager.

## Milestone 4: Dashboard

Deliverables:

1. Energy overview dashboard.
2. Device detail dashboard.
3. Event timeline dashboard.
4. System metrics dashboard.

## Milestone 5: Thesis Evaluation

Deliverables:

1. Baseline test mode.
2. Proposed test mode.
3. Synthetic scenarios.
4. Latency measurement.
5. Throughput measurement.
6. Storage/data reduction measurement.
7. Exported result tables and charts.

## Milestone 6: Hardware Integration

Deliverables:

1. STM32 ADC sampling.
2. ESP Wi-Fi MQTT publishing.
3. Real telemetry visible in Grafana.
4. At least one abnormal condition test.

---

## 21. Thesis Chapter Mapping

## Chapter 1: Introduction

Discuss smart energy monitoring, IoT, edge processing, and the need for event-driven monitoring.

## Chapter 2: Background and Literature Review

Topics:

1. Smart grid and smart metering.
2. IoT communication protocols.
3. MQTT publish/subscribe architecture.
4. Edge computing.
5. Time-series databases.
6. Observability dashboards.
7. Rule-based event detection.
8. Future AI/ML anomaly detection.

## Chapter 3: System Architecture

Use this document as the base.

## Chapter 4: Implementation

Describe hardware, firmware, MQTT topics, gateway modules, database schema, dashboards, and Docker deployment.

## Chapter 5: Evaluation

Compare baseline and proposed modes.

## Chapter 6: Results and Discussion

Present latency, throughput, storage reduction, event detection, and dashboard screenshots.

## Chapter 7: Conclusion and Future Work

Discuss AI/ML extension, TLS security, more devices, cloud integration, and model-based anomaly detection.

---

## 22. Recommended Names

Project name options:

```text
EdgeGrid Monitor
SmartEdge Energy Monitor
EnergyEdge Observability
Edge-Monitor for Smart Energy Systems
```

Recommended thesis title:

```text
Design and Implementation of an Event-Driven Edge Gateway for IoT-Based Smart Energy Monitoring
```

Alternative title emphasizing the architecture claim:

```text
An Edge-First, Event-Driven Observability Architecture for Smart Energy Monitoring
```

---

## 23. Reference Documentation for Developers

These are useful implementation references for humans and AI coding agents:

1. MQTT official site: https://mqtt.org/
2. Eclipse Mosquitto: https://mosquitto.org/
3. MQTT/Mosquitto concepts: https://mosquitto.org/man/mqtt-7.html
4. FastAPI documentation: https://fastapi.tiangolo.com/
5. TimescaleDB documentation: https://docs.timescale.com/
6. TimescaleDB GitHub: https://github.com/timescale/timescaledb
7. Grafana PostgreSQL data source: https://grafana.com/docs/grafana/latest/datasources/postgres/
8. Docker Compose documentation: https://docs.docker.com/compose/
9. PostgreSQL JSON/JSONB documentation: https://www.postgresql.org/docs/current/datatype-json.html

---

## 24. Final Architecture Statement

The system implements an STM32-based smart energy monitoring node that publishes measurements through MQTT. A Mosquitto broker routes telemetry to a FastAPI-based edge gateway. The gateway validates payloads, applies rule-based event detection, classifies abnormal conditions, stores time-series data and events in PostgreSQL/TimescaleDB, and triggers notifications for critical events. Grafana provides real-time observability and thesis evaluation dashboards. The system is evaluated by comparing a baseline raw-ingestion architecture against the proposed event-driven edge-processing architecture using latency, throughput, storage growth, data reduction, and event detection metrics. The final architecture claim is that this is an edge-first, event-driven observability architecture for smart energy monitoring, with rule-based detection, time-series storage, and future ML extension points.
