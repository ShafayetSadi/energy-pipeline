# Edge Gateway Run Report

- Captured at: 2026-06-30T09:16:35.198830+00:00
- Source: http://localhost:8001
- Uptime: 605.1s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 10 |
| `events.critical` | 228 |
| `events.info` | 30 |
| `events.type.device_failure` | 10 |
| `events.type.ml_anomaly` | 7 |
| `events.type.over_voltage` | 15 |
| `events.type.overload` | 218 |
| `events.type.power_spike` | 387 |
| `events.type.under_voltage` | 30 |
| `events.type.voltage_anomaly` | 30 |
| `events.warning` | 439 |
| `messages.received` | 1428 |
| `messages.status` | 53 |
| `messages.telemetry` | 1375 |
| `ml.anomalies` | 94 |
| `ml.scored` | 1375 |
| `readings.stored` | 1375 |
| `validation.status.success` | 53 |
| `validation.telemetry.success` | 1375 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ml_inference` | 1375 | 11.90 | 11.68 | 13.24 | 16.50 |
| `status` | 53 | 5.49 | 5.43 | 6.45 | 6.65 |
| `telemetry` | 1375 | 19.63 | 19.41 | 21.97 | 24.83 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 228 |
| INFO | 30 |
| WARNING | 439 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
