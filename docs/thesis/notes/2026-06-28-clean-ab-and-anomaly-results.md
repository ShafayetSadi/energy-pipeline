# 2026-06-28 Clean A/B and Anomaly Detection Results

## Purpose

This note records the latest thesis evaluation evidence collected after adding
clean high-throughput A/B runs and a separate proposed-mode anomaly detection
experiment.

These results are stronger than the earlier exploratory run notes because the
high-throughput A/B script resets the Docker volumes between runs. That makes
the baseline and proposed measurements more suitable for Chapter 5 and Chapter
6 tables.

The results support the current thesis claim:

> An edge-first, event-driven gateway can add validation, rule-based event
> detection, and observability to an IoT smart energy monitoring pipeline while
> preserving low-latency ingestion behavior.

## Commands Executed

Automated tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest gateway/tests/scripts/test_scripts.py -q
UV_CACHE_DIR=/tmp/uv-cache uv run pytest gateway/tests -q
```

Benchmark and detection experiments:

```bash
REPETITIONS=3 just ab-high-throughput
just anomaly-detection
```

## Test Status

The local automated test suite passed:

| Test command | Result |
| --- | ---: |
| `gateway/tests/scripts/test_scripts.py` | 2 passed |
| `gateway/tests` | 45 passed |

This validates the script smoke tests and the current gateway test coverage
before interpreting the benchmark results.

## Experiment 1: Clean High-Throughput A/B Test

### Method

The A/B test compared the same high-throughput simulator workload in two modes:

| Mode | Meaning |
| --- | --- |
| Baseline | Raw ingestion path without the proposed event-driven processing behavior |
| Proposed | Event-driven gateway path with rule processing, event generation, aggregation, and alert-related behavior enabled |

Scenario:

- Scenario file: `high_throughput.yaml`
- Simulated devices: 200
- Device interval: 1.0 second
- Duration: approximately 120 seconds per run
- Repetitions: 3 baseline runs and 3 proposed runs
- Output folder: `results/ab/high_throughput/`

The script reset the stack and database volumes between runs. This makes the
database-size and counter evidence cleaner than earlier exploratory runs.

### Simulator Output

The simulator completed every run with zero publishing failures.

| Mode | Run | Total sent | Failed | Simulator rate |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 1 | 23,940 | 0 | 199.48 msg/s |
| Baseline | 2 | 23,960 | 0 | 199.64 msg/s |
| Baseline | 3 | 23,968 | 0 | 199.71 msg/s |
| Proposed | 1 | 23,936 | 0 | 199.44 msg/s |
| Proposed | 2 | 23,952 | 0 | 199.57 msg/s |
| Proposed | 3 | 23,976 | 0 | 199.78 msg/s |

Average simulator rate:

| Mode | Average rate |
| --- | ---: |
| Baseline | 199.61 msg/s |
| Proposed | 199.60 msg/s |

Interpretation:

- The proposed gateway did not reduce simulator-side throughput.
- Both modes sustained approximately 200 messages per second.
- The workload was stable enough to support a fair latency and event-processing comparison.

### Gateway Counter Averages

Average values across the three exported gateway snapshots:

| Metric | Baseline average | Proposed average | Observation |
| --- | ---: | ---: | --- |
| Uptime | 122.24 s | 122.25 s | Comparable run length |
| `messages.received` | 24,731.67 | 24,744.33 | Comparable input volume |
| `messages.telemetry` | 23,501.33 | 23,472.67 | Comparable valid telemetry volume |
| `readings.stored` | 23,501.33 | 23,472.33 | Near-complete storage parity |
| `validation.failures` | 454.67 | 478.00 | Invalid payload handling remained active |
| `events.critical` | 136.67 | 3,980.67 | Proposed mode generated critical events |
| `events.warning` | 0.00 | 5,948.00 | Proposed mode generated warning events |

Important caveat:

- In proposed run 2, `messages.telemetry` was `23,479` while
  `readings.stored` was `23,478`.
- This is a one-reading mismatch in one run.
- Do not claim perfect storage parity across every run. Use wording such as
  "near-complete storage parity" or "only one stored-reading mismatch was
  observed across repeated proposed high-throughput runs."

### Latency Averages

Average telemetry latency across three runs:

| Metric | Baseline | Proposed | Difference |
| --- | ---: | ---: | ---: |
| Avg | 4.11 ms | 4.43 ms | +0.32 ms |
| p50 | 4.02 ms | 4.33 ms | +0.30 ms |
| p95 | 4.97 ms | 5.56 ms | +0.59 ms |
| p99 | 5.52 ms | 6.29 ms | +0.77 ms |

Average status-message latency:

| Metric | Baseline | Proposed | Difference |
| --- | ---: | ---: | ---: |
| Avg | 3.84 ms | 3.87 ms | +0.03 ms |
| p99 | 5.31 ms | 5.19 ms | -0.12 ms |

Interpretation:

- The proposed gateway adds measurable but small telemetry-processing overhead.
- The p99 telemetry latency remained below 7 ms in the repeated
  high-throughput A/B runs.
- The latency cost is reasonable for the added event-processing behavior.

### Database Size

The database-size measurements are now cleaner because the A/B script resets
volumes between runs.

| Mode | Avg size before | Avg size after | Avg growth |
| --- | ---: | ---: | ---: |
| Baseline | ~9.94 MB | ~21.84 MB | ~11.89 MB |
| Proposed | ~9.96 MB | ~25.90 MB | ~15.94 MB |

Interpretation:

- Proposed mode used more database space in the high-throughput experiment.
- This is expected because proposed mode stores extra event and operational
  evidence.
- These results do not support a storage-reduction claim.
- Storage reduction should remain future work unless a separate selective
  retention, downsampling, or event-only storage experiment is implemented.

## Experiment 2: Proposed-Mode Anomaly Detection

### Method

The anomaly detection experiment ran proposed mode only. It was designed to
show rule-based event detection and validation behavior, not to compare
baseline and proposed throughput.

Output folder:

```text
results/anomaly_detection/proposed/
```

Scenarios:

- `undervoltage_test`
- `overload_test`
- `power_spike_test`
- `invalid_payloads`

### Simulator Output

All anomaly scenarios completed with zero simulator-side publishing failures.

| Scenario | Total sent | Failed | Rate |
| --- | ---: | ---: | ---: |
| Undervoltage | 450 | 0 | 2.50 msg/s |
| Overload | 449 | 0 | 2.49 msg/s |
| Power spike | 480 | 0 | 2.00 msg/s |
| Invalid payloads | 478 | 0 | 3.98 msg/s |

### Gateway Counters

Key counters from `results/anomaly_detection/proposed/metrics-summary.json`:

| Metric | Value |
| --- | ---: |
| `messages.received` | 1,925 |
| `messages.telemetry` | 1,709 |
| `readings.stored` | 1,709 |
| `messages.status` | 68 |
| `validation.failures` | 148 |
| `events.critical` | 296 |
| `events.warning` | 475 |
| `events.info` | 31 |

Interpretation:

- All valid telemetry readings were stored in this anomaly run.
- Invalid payloads were rejected and counted through validation metrics.
- The proposed gateway generated critical, warning, and informational events.

### Event Detection Counts

Event counts from the anomaly experiment:

| Event type | Severity | Count |
| --- | --- | ---: |
| `OVERLOAD` | Critical | 284 |
| `DEVICE_FAILURE` | Critical | 12 |
| `POWER_SPIKE` | Warning | 430 |
| `UNDER_VOLTAGE` | Warning | 31 |
| `OVER_VOLTAGE` | Warning | 14 |
| `VOLTAGE_ANOMALY` | Info | 31 |

Severity totals:

| Severity | Count |
| --- | ---: |
| Critical | 296 |
| Warning | 475 |
| Info | 31 |

Validation errors:

| Error type | Count |
| --- | ---: |
| `invalid_json` | 148 |

Interpretation:

- The rule engine detected multiple abnormal electrical conditions.
- The event classification model is functioning at critical, warning, and info levels.
- Invalid JSON handling is measurable and can be discussed under data-quality behavior.

### Anomaly Run Latency

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Telemetry | 1,709 | 6.62 ms | 6.56 ms | 7.98 ms | 8.78 ms |
| Status | 68 | 5.30 ms | 5.24 ms | 6.17 ms | 6.29 ms |

Interpretation:

- Even during anomaly scenarios, telemetry latency stayed below 9 ms at p99.
- This supports the claim that rule-based detection can run at the edge with
  low processing latency.

## Thesis Claims Supported by These Results

The latest tests support these claims:

1. The system can ingest MQTT telemetry at approximately 200 messages per
   second in both baseline and proposed modes.
2. The proposed event-driven gateway adds only a small latency overhead under
   the high-throughput workload.
3. The proposed mode detects overload, power spike, under-voltage,
   over-voltage, voltage anomaly, and device-failure conditions.
4. The gateway validates malformed payloads and exposes validation failures as
   measurable quality metrics.
5. The architecture is observable: latency, throughput, validation failures,
   event counts, and database-size evidence can be exported for thesis tables.
6. The system is reproducible enough for local evaluation because the scripts
   reset and rerun the Docker-based stack.

## Claims Not Supported Yet

Do not claim the following based on these tests:

1. Storage reduction.
   - Proposed mode currently stores more data because it writes event evidence.
   - Storage optimization remains future work.
2. AI/ML anomaly detection.
   - Current anomaly detection is rule-based.
   - ML integration remains a future extension point.
3. Real-world hardware performance.
   - These runs use synthetic simulator workloads.
   - STM32/ESP hardware evidence should be collected separately if needed.
4. Long-term production stability.
   - These are short local Docker experiments.
   - They do not prove multi-day uptime or field reliability.
5. Electrical metering accuracy certification.
   - The experiment validates the software pipeline, not certified metering accuracy.

## Suggested Chapter 5 Methodology Text

The evaluation used two experiment groups. First, a clean high-throughput A/B
test compared a baseline raw-ingestion gateway against the proposed
event-driven gateway using the same 200-device MQTT simulator workload. The
experiment was repeated three times in each mode, and the stack was reset
between runs to avoid database contamination. Second, proposed-mode anomaly
scenarios were executed to verify rule-based detection of abnormal energy
conditions and validation behavior for invalid payloads.

Metrics were collected from simulator logs, exported gateway counters, latency
summaries, event tables, validation-error summaries, and database-size
snapshots.

## Suggested Chapter 6 Result Statement

The proposed event-driven edge gateway sustained approximately 199.6 messages
per second, matching the baseline raw-ingestion mode under the same
high-throughput workload. Enabling rule-based event detection increased average
telemetry latency from about 4.11 ms to 4.43 ms and p99 latency from about
5.52 ms to 6.29 ms. This small overhead enabled detection of critical and
warning events, including overload, power spike, voltage anomaly,
under-voltage, over-voltage, and device failure conditions. The results show
that rule-based edge intelligence can be added to a smart energy monitoring
pipeline while preserving low-latency ingestion behavior.

## Recommended Tables for Thesis Draft

Use these tables in Chapter 6:

1. High-throughput simulator rate by mode.
2. Baseline vs proposed telemetry latency.
3. Baseline vs proposed event counts.
4. Proposed anomaly event counts by type and severity.
5. Validation errors from invalid payload scenarios.
6. Database-size growth as an observability/storage-cost discussion, not as a
   storage-reduction result.

## Recommended Figures or Screenshots

Collect these after a clean proposed run:

1. Grafana energy overview dashboard.
2. Event timeline panel.
3. System latency or throughput panel.
4. Device health/status panel.
5. Optional screenshot of the exported report folder structure.

## Final Position

The project is thesis-evaluation ready for the current scope:

- MQTT ingestion works.
- Edge validation works.
- Rule-based event detection works.
- Time-series storage works.
- Metrics export works.
- Repeated A/B evaluation works.
- Proposed mode adds useful event intelligence with low millisecond-level overhead.

The remaining thesis work should focus on writing the methodology/results
chapters, adding dashboard screenshots, and clearly separating current
rule-based detection from future AI/ML anomaly detection.
