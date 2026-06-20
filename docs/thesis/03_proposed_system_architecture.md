# Chapter 3: Proposed System Architecture

## 3.1 System Overview

Present the full architecture from energy monitoring node to broker, edge gateway, storage, and dashboard.

## 3.2 STM32 Energy Monitoring Node

Describe the STM32-based node, what it measures, how it packages readings, and how it publishes telemetry.

## 3.3 MQTT Broker Layer

Explain the broker role, topic routing, decoupling of producers/consumers, and message-flow reliability considerations.

## 3.4 FastAPI Edge Gateway

Describe the gateway responsibilities: MQTT consumption, validation, event generation, persistence, REST APIs, and metrics endpoints.

## 3.5 Data Validation Pipeline

Explain schema validation, rejected payload handling, and quality control before storage.

## 3.6 Rule Engine and Event Classifier

Describe threshold rules, percentage increase rules, event severity, and how the system converts raw telemetry into meaningful events.

## 3.7 PostgreSQL/TimescaleDB Storage Layer

Describe the schema, hypertables, continuous aggregates, and why this storage approach is appropriate.

## 3.8 Grafana Dashboard and Alerting

Explain dashboard design, visual monitoring, and alerting workflow.

## 3.9 AI/ML-Ready Extension Points

Describe where prediction models, anomaly detection, or forecasting components can be integrated later.

---

## Migrated seed notes (draft/reference)

- TimescaleDB was preferred over raw PostgreSQL because continuous aggregates support faster dashboard views at 1-minute and 5-minute granularity.
- The `model_predictions` table already exists as a future extension point, even though it is not used in the current version.
- When writing the final thesis, connect these design points to the architecture diagram and database design evidence.

---

## Notes / Evidence to collect

- architecture diagram
- topic flow diagram
- component responsibility table
- database ERD or schema snapshot
- future AI/ML integration sketch
