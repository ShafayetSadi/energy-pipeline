# Edge Gateway Run Report

- Captured at: 2026-06-28T09:54:41.508089+00:00
- Source: http://localhost:8001
- Uptime: 725.1s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 12 |
| `events.critical` | 296 |
| `events.info` | 31 |
| `events.type.device_failure` | 12 |
| `events.type.over_voltage` | 14 |
| `events.type.overload` | 284 |
| `events.type.power_spike` | 430 |
| `events.type.under_voltage` | 31 |
| `events.type.voltage_anomaly` | 31 |
| `events.warning` | 475 |
| `messages.received` | 1925 |
| `messages.status` | 68 |
| `messages.telemetry` | 1709 |
| `readings.stored` | 1709 |
| `validation.failures` | 148 |
| `validation.status.success` | 68 |
| `validation.telemetry.success` | 1709 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 68 | 5.30 | 5.24 | 6.17 | 6.29 |
| `telemetry` | 1709 | 6.62 | 6.56 | 7.98 | 8.78 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 296 |
| INFO | 31 |
| WARNING | 475 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 148 |
