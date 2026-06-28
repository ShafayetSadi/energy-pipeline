# Edge Gateway Run Report

- Captured at: 2026-06-28T09:42:04.020182+00:00
- Source: http://localhost:8001
- Uptime: 122.3s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 138 |
| `events.critical` | 4032 |
| `events.type.device_failure` | 138 |
| `events.type.overload` | 3894 |
| `events.type.power_spike` | 5801 |
| `events.warning` | 5801 |
| `messages.received` | 24753 |
| `messages.status` | 777 |
| `messages.telemetry` | 23496 |
| `readings.stored` | 23496 |
| `validation.failures` | 480 |
| `validation.status.success` | 777 |
| `validation.telemetry.success` | 23496 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 777 | 3.85 | 3.78 | 4.50 | 4.90 |
| `telemetry` | 10000 | 4.28 | 4.19 | 5.21 | 5.74 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 4032 |
| WARNING | 5801 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 480 |
