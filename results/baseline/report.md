# Edge Gateway Run Report

- Captured at: 2026-06-22T10:16:59.352889+00:00
- Source: http://localhost:8001
- Uptime: 3335.2s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 395 |
| `events.critical` | 395 |
| `events.type.device_failure` | 395 |
| `messages.received` | 24722 |
| `messages.status` | 803 |
| `messages.telemetry` | 23419 |
| `readings.stored` | 23419 |
| `validation.failures` | 500 |
| `validation.status.success` | 803 |
| `validation.telemetry.success` | 23419 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 803 | 9.18 | 9.54 | 12.18 | 12.89 |
| `telemetry` | 10000 | 10.32 | 11.47 | 13.04 | 13.79 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 903 |
| WARNING | 7342 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 1178 |
