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

## 6.7 Edge ML Anomaly Detection Results (Phase 1)

This section reports the offline detection quality of the edge Isolation Forest
detector. These results were produced by
`scripts/train_anomaly_model.py --evaluate` (seed 42, 50,000 normal training
samples, a held-out test set of 10,000 normal and 2,000 injected anomalies)
and written to `results/anomaly_model/offline_evaluation.json`.

At the shipped operating point (detection threshold = 0.90 quantile of the
normal-data anomaly scores):

| Metric | Value |
| --- | ---: |
| Precision | 0.612 |
| Recall | 0.780 |
| F1 | 0.686 |
| False-positive rate | 0.099 |
| Confusion (tn / fp / fn / tp) | 9010 / 990 / 439 / 1561 |

Recall varied by anomaly type:

| Anomaly type | Count | Recall |
| --- | ---: | ---: |
| `overvoltage` | 499 | 0.992 |
| `power_spike` | 502 | 0.861 |
| `undervoltage` | 492 | 0.831 |
| `overload` | 507 | 0.444 |

The detection threshold is a tunable operating point. Lowering it raises recall
at the cost of more false positives:

| Threshold quantile | Threshold | FPR | Recall |
| ---: | ---: | ---: | ---: |
| 0.90 | 0.545 | 0.099 | 0.780 |
| 0.95 | 0.573 | 0.052 | 0.387 |
| 0.975 | 0.602 | 0.025 | 0.242 |
| 0.99 | 0.634 | 0.011 | 0.188 |

The interpretation is twofold. First, the unsupervised detector reliably flags
anomalies that leave the normal operating envelope — over-voltage (0.99),
power spikes (0.86), and under-voltage (0.83) — without using any labels.
Second, `overload` recall is low (0.44), and this is an expected and useful
finding rather than a failure: the simulator's normal evening load already
drives current well above the rule's 10 A overload threshold, so a rule-based
overload alarm fires on normal high-load operation, whereas a detector trained
on the actual operating distribution correctly treats those readings as normal.
This directly informs the rules-versus-ML discussion: rules are decisive for
hard bound violations, while the model adds value for envelope and
consistency anomalies and avoids the over-sensitivity of a fixed current
threshold.

### 6.7.1 Online detection A/B (operational cost)

The online A/B (`scripts/run_detection_ab_test.sh`) ran the same labeled
anomaly scenarios (undervoltage, overload, power_spike) in three live gateway
configurations. It measures the *operational cost* of ML scoring, separate from
the offline detection-quality result above. The three modes processed a
comparable input volume (1,376–1,379 telemetry messages); small differences and
the per-mode event counts reflect the random component of the scenarios and so
should be read as indicative rather than exact like-for-like.

**Processing latency.** This was the headline operational finding of the first
run, in which scoring was performed *inline* (synchronously, one reading at a
time) in the ingestion path:

| Mode (inline scoring) | Telemetry avg | Telemetry p99 | ML inference avg | ML inference p99 |
| --- | ---: | ---: | ---: | ---: |
| rules | 6.72 ms | 9.71 ms | – | – |
| ml | 19.30 ms | 24.98 ms | 11.85 ms | 16.28 ms |
| hybrid | 19.63 ms | 24.83 ms | 11.90 ms | 16.50 ms |

Inline ML scoring added roughly +12.6 ms average and +15 ms p99 to telemetry
processing, dominated by the per-sample `ml_inference` cost (~11.9 ms average).
This is much larger than the sub-millisecond overhead of rule evaluation and is
an artifact of calling scikit-learn's `score_samples` on one sample at a time:
scikit-learn is optimised for batched inference, so per-message Python/NumPy
call overhead dominates (profiling measured ~10 ms per single sample versus
~0.014 ms per row when scoring a batch). Even so, p99 telemetry latency stayed
under 25 ms at the tested throughput.

In response, scoring was moved into an asynchronous micro-batch worker
(Section 4.9, `ML_ASYNC_SCORING`, now the default): the telemetry handler
enqueues each reading and returns immediately, and the worker scores readings
in batches off the hot path. Re-running the A/B with asynchronous scoring
enabled gives the "after" measurement:

| Mode (async scoring) | Telemetry avg | Telemetry p99 | ML inference avg / p99 | Queue delay avg / p99 |
| --- | ---: | ---: | ---: | ---: |
| rules | 6.72 ms | 9.61 ms | – | – |
| ml | 6.35 ms | 10.35 ms | 10.42 / 15.63 ms | 48.75 / 54.97 ms |
| hybrid | 6.65 ms | 9.96 ms | 10.41 / 13.82 ms | 49.02 / 54.87 ms |

