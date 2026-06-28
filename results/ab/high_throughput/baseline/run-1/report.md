# Edge Gateway Run Report

- Captured at: 2026-06-28T09:31:03.394169+00:00
- Source: http://localhost:8001
- Uptime: 122.2s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 136 |
| `events.critical` | 136 |
| `events.type.device_failure` | 136 |
| `messages.received` | 24705 |
| `messages.status` | 765 |
| `messages.telemetry` | 23480 |
| `readings.stored` | 23480 |
| `validation.failures` | 460 |
| `validation.status.success` | 765 |
| `validation.telemetry.success` | 23480 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 765 | 3.76 | 3.70 | 4.42 | 5.00 |
| `telemetry` | 10000 | 4.24 | 4.15 | 5.18 | 5.77 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 136 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 460 |
