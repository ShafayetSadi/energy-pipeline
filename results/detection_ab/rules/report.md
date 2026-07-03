# Edge Gateway Run Report

- Captured at: 2026-07-03T04:48:35.636166+00:00
- Source: http://localhost:8001
- Uptime: 603.9s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 10 |
| `events.critical` | 32 |
| `events.info` | 30 |
| `events.type.device_failure` | 10 |
| `events.type.over_voltage` | 15 |
| `events.type.overload` | 22 |
| `events.type.power_spike` | 490 |
| `events.type.under_voltage` | 30 |
| `events.type.voltage_anomaly` | 30 |
| `events.warning` | 535 |
| `messages.received` | 1418 |
| `messages.status` | 39 |
| `messages.telemetry` | 1379 |
| `readings.stored` | 1379 |
| `validation.status.success` | 39 |
| `validation.telemetry.success` | 1379 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 39 | 5.47 | 5.28 | 6.54 | 6.80 |
| `telemetry` | 1379 | 6.72 | 6.58 | 8.09 | 9.61 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 32 |
| INFO | 30 |
| WARNING | 535 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
