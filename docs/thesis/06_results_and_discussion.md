# Chapter 6: Results and Discussion

## 6.1 Summary of Results

The experimental results support the main thesis claim that the proposed
gateway adds event intelligence with only a small latency overhead. In the
clean high-throughput A/B test, the proposed gateway sustained almost the same
simulator throughput as the baseline. At the same time, proposed mode produced
critical and warning events through rule-based edge processing.

The most important result is that the proposed event-driven edge gateway
preserved low-millisecond telemetry processing latency while adding validation,
rule evaluation, event generation, storage, and dashboard observability.

## 6.2 Throughput Results

The high-throughput experiment used 200 simulated devices publishing at a
1-second interval for approximately 120 seconds per run. The experiment was
repeated three times in each mode.

| Mode | Run 1 | Run 2 | Run 3 | Average |
| --- | ---: | ---: | ---: | ---: |
| Baseline simulator rate | 199.48 msg/s | 199.64 msg/s | 199.71 msg/s | 199.61 msg/s |
| Proposed simulator rate | 199.44 msg/s | 199.57 msg/s | 199.78 msg/s | 199.60 msg/s |

The simulator completed every run with zero publish failures. The average
rate was nearly identical between modes: 199.61 messages per second for the
baseline and 199.60 messages per second for the proposed gateway. This shows
that the proposed rule-processing behavior did not reduce simulator-side
throughput under the tested workload.

Gateway counters also showed comparable input volume:

| Metric | Baseline average | Proposed average | Observation |
| --- | ---: | ---: | --- |
| Uptime | 122.24 s | 122.25 s | Comparable run length |
| `messages.received` | 24,731.67 | 24,744.33 | Comparable input volume |
| `messages.telemetry` | 23,501.33 | 23,472.67 | Comparable valid telemetry volume |
| `readings.stored` | 23,501.33 | 23,472.33 | Near-complete storage parity |

One caveat is that proposed run 2 had a single-reading mismatch:
`messages.telemetry` was 23,479 while `readings.stored` was 23,478. For this
reason, the result should be described as near-complete storage parity rather
than perfect storage parity across all runs.

## 6.3 Latency Results

Telemetry latency remained low in both modes. The proposed mode introduced a
small but measurable overhead because it performed additional rule-based
processing and event generation.

| Metric | Baseline | Proposed | Difference |
| --- | ---: | ---: | ---: |
| Avg telemetry latency | 4.11 ms | 4.43 ms | +0.32 ms |
| p50 telemetry latency | 4.02 ms | 4.33 ms | +0.30 ms |
| p95 telemetry latency | 4.97 ms | 5.56 ms | +0.59 ms |
| p99 telemetry latency | 5.52 ms | 6.29 ms | +0.77 ms |

The p99 telemetry latency stayed below 7 ms in the repeated high-throughput
A/B runs. This is important because p99 latency reflects slower cases better
than the average. The measured difference indicates that rule evaluation and
event processing added less than 1 ms at p99 in this experiment.

Status-message latency was also similar between modes:

| Metric | Baseline | Proposed | Difference |
| --- | ---: | ---: | ---: |
| Avg status latency | 3.84 ms | 3.87 ms | +0.03 ms |
| p99 status latency | 5.31 ms | 5.19 ms | -0.12 ms |

The latency results support the conclusion that the proposed gateway can add
edge intelligence while preserving low-latency ingestion behavior.

## 6.4 Event Detection Results

The proposed gateway generated event records during both the high-throughput
A/B test and the separate anomaly detection experiment. In the high-throughput
A/B test, proposed mode produced many more events than baseline mode because
rule-based processing was active.

| Metric | Baseline average | Proposed average |
| --- | ---: | ---: |
| `events.critical` | 136.67 | 3,980.67 |
| `events.warning` | 0.00 | 5,948.00 |

The separate anomaly detection experiment provides clearer functional evidence
for specific rule types. Proposed mode detected overload, power spike,
under-voltage, over-voltage, voltage anomaly, and device failure events.

| Event type | Severity | Observed count |
| --- | --- | ---: |
| `OVERLOAD` | Critical | 284 |
| `DEVICE_FAILURE` | Critical | 12 |
| `POWER_SPIKE` | Warning | 430 |
| `UNDER_VOLTAGE` | Warning | 31 |
| `OVER_VOLTAGE` | Warning | 14 |
| `VOLTAGE_ANOMALY` | Info | 31 |

Severity totals from the anomaly experiment were:

| Severity | Count |
| --- | ---: |
| Critical | 296 |
| Warning | 475 |
| Info | 31 |

These results show that the event-driven gateway can classify abnormal
conditions into severity levels. This directly supports the research question
about whether rule-based processing can detect abnormal energy events while
maintaining low processing latency.

The anomaly experiment also reported telemetry latency:

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Telemetry | 1,709 | 6.62 ms | 6.56 ms | 7.98 ms | 8.78 ms |
| Status | 68 | 5.30 ms | 5.24 ms | 6.17 ms | 6.29 ms |

Even during anomaly scenarios, telemetry p99 latency stayed below 9 ms.

## 6.5 Validation and Data Quality Results

Validation behavior was visible in both the high-throughput A/B test and the
anomaly experiment. The gateway rejected malformed payloads and exposed
validation failures as measurable counters and data-quality logs.

Average validation failures in the high-throughput A/B test:

| Mode | Average validation failures |
| --- | ---: |
| Baseline | 454.67 |
| Proposed | 478.00 |

In the proposed anomaly detection experiment, invalid payload handling was
measured directly:

| Error type | Count |
| --- | ---: |
| `invalid_json` | 148 |

