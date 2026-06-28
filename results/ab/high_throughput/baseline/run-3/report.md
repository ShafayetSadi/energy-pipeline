# Edge Gateway Run Report

- Captured at: 2026-06-28T09:39:51.881295+00:00
- Source: http://localhost:8001
- Uptime: 122.1s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 136 |
| `events.critical` | 136 |
| `events.type.device_failure` | 136 |
| `messages.received` | 24747 |
| `messages.status` | 779 |
| `messages.telemetry` | 23514 |
| `readings.stored` | 23514 |
| `validation.failures` | 454 |
| `validation.status.success` | 779 |
| `validation.telemetry.success` | 23514 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 779 | 3.90 | 3.80 | 4.63 | 5.19 |
| `telemetry` | 10000 | 4.05 | 3.99 | 4.78 | 5.26 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 136 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 454 |
