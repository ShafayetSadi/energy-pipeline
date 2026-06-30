# Chapter 1: Introduction

## 1.1 Background

Smart energy monitoring systems are increasingly built from connected sensing
devices, lightweight communication protocols, local or cloud gateways,
time-series storage, and visualization dashboards. These systems help users
and operators observe voltage, current, power, and device status over time.
However, monitoring is more useful when the system can also identify abnormal
conditions quickly, not only store raw measurements for later review.

IoT-based energy monitoring commonly uses microcontrollers and network modules
to publish measurements from distributed devices. MQTT is suitable for this
kind of system because it supports lightweight publish/subscribe messaging
between devices and backend services. An edge gateway can subscribe to MQTT
topics, validate incoming payloads, detect important events, and store the
resulting data in a time-series database for dashboards and later analysis.

## 1.2 Problem Statement

Raw telemetry pipelines can store energy measurements but often provide limited
local intelligence. If telemetry is only collected and stored, abnormal
conditions such as overload, voltage deviation, device silence, or malformed
payloads may not become visible until a later dashboard query or manual review.
As the number of devices grows, the monitoring pipeline also needs observable
validation, event classification, and latency evidence.

This thesis addresses that problem by designing and implementing an
event-driven edge gateway for IoT-based smart energy monitoring. The gateway
uses MQTT for device communication, validates incoming payloads, applies
rule-based event detection, stores time-series readings in TimescaleDB, and
exposes readings, events, and system metrics through Grafana dashboards.

## 1.3 Motivation

The motivation for this work is the need for timely, observable, and
extensible smart energy monitoring. A raw telemetry pipeline can show what
happened, but it may not immediately classify abnormal conditions or expose
data-quality problems. In practical energy monitoring, operators need to know
whether devices are reporting, whether measurements look abnormal, and whether
the gateway is processing messages within acceptable latency.

Academically, the project is useful because it provides a measurable
architecture comparison. Instead of only building a dashboard, this thesis
compares a baseline ingestion path against a proposed event-driven edge
gateway. The comparison uses throughput, latency, validation, event-detection,
and observability evidence.

## 1.4 Aim and Objectives

The aim of this thesis is to design and implement an event-driven edge gateway
for IoT-based smart energy monitoring using MQTT, rule-based event detection,
TimescaleDB storage, and Grafana observability dashboards.

The specific objectives are:

1. Build an MQTT-based telemetry pipeline for smart energy monitoring devices.
2. Implement an edge gateway that validates incoming telemetry and status messages.
3. Detect abnormal energy conditions using configurable rule-based processing.
4. Store accepted readings, events, validation logs, and operational metrics in PostgreSQL/TimescaleDB.
5. Provide Grafana dashboards for energy overview, device detail, event timeline, system observability, and thesis evaluation.
6. Compare a baseline ingestion path with the proposed event-driven gateway using throughput, latency, validation, event-detection, and storage-cost evidence.
7. Add an unsupervised edge anomaly detector (Isolation Forest) and evaluate it against rule-based detection (Phase 1 of a hybrid edge–cloud direction).

## 1.5 Scope of the Project

The scope of the project is the design, implementation, and evaluation of the
smart energy monitoring pipeline from MQTT telemetry ingestion to edge
processing, storage, and dashboards.

Included:

- STM32-based energy node
- MQTT communication
- edge gateway processing
- rule-based event detection
- edge ML anomaly detection (Isolation Forest, Phase 1), offline-evaluated
- PostgreSQL/TimescaleDB storage
- Grafana dashboards

Excluded / out of scope:

- full production deployment
- large-scale field hardware validation
- cloud-tier ML, forecasting, and score-gated edge→cloud escalation
- certified commercial metering accuracy
- storage reduction as a measured result

## 1.6 Research Questions

This thesis answers the following research questions:

1. How can an event-driven edge gateway improve smart energy monitoring pipelines?
2. How does the proposed architecture compare with a baseline telemetry-storage approach?
3. Can rule-based processing detect abnormal energy events while maintaining low processing latency?
4. Can a lightweight unsupervised model (Isolation Forest) add anomaly detection at the edge, and how does it compare with rule-based detection?

## 1.7 Expected Contributions

The expected contributions are:

1. A working edge-gateway architecture for IoT smart energy monitoring.
2. A baseline versus proposed evaluation showing the overhead of event-driven edge processing.
3. Rule-based detection evidence for overload, power spike, voltage anomaly, under-voltage, over-voltage, and device-failure conditions.
4. Validation and data-quality evidence for malformed MQTT payloads.
5. Grafana dashboards that expose readings, events, gateway metrics, and thesis evaluation results.
6. An edge Isolation Forest anomaly detector (Phase 1) with an offline precision/recall evaluation and an honest rules-versus-ML comparison.
7. A clearly defined phased path toward a hybrid edge–cloud design (cloud-tier model, score-gated escalation, storage optimization) without claiming those as completed results.

## 1.8 Thesis Organization

Chapter 1 introduces the problem, motivation, scope, research questions, and
expected contributions. Chapter 2 reviews related work on IoT energy
monitoring, MQTT communication, edge processing, time-series storage, and
observability dashboards. Chapter 3 presents the proposed system architecture.
Chapter 4 describes the implementation methodology, including the gateway,
database, rules, and dashboards. Chapter 5 explains the experimental
evaluation method. Chapter 6 presents and discusses the results. Chapter 7
concludes the thesis and describes future work such as ML anomaly detection,
storage optimization, and broader hardware validation.