The anomaly run stored all valid telemetry readings:

| Metric | Value |
| --- | ---: |
| `messages.telemetry` | 1,709 |
| `readings.stored` | 1,709 |

These results show that the gateway does not silently accept malformed data.
Instead, it rejects invalid payloads, records the failure type, and exposes the
behavior through reports and dashboards. This is important for a monitoring
system because data quality problems must be visible to operators and
researchers.

## 6.6 Dashboard and Observability Results

Grafana dashboards were used to inspect readings, event timelines, device
details, system metrics, and thesis evaluation summaries. The dashboard layer
does not create the underlying measurements; it makes the gateway behavior
visible.

The following dashboard screenshots should be included in the final formatted
thesis after capturing them from the clean proposed run:

| Figure | Dashboard | Purpose |
| --- | --- | --- |
| Figure 6.1 | Energy Overview | Shows system-level readings, load, voltage, and event counts |
| Figure 6.2 | Device Detail | Shows per-device measurements with thresholds and event context |
| Figure 6.3 | Event Timeline | Shows rule-generated event records and severity classification |
| Figure 6.4 | System Observability | Shows gateway message rate, validation rate, and latency metrics |
| Figure 6.5 | Thesis Evaluation | Shows the A/B and anomaly evidence summary used in this chapter |

The implemented dashboards support the following views:

| Dashboard | Purpose |
| --- | --- |
| Energy Overview | Shows devices seen, stored readings, latest load, average voltage, events, and latest readings |
| Device Detail | Shows per-device status, freshness, latest values, time-series readings, thresholds, events, and status history |
| Event Timeline | Shows recent events, event counts by type and severity, affected devices, and unacknowledged events |
| System Observability | Shows message rate, stored-reading rate, validation-failure rate, latency percentiles, and alert outbox state |
| Thesis Evaluation | Summarizes the A/B result, anomaly detection evidence, database-size observation, and interpretation boundaries |

This supports the thesis contribution because the system is not only storing
readings; it also exposes operational evidence for evaluation and monitoring.
The dashboards help demonstrate event-driven observability, which is part of
the proposed architecture.

## 6.7 Database Size Discussion

Database size was measured before and after the clean high-throughput A/B
runs. The measurements are useful as a storage-cost observation, but they do
not prove storage optimization.

| Mode | Avg size before | Avg size after | Avg growth |
| --- | ---: | ---: | ---: |
| Baseline | ~9.94 MB | ~21.84 MB | ~11.89 MB |
| Proposed | ~9.96 MB | ~25.90 MB | ~15.94 MB |

The proposed mode used more database space. This is expected because proposed
mode stores additional event and operational evidence. Therefore, this thesis
should not claim storage reduction. A fair storage-reduction claim would
require a separate implementation and experiment using selective raw-data
retention, downsampling, or event-only long-term storage.

The correct interpretation is that proposed mode has an observable storage
cost in exchange for additional event intelligence and monitoring evidence.

## 6.8 Discussion Against Research Questions

The first research question asks how an event-driven edge gateway can improve
smart energy monitoring pipelines. The results show that the gateway improves
the pipeline by adding validation, rule-based detection, event classification,
and dashboard visibility before data is treated only as stored telemetry.

The second research question asks how the proposed architecture compares with
a baseline telemetry-storage approach. The high-throughput A/B results show
that proposed mode preserved approximately the same simulator throughput as
baseline mode while adding event records. The latency overhead was small:
average telemetry latency increased by 0.32 ms and p99 latency increased by
0.77 ms.

The third research question asks whether rule-based processing can detect
abnormal energy events while maintaining low latency. The anomaly detection
experiment confirms that overload, power spike, voltage, and device-failure
events were detected, while telemetry p99 latency remained below 9 ms in the
anomaly run.

The fourth research question asks how ready the platform is for future AI/ML
extension. The current system is ready at the architecture level because it
stores time-series readings, events, validation logs, and metrics that could
later be used for model training or evaluation. However, the current results
do not include an implemented ML anomaly detector.

## 6.9 Limitations

The results should be interpreted within the scope of the experiment.

First, the workload was generated by a simulator. The results are valid for
the implemented software pipeline, but real hardware tests are still needed to
evaluate sensor behavior, firmware timing, Wi-Fi reliability, and physical
measurement accuracy.

Second, the experiments were short local Docker runs. They do not prove
long-term production reliability, cloud deployment readiness, or large-scale
field performance.

Third, the anomaly detection logic is rule-based. The current thesis should
not describe the system as an ML anomaly detection system. Machine learning,
adaptive thresholds, forecasting, and predictive maintenance should be framed
as future work.

Fourth, storage reduction was not achieved or measured as a successful result.
The proposed mode increased database growth because it stored additional event
evidence. Storage optimization remains a separate future experiment.

Finally, the system is not a certified metering platform. It demonstrates an
event-driven monitoring architecture and software pipeline, not certified
commercial billing accuracy.

## 6.10 Chapter Conclusion

The results show that the proposed event-driven gateway adds useful event
intelligence with only a small latency overhead. Under the repeated
high-throughput workload, the proposed system sustained approximately the same
simulator message rate as the baseline. It increased average telemetry latency
from 4.11 ms to 4.43 ms and p99 telemetry latency from 5.52 ms to 6.29 ms.
In return, the proposed system generated critical and warning events and
provided observability through reports and Grafana dashboards.

The defensible conclusion is that rule-based edge processing can improve an
IoT smart energy monitoring pipeline by adding timely abnormal-event detection
and operational visibility while preserving low-latency ingestion behavior.
