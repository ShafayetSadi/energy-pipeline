# 2026-06-28 Experimental Run Notes

## Context

Both benchmark scripts were executed successfully:

- `just baseline`
- `just proposed`

The baseline run used the gateway in raw-ingestion mode with the rule engine, aggregation, and alerts disabled. The proposed run used the gateway in event-driven mode with the rule engine, aggregation, and alerts enabled.

These notes are working material for Chapter 5 and Chapter 6. They should not be copied directly into the final thesis without cleaning the experimental method and rerunning with a reset database.

## Baseline Run Summary

Configuration:

- `PROCESSING_MODE=baseline`
- `STORE_RAW_READINGS=true`
- `ENABLE_RULE_ENGINE=false`
- `ENABLE_AGGREGATION=false`
- `ENABLE_ALERTS=false`

Scenario:

- `high_throughput.yaml`
- 200 devices
- 1.0 second interval
- 120 seconds

Simulator output:

- Total sent: `23941`
- Failed: `0`
- Simulator rate: `199.47 msg/s`

Exported gateway counters:

- `messages.received`: `24730`
- `messages.telemetry`: `23493`
- `messages.status`: `789`
- `readings.stored`: `23493`
- `validation.failures`: `448`
- `validation.telemetry.success`: `23493`
- `validation.status.success`: `789`

Latency:

| Operation | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: |
| telemetry | 4.04 ms | 3.97 ms | 4.83 ms | 5.38 ms |
| status | 3.80 ms | 3.68 ms | 4.69 ms | 5.71 ms |

Initial interpretation:

- The baseline gateway sustained approximately 200 messages per second from the simulator.
- MQTT publishing completed without simulator-side failures.
- Gateway telemetry processing latency stayed in the low-millisecond range.

## Proposed Run Summary

Configuration:

- `PROCESSING_MODE=proposed`
- `STORE_RAW_READINGS=true`
- `ENABLE_RULE_ENGINE=true`
- `ENABLE_AGGREGATION=true`
- `ENABLE_ALERTS=true`

Scenarios:

- `undervoltage.yaml`
- `overload.yaml`
- `power_spike.yaml`
- `invalid_payloads.yaml`
- `high_throughput.yaml`

Simulator output:

| Scenario | Total sent | Failed | Rate |
| --- | ---: | ---: | ---: |
| undervoltage | 450 | 0 | 2.50 msg/s |
| overload | 448 | 0 | 2.49 msg/s |
| power spike | 478 | 0 | 1.99 msg/s |
| invalid payloads | 482 | 0 | 4.02 msg/s |
| high throughput | 23947 | 0 | 199.54 msg/s |

Exported gateway counters:

- `messages.received`: `26628`
- `messages.telemetry`: `25162`
- `messages.status`: `823`
- `readings.stored`: `25162`
- `validation.failures`: `643`
- `validation.telemetry.success`: `25162`
- `validation.status.success`: `823`

Event counters:

- `events.critical`: `4463`
- `events.warning`: `6508`
- `events.info`: `31`
- `events.type.device_failure`: `317`
- `events.type.overload`: `4146`
- `events.type.power_spike`: `6462`
- `events.type.under_voltage`: `31`
- `events.type.over_voltage`: `15`
- `events.type.voltage_anomaly`: `31`

Latency:

| Operation | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: |
| telemetry | 4.50 ms | 4.40 ms | 5.75 ms | 6.46 ms |
| status | 4.04 ms | 3.90 ms | 5.22 ms | 5.84 ms |

Initial interpretation:

- The proposed gateway sustained the high-throughput scenario at approximately the same simulator rate as baseline.
- Rule processing and event generation added a small processing overhead.
- Telemetry average latency increased from 4.04 ms to 4.50 ms.
- Telemetry p99 latency increased from 5.38 ms to 6.46 ms.
- The proposed mode successfully produced critical, warning, and info events from synthetic anomaly scenarios.

## Valid Thesis Claims From This Run

The current run supports these claims:

- The system can ingest MQTT telemetry at approximately 200 messages per second in both baseline and proposed modes.
- The proposed event-driven gateway adds rule evaluation and event creation with low millisecond-level processing overhead.
- The proposed mode detects multiple classes of abnormal electrical behavior, including overload, power spike, under-voltage, over-voltage, voltage anomaly, and device failure.
- Invalid payload handling is active and measurable through validation failure counters.
- The experiment demonstrates functional integration among simulator, MQTT broker, gateway, TimescaleDB, and metrics export.