Telemetry processing latency returned to the rule-only baseline (~6.4–6.7 ms
average in all three modes): ML scoring no longer adds measurable cost to the
ingestion hot path. The cost did not disappear — it moved. The new `ml_queue`
series measures the delay from enqueueing a reading to its score being
available, ~49 ms average, dominated by the worker's 50 ms batch-collection
window. An `ML_ANOMALY` event therefore trails its reading by roughly the
batch window plus inference, still far below any actionable alerting
timescale. Two honest caveats: first, at the tested throughput (~2.3 msg/s)
the worker collected an average batch of only ~1.1 readings
(1,256–1,268 batches for ~1,376 scored), so per-batch inference remains
~10 ms and the amortisation benefit of batching (~0.014 ms per row, Section
4.9) would only materialise at higher message rates — what this experiment
demonstrates is the decoupling, not the amortisation. Second, the two runs
were taken on the same host but at different times, so small cross-run
differences in absolute numbers reflect ordinary load variance; the
within-run comparison against the rules mode is the controlled one.

**Detection output.** Counts of generated events and ML scores by mode (from
the async-scoring run, which is the evidence retained under
`results/detection_ab/`):

| Signal | rules | ml | hybrid |
| --- | ---: | ---: | ---: |
| Rule events (OVERLOAD/POWER_SPIKE/…) | 587 | 0 | 526 |
| `ML_ANOMALY` events | 0 | 6 | 5 |
| `model_predictions` rows | 0 | 1,379 | 1,376 |
| Readings scored anomalous (`ml.anomalies`) | – | 93 | 88 |

Two points stand out. First, the ml-only mode flagged 93 readings as anomalous
but emitted only 6 `ML_ANOMALY` events: the per-device cooldown collapses a
burst of anomalous readings during an anomaly window into a single event, which
is the intended behaviour for alert hygiene. Second, the hybrid mode produces
the union — the full set of rule events plus a small number of ML events — so a
deployment can keep decisive rule alarms for hard bound violations while the
model adds coverage. The detection *quality* of these flags (precision/recall)
is established offline in Section 6.7, because the live pipeline does not carry
per-reading ground-truth labels.

**Storage.** Database growth over each run:

| Mode | Before | After | Growth |
| --- | ---: | ---: | ---: |
| rules | 10.01 MB | 11.91 MB | 1.90 MB |
| ml | 10.01 MB | 12.11 MB | 2.11 MB |
| hybrid | 10.01 MB | 12.55 MB | 2.55 MB |

Hybrid stored the most because it writes rule events, a `model_prediction` row
for every reading, and ML events. As in Section 6.8, this confirms that added
intelligence has an observable storage cost; it is not a storage-reduction
result. Persisting a prediction per reading is the main ML storage contributor
and is a candidate for the selective-retention work in a later phase.

### 6.7.2 Escalation bandwidth A/B (Phase 2)

Phase 2 adds the score-gated edge-to-cloud escalation path (Sections 3.9 and
4.10): scored readings whose anomaly score crosses the escalation threshold
are batched and forwarded to a minimal cloud-tier receiver, and both sides
count forwarded readings and payload bytes. The evaluation compares `gated`
forwarding against the naive `all`-to-cloud baseline under the identical
pipeline (Section 5.6), so the gate is the only variable.

The path is implemented and verified end to end (a functional test confirmed
that flagged readings arrive at the cloud tier with matching byte counts on
the sending and receiving side, while normal readings are not forwarded), but
the bandwidth A/B has not yet been run; its measured reduction will be
reported here. The expected outcome follows from the gate by construction —
gated volume tracks the model's flag rate (roughly 7% of readings in the
detection A/B scenarios) rather than the full stream — but consistent with the
measurement-only policy of this thesis, no reduction percentage is claimed
until measured.

## 6.8 Database Size Discussion

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

## 6.9 Discussion Against Research Questions

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

The fourth research question asks how ready the platform is for AI/ML
extension. Phase 1 answers this concretely: an edge Isolation Forest detector
is implemented, trained offline, and evaluated (Section 6.7), scoring every
reading into `model_predictions` and optionally raising `ML_ANOMALY` events
through the same path as rules. The platform is therefore no longer only
ML-ready in principle; it runs a working edge ML detector, with the cloud tier,
score-gated escalation, and storage optimization staged as later phases.

## 6.10 Limitations

The results should be interpreted within the scope of the experiment.

First, the workload was generated by a simulator. The results are valid for
the implemented software pipeline, but real hardware tests are still needed to
evaluate sensor behavior, firmware timing, Wi-Fi reliability, and physical
measurement accuracy.

Second, the experiments were short local Docker runs. They do not prove
long-term production reliability, cloud deployment readiness, or large-scale
field performance.

Third, the machine-learning detection-quality result in Section 6.7 is an
offline measurement on simulator-faithful synthetic data, not a field result;
the online A/B in Section 6.7.1 measures only operational cost, not live
precision/recall. The online A/B also showed that per-sample ML inference adds
substantial latency (~12 ms) in the current naive implementation — an
optimization target (batched or offloaded scoring) rather than a fundamental
limit. The detector is a single global Isolation Forest. Per-device models,
adaptive thresholds, forecasting, predictive maintenance, and the cloud tier
remain future work.

Fourth, storage reduction was not achieved or measured as a successful result.
The proposed mode increased database growth because it stored additional event
evidence. Storage optimization remains a separate future experiment.

Finally, the system is not a certified metering platform. It demonstrates an
event-driven monitoring architecture and software pipeline, not certified
commercial billing accuracy.

## 6.11 Chapter Conclusion

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
