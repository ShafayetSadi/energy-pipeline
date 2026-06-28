# Chapter 7: Conclusion and Future Work

## 7.1 Summary

This thesis designed and implemented an event-driven edge gateway for
IoT-based smart energy monitoring. The system uses MQTT for communication,
FastAPI for the gateway service, PostgreSQL/TimescaleDB for time-series
storage, rule-based processing for abnormal-event detection, and Grafana for
observability dashboards.

The problem addressed by the thesis is that raw telemetry pipelines can store
measurements but provide limited local intelligence. In such systems,
abnormal conditions may only become visible after later analysis or dashboard
inspection. The proposed gateway improves this pipeline by validating
messages, detecting events at the edge, storing event evidence, and exposing
metrics for evaluation.

The evaluation compared a baseline ingestion path with the proposed
event-driven gateway. The clean high-throughput A/B test showed that both
modes sustained approximately 200 simulator messages per second. The proposed
mode increased average telemetry latency from 4.11 ms to 4.43 ms and p99
telemetry latency from 5.52 ms to 6.29 ms. This is a small overhead for the
added rule-based event processing.

The anomaly detection experiment showed that the proposed gateway detected
overload, power spike, under-voltage, over-voltage, voltage anomaly, and
device-failure events. It also rejected malformed payloads and recorded
validation failures. These results support the conclusion that rule-based edge
processing can add useful event intelligence while preserving low-latency
ingestion behavior.

## 7.2 Contributions

The project makes the following contributions:

1. It implements an MQTT-based smart energy monitoring pipeline with an edge
   gateway, time-series storage, and dashboards.
2. It defines a baseline versus proposed comparison for evaluating the cost of
   event-driven edge processing.
3. It implements validation and data-quality logging for malformed MQTT
   payloads.
4. It implements configurable rule-based event detection for overload, power
   spike, voltage, temperature, and device-failure conditions.
5. It stores readings, events, status history, validation logs, and system
   metrics in PostgreSQL/TimescaleDB.
6. It provides Grafana dashboards for energy overview, device detail, event
   timeline, system observability, and thesis evaluation.
7. It exports repeatable experimental evidence through scripts and reports.
8. It provides database and architecture extension points for future ML-based
   anomaly detection and forecasting.

## 7.3 Answers to Research Questions

The first research question asked how an event-driven edge gateway can improve
smart energy monitoring pipelines. The implemented gateway improves the
pipeline by adding validation, event detection, event classification, metrics,
and dashboard observability before telemetry becomes only stored history.

The second research question asked how the proposed architecture compares with
a baseline telemetry-storage approach. The repeated high-throughput A/B test
showed that proposed mode preserved almost the same simulator throughput as
baseline mode. The measured latency overhead was small: +0.32 ms average
telemetry latency and +0.77 ms p99 telemetry latency.

The third research question asked whether rule-based processing can detect
abnormal energy events while maintaining low latency. The anomaly experiment
confirmed detection of multiple event types, and telemetry p99 latency
remained below 9 ms in that experiment.

The fourth research question asked how ready the platform is for future AI/ML
extension. The platform is ready at the data and architecture level because it
stores time-series readings, events, validation logs, status history, and a
future `model_predictions` table. However, the current thesis does not
implement or evaluate a machine-learning anomaly detection model.

## 7.4 Limitations

The thesis results should be interpreted within the measured scope.

First, the evaluation used a simulator rather than field hardware. The
software pipeline was tested repeatably, but real STM32/ESP hardware behavior,
sensor accuracy, Wi-Fi stability, and electrical measurement quality require
separate validation.

Second, the experiments were short local Docker runs. They demonstrate
controlled behavior but do not prove long-term production reliability,
multi-day uptime, cloud deployment readiness, or large-scale field
performance.

Third, anomaly detection is rule-based. The system should not be presented as
an AI/ML anomaly detection system in its current form.

Fourth, the current results do not prove storage reduction. Proposed mode
stores additional event and operational evidence, which increased database
growth in the high-throughput experiment. Storage optimization remains future
work.

Finally, the system is not a certified commercial metering platform. It is a
monitoring and observability architecture, not a billing-grade energy meter.

## 7.5 Future AI/ML Extensions

Future work can add model-based anomaly detection. The existing database
already stores readings, event labels, status history, and validation logs
that could support model training or evaluation.

Future ML extensions include:

- unsupervised anomaly detection on voltage, current, and power windows
- load forecasting by device or household
- predictive maintenance from status history and device-failure events
- adaptive thresholds based on historical behavior
- model confidence or anomaly scores stored in `model_predictions`

These extensions should be evaluated separately from the current rule-based
system. A future thesis or project phase should compare rule-only detection
against model-assisted detection using precision, recall, false positives,
latency, and operational cost.

## 7.6 Future Storage Optimization

The current implementation stores raw readings and event evidence. This is
useful for evaluation, but it is not optimized for long-term storage cost.

Future storage work may include:

- selective raw-reading retention
- downsampling old normal readings
- keeping critical events permanently
- storing event-triggering readings longer than normal readings
- compressing or pruning old operational metrics
- measuring database growth under identical baseline/proposed workloads

A valid storage-reduction claim would require a dedicated implementation and
a controlled experiment. It should not be inferred from the current results.

## 7.7 Future Deployment and Security Work

Future deployment work should address security, reliability, and operational
hardening. Practical extensions include:

- TLS-secured MQTT
- per-device credentials
- authentication and authorization for APIs
- production-grade alert delivery
- cloud or hybrid deployment
- backup and restore procedures
- longer-duration soak tests
- hardware-in-the-loop testing

These additions would move the system from a thesis prototype toward a more
complete production-ready monitoring platform.

## 7.8 Final Conclusion

The thesis demonstrates that an event-driven edge gateway can improve an
IoT-based smart energy monitoring pipeline by adding validation, rule-based
event detection, event classification, time-series storage, and operational
dashboards. The proposed gateway preserved approximately the same simulator
throughput as the baseline while adding only a small latency overhead.

The defensible final conclusion is that rule-based edge intelligence can be
added to a smart energy monitoring pipeline without sacrificing low-latency
ingestion behavior. The system is not yet an ML-based or production-certified
platform, but it provides a clear and measurable foundation for future
AI/ML-based anomaly detection, storage optimization, and hardware-field
validation.
