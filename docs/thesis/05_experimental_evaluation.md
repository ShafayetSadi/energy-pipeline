# Chapter 5: Experimental Evaluation

## 5.1 Experimental Setup

This chapter evaluates the implemented smart energy monitoring pipeline using a
local reproducible test environment. The evaluated system consists of an MQTT
broker, a FastAPI edge gateway, PostgreSQL/TimescaleDB storage, Grafana
dashboards, and a synthetic MQTT device simulator.

The evaluation focuses on the software pipeline and gateway behavior. The
simulator represents multiple energy monitoring devices that publish voltage,
current, power, temperature, status, and invalid-payload test messages through
MQTT. The experiment therefore measures gateway ingestion, validation,
rule-based event detection, database persistence, and observability behavior.
It does not claim certified electrical metering accuracy or large-scale field
hardware validation.

The stack was executed through Docker Compose. The gateway consumed MQTT
messages from Mosquitto, validated incoming payloads, stored accepted telemetry
in TimescaleDB, and exported metrics and reports for comparison. Grafana was
used to verify dashboard visibility for readings, events, and system metrics.

Before interpreting the benchmark results, the automated test suite was run:

| Test command | Result |
| --- | ---: |
| `UV_CACHE_DIR=/tmp/uv-cache uv run pytest gateway/tests/scripts/test_scripts.py -q` | 2 passed |
| `UV_CACHE_DIR=/tmp/uv-cache uv run pytest gateway/tests -q` | 45 passed |

These tests verified the script smoke tests and the current gateway behavior
covered by the repository test suite.

## 5.2 Baseline and Proposed System Definition

The evaluation compares two gateway modes: a baseline raw-ingestion mode and a
proposed event-driven edge-processing mode.

The baseline mode represents a simpler telemetry pipeline. In this mode, valid
MQTT telemetry is validated and stored, but the proposed event-driven rule
processing behavior is not used as the main contribution. This provides a
reference point for measuring ingestion throughput and latency when the gateway
acts mainly as a storage path for valid readings.

The proposed mode represents the thesis architecture. In this mode, the
gateway performs validation, applies rule-based detection, classifies events,
stores telemetry and event records, and exposes operational metrics for
dashboards and thesis evaluation. This mode is intended to show whether an
edge gateway can add useful event intelligence without introducing excessive
processing latency.

The defensible thesis claim is:

> This project designs and implements an event-driven edge gateway for
> IoT-based smart energy monitoring using MQTT, rule-based event detection,
> TimescaleDB storage, and Grafana observability dashboards.

Building on this baseline, the work adds an edge machine-learning detector
(Phase 1, Section 5.5), so detection can be compared across rules-only,
ml-only, and hybrid configurations, and a score-gated edge-to-cloud escalation
path (Phase 2, Section 5.6), so gated forwarding can be compared against a
naive all-to-cloud baseline. The current work does not yet claim a cloud-side
model, storage reduction, production-grade field deployment, certified
metering accuracy, or large-scale smart-grid validation. These are treated as
later phases and future work.

## 5.3 High-Throughput A/B Test Method

The first experiment was a clean high-throughput A/B comparison. The same
simulated workload was run in baseline and proposed modes. The purpose was to
measure whether the proposed event-driven gateway introduces significant
throughput or latency overhead compared with the baseline ingestion path.

The experiment was executed with:

```bash
REPETITIONS=3 just ab-high-throughput
```

The high-throughput scenario used:

| Parameter | Value |
| --- | ---: |
| Scenario | `high_throughput.yaml` |
| Simulated devices | 200 |
| Device interval | 1.0 second |
| Run duration | approximately 120 seconds |
| Repetitions | 3 baseline runs and 3 proposed runs |
| Output directory | `results/ab/high_throughput/` |

The A/B script reset the Docker stack and database volumes between runs. This
was important because it prevented previous data from contaminating the
counter, event, and database-size measurements.

For each run, the simulator log recorded total messages sent, publish
failures, and simulator-side message rate. The gateway exported a report and
raw snapshot containing counters and latency summaries.

## 5.4 Anomaly Detection Experiment Method

The second experiment evaluated proposed-mode rule-based event detection. This
experiment was not a baseline/proposed throughput comparison. Instead, it
tested whether the proposed gateway could detect abnormal electrical
conditions and validation failures under controlled synthetic scenarios.

The experiment was executed with:

```bash
just anomaly-detection
```

The anomaly detection experiment ran these proposed-mode scenarios:

| Scenario | Purpose |
| --- | --- |
| `undervoltage_test` | Verify under-voltage and voltage-anomaly event generation |
| `overload_test` | Verify critical overload detection |
| `power_spike_test` | Verify warning-level power-spike detection |
| `invalid_payloads` | Verify malformed payload rejection and validation metrics |

The output was written under:

```text
results/anomaly_detection/proposed/
```

This experiment collected event counts by type and severity, validation errors
by type, gateway counters, and latency summaries.

## 5.5 Edge ML Detection Evaluation Method (Phase 1)

The edge Isolation Forest detector is evaluated in two complementary ways: an
offline detection-quality measurement and an online operational A/B.

**Offline detection quality.** The model is trained and evaluated by
`scripts/train_anomaly_model.py --evaluate`. Training data mirrors the
simulator's telemetry distribution; a held-out labeled test set combines normal
readings with injected anomalies generated the way the simulator generates them
(overriding only the anomaly field). Because the labels are known by
construction, this yields genuine precision, recall, F1, false-positive rate,
per-anomaly-type recall, and an operating-point tradeoff table (detection
threshold versus recall/FPR). This separates *detection quality* from the live
pipeline and is fully reproducible from a fixed seed without a running stack.