## Claims Not Yet Supported

The current run does not yet support these claims:

- It does not prove storage reduction, because both runs used `STORE_RAW_READINGS=true`.
- It does not provide a clean database-size comparison, because the database was not reset before the runs.
- It does not provide a strict A/B comparison for all counters, because baseline ran only the high-throughput scenario while proposed ran multiple anomaly scenarios before high throughput.
- It does not prove long-term production stability, because the run duration was short and executed on a local Docker environment.
- It does not measure real hardware STM32 behavior unless the simulator is explicitly presented as a synthetic workload generator.

## Methodology Caveats

The database contained previous data during this run. Therefore, database-backed 24-hour event counts and total table counts should be treated as contaminated exploratory evidence.

For final thesis tables, prefer these sources from this run:

- simulator terminal output
- in-memory gateway counters from `results/baseline/report.md`
- in-memory gateway counters from `results/proposed/report.md`

Avoid using these as final isolated measurements:

- `events-by-severity` 24-hour database counts
- total database row counts
- database size growth

## Recommended Next Experiments

### 1. Reset Database Before Final Runs

Use a clean database before collecting final thesis evidence:

```bash
docker compose down -v
just baseline
just proposed
```

This removes old TimescaleDB volume data and prevents previous runs from contaminating event counts, row counts, and storage measurements.

### 2. Add A/B High-Throughput Runs

Run the exact same high-throughput workload in both modes.

Suggested final design:

| Run | Mode | Scenario | Duration | Purpose |
| --- | --- | --- | ---: | --- |
| A1 | baseline | high throughput | 120s | baseline latency and throughput |
| A2 | proposed | high throughput | 120s | proposed overhead under same load |
| A3 | baseline | high throughput | 120s | repeatability |
| A4 | proposed | high throughput | 120s | repeatability |
| A5 | baseline | high throughput | 120s | repeatability |
| A6 | proposed | high throughput | 120s | repeatability |

Use averages across repeated runs in the final thesis table.

### 3. Keep Anomaly Detection Separate

Treat anomaly scenarios as functionality and detection experiments, not as direct baseline/proposed throughput comparisons.

Suggested final design:

| Scenario | Expected Evidence |
| --- | --- |
| undervoltage | under-voltage or voltage anomaly event generation |
| overload | critical overload events |
| power spike | warning power-spike events |
| invalid payloads | validation failure count |
| missing heartbeat/status gap | device-failure events |

### 4. Storage Reduction Strategy Decision

Decision: storage reduction will not be treated as a current measured thesis result.

Reason:

- Both baseline and proposed runs currently use `STORE_RAW_READINGS=true`.
- A valid storage-reduction claim would require a separate implementation and controlled experiment.
- The current thesis should focus on low-latency event detection, throughput stability, validation behavior, dashboards, and future extensibility.

Future-work framing:

- Selective raw-reading retention could store only event-triggering readings.
- Downsampling could preserve long-term trends while reducing raw-table growth.
- Event-first retention could keep events permanently while pruning normal telemetry.
- A future experiment should measure database size before and after identical workloads.

### 5. Collect Dashboard Evidence

Capture screenshots after a clean proposed run:

- Grafana energy overview
- event timeline
- system observability dashboard
- device detail page

Use these screenshots in Chapter 6 to show operational visibility, not just numeric counters.

## Suggested Chapter 6 Framing

Use this structure:

1. Performance overhead: compare baseline and proposed high-throughput latency.
2. Throughput stability: show both modes sustaining approximately 200 messages per second.
3. Event detection: show proposed-mode event counts by event type and severity.
4. Validation behavior: show invalid payloads being rejected and counted.
5. Observability: show Grafana dashboards and exported metrics.
6. Limitations: mention synthetic workloads, local Docker environment, short duration, and database contamination in exploratory runs.

## Draft Result Statement

The proposed event-driven gateway sustained the high-throughput simulator workload at approximately 199.54 messages per second, comparable to the baseline rate of 199.47 messages per second. The additional rule engine and event-processing logic increased average telemetry latency from 4.04 ms to 4.50 ms and p99 latency from 5.38 ms to 6.46 ms. Despite this small overhead, the proposed mode produced critical, warning, and informational events across overload, power-spike, voltage-anomaly, and device-failure scenarios. These results indicate that rule-based edge processing can add actionable event intelligence while preserving low-latency ingestion behavior.

This statement should be revised after final clean database runs.
