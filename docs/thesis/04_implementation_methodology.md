# Chapter 4: Implementation Methodology

## 4.1 Hardware Setup

Describe the physical setup of the STM32 energy monitoring node, sensing arrangement, and test environment.

## 4.2 Firmware Design

Explain firmware responsibilities, data sampling, formatting, and message publishing workflow.

## 4.3 MQTT Topic and Payload Design

Document the topic structure (such as telemetry, status, and events) and payload fields used by the system.

Example notes:

- `energy/+/telemetry`
- `energy/+/status`
- `energy/+/events`

## 4.4 Backend API and MQTT Consumer

Explain how the FastAPI backend consumes MQTT messages and exposes REST endpoints for monitoring and querying.

## 4.5 Database Schema

Describe the database tables, relationships, indexes, hypertables, and aggregation support.

## 4.6 Rule Engine Implementation

Explain how rules are configured, loaded, evaluated, and reloaded at runtime.

## 4.7 Dashboard Implementation

Describe how Grafana dashboards were provisioned and what panels or views were implemented.

## 4.8 Docker-Based Deployment

Explain the containerized setup for Mosquitto, gateway, database, Grafana, and simulator.

## 4.9 Testing Strategy

Describe unit tests, integration checks, simulated scenarios, and comparison runs.

---

## Migrated seed notes (draft/reference)

- `aiomqtt` was selected because it fits the native asyncio design of the gateway and avoids a callback-bridge style client.
- The rule engine was placed before storage because the proposed system aims to reduce unnecessary storage growth while detecting important events earlier.
- The `rule_definitions` table exists even though rules are file-based, because it provides a future path for API-driven or UI-driven rule management.

---

## Notes / Evidence to collect

- firmware snippets or flowcharts
- payload JSON examples
- API endpoint screenshots
- schema screenshots
- docker-compose diagram
- test plan and test evidence