**Online detection A/B.** The script `scripts/run_detection_ab_test.sh` runs
the same labeled anomaly scenarios in three gateway configurations:

| Mode | Configuration |
| --- | --- |
| rules | `ENABLE_RULE_ENGINE=true`, `ENABLE_ML=false` |
| ml | `ENABLE_RULE_ENGINE=false`, `ENABLE_ML=true`, `ML_EMIT_EVENTS=true` |
| hybrid | `ENABLE_RULE_ENGINE=true`, `ENABLE_ML=true`, `ML_EMIT_EVENTS=true` |

For each mode it captures detected events by type, prediction counts and score
statistics from `model_predictions`, telemetry and `ml_inference` latency, and
database growth, under:

```text
results/detection_ab/{rules,ml,hybrid}/
```

This measures the *operational cost* of adding ML scoring to the live pipeline,
complementing the offline detection-quality measurement.

## 5.6 Escalation Bandwidth A/B Method (Phase 2)

The score-gated edge-to-cloud escalation (Section 4.10) is evaluated by
`scripts/run_escalation_bandwidth_test.sh`, which runs the same labeled anomaly
scenarios in two gateway configurations that differ *only* in the escalation
gate:

| Mode | Configuration |
| --- | --- |
| gated | `CLOUD_FORWARD_MODE=gated` — forward only readings whose anomaly score crosses the escalation threshold |
| all | `CLOUD_FORWARD_MODE=all` — forward every scored reading (naive all-to-cloud baseline) |

Both modes run the full hybrid pipeline (rules + async ML scoring + event
emission) and the cloud-tier receiver, so the comparison isolates the gate.
For each mode the script captures the gateway's forwarding counters
(`cloud.forwarded`, `cloud.batches`, `cloud.bytes_sent`,
`cloud.forward_failed`, `cloud_forward` latency) and the cloud tier's
independent receive counters (readings, batches, bytes), then computes the
byte and reading reduction of gated relative to all-to-cloud in
`bandwidth-summary.json`, under:

```text
results/escalation_bandwidth/{gated,all}/
```

Counting payload bytes on both the sending and receiving side guards against
measurement error: the two totals must agree for a run to be valid. The
measured quantity is application-payload bytes (the JSON envelope), not
wire-level bytes including HTTP and TCP/IP overhead; because batching gives
both modes similar per-batch overhead, the payload-byte ratio is the honest
comparison statistic. The expected reduction follows from the gate: in gated
mode the forwarded volume tracks the model's flag rate (roughly 7% of readings
in the detection A/B scenarios) rather than the full telemetry stream.

## 5.7 Metrics Collected

The evaluation used both simulator-side and gateway-side metrics.

Simulator-side metrics:

- total MQTT messages sent
- failed publish attempts
- simulator message rate

Gateway-side metrics:

- `messages.received`
- `messages.telemetry`
- `readings.stored`
- `validation.failures`
- `events.critical`
- `events.warning`
- `events.info`
- event counts by type
- validation errors by type
- `ml.scored` and `ml.anomalies` counters (when ML is enabled)
- `model_predictions` counts and anomaly-score statistics
- telemetry, status, and `ml_inference` latency percentiles

Latency was reported using average, p50, p95, and p99 values. These values
were exported from the gateway metrics snapshot and summarized in generated
reports. The p95 and p99 values are especially useful because they show
whether the gateway remains responsive outside the average case.

Database size was also captured before and after high-throughput runs. In this
thesis, database size is treated as a storage-cost and observability
discussion, not as a storage-optimization result. Both modes store raw
readings, and the proposed mode also stores event evidence. Therefore, the
current experiment does not support a storage-reduction claim.

## 5.8 Data Collection Procedure

The high-throughput A/B test and anomaly detection experiment generated
machine-readable and human-readable artifacts.

The high-throughput A/B results were stored under:

```text
results/ab/high_throughput/
```

Each run directory contains:

- `simulator.log`
- `snapshot.json`
- `report.md`
- `db-size-before.txt`
- `db-size-after.txt`

The anomaly detection results were stored under:

```text
results/anomaly_detection/proposed/
```

This directory contains:

- per-scenario simulator logs
- `metrics-summary.json`
- `events-by-severity.txt`
- `events-by-type.txt`
- `validation-errors-by-type.txt`
- `report.md`
- database-size snapshots

The exported reports were used to build the result tables in Chapter 6.
Grafana dashboards were used as visual evidence that readings, events,
validation behavior, and system metrics can be inspected during and after the
experiments.

## 5.9 Experimental Limitations

The evaluation has several limitations.

First, the tests use synthetic simulator workloads. The results demonstrate
the gateway and data pipeline behavior, but they do not prove performance with
real STM32 or ESP-based hardware under field conditions.

Second, the experiments are short local Docker runs. They show repeatable
behavior under controlled test conditions, but they do not prove multi-day
production reliability or deployment readiness.

Third, the machine-learning detector is evaluated offline on simulator-faithful
synthetic data, and in the live pipeline only its operational cost is measured.
The offline precision/recall therefore reflects detection quality on controlled
data, not field accuracy. The detector is also a single global Isolation Forest;
per-device models (which the literature shows can perform better) and the cloud
tier with score-gated escalation remain future phases.

Fourth, storage reduction is not measured as a successful result. The proposed
mode writes additional event records, so database growth is expected. Selective
raw retention, downsampling, and event-only long-term storage remain future
work.

Finally, the system is not evaluated for certified electrical metering
accuracy, production security, or large-scale smart-grid deployment. The
evaluation is intentionally scoped to the event-driven edge gateway and its
observable software behavior.
