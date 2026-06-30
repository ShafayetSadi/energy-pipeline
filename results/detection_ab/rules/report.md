# Edge Gateway Run Report

- Captured at: 2026-06-30T08:56:01.828770+00:00
- Source: http://localhost:8001
- Uptime: 611.1s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 10 |
| `events.critical` | 252 |
| `events.info` | 30 |
| `events.type.device_failure` | 10 |
| `events.type.over_voltage` | 15 |
| `events.type.overload` | 242 |
| `events.type.power_spike` | 355 |
| `events.type.under_voltage` | 30 |
| `events.type.voltage_anomaly` | 30 |
| `events.warning` | 400 |
| `messages.received` | 1428 |
| `messages.status` | 49 |
| `messages.telemetry` | 1379 |
| `readings.stored` | 1379 |
| `validation.status.success` | 49 |
| `validation.telemetry.success` | 1379 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 49 | 5.63 | 5.31 | 6.46 | 7.12 |
| `telemetry` | 1379 | 6.72 | 6.57 | 8.33 | 9.71 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 252 |
| INFO | 30 |
| WARNING | 400 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
