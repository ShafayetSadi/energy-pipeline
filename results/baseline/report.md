# Edge Gateway Run Report

- Captured at: 2026-06-28T06:13:49.212791+00:00
- Source: http://localhost:8001
- Uptime: 122.3s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 124 |
| `events.critical` | 124 |
| `events.type.device_failure` | 124 |
| `messages.received` | 24724 |
| `messages.status` | 790 |
| `messages.telemetry` | 23442 |
| `readings.stored` | 23442 |
| `validation.failures` | 492 |
| `validation.status.success` | 790 |
| `validation.telemetry.success` | 23442 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 790 | 3.54 | 3.47 | 4.12 | 5.05 |
| `telemetry` | 10000 | 3.84 | 3.77 | 4.49 | 5.00 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 124 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 492 |
