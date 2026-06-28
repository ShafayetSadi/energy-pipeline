# Edge Gateway Run Report

- Captured at: 2026-06-28T09:35:27.883491+00:00
- Source: http://localhost:8001
- Uptime: 122.4s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 138 |
| `events.critical` | 138 |
| `events.type.device_failure` | 138 |
| `messages.received` | 24743 |
| `messages.status` | 783 |
| `messages.telemetry` | 23510 |
| `readings.stored` | 23510 |
| `validation.failures` | 450 |
| `validation.status.success` | 783 |
| `validation.telemetry.success` | 23510 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 783 | 3.86 | 3.78 | 4.66 | 5.74 |
| `telemetry` | 10000 | 4.02 | 3.93 | 4.95 | 5.54 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 138 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 450 |
