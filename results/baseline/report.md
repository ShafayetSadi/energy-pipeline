# Edge Gateway Run Report

- Captured at: 2026-06-28T08:40:17.001960+00:00
- Source: http://localhost:8001
- Uptime: 122.6s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 143 |
| `events.critical` | 143 |
| `events.type.device_failure` | 143 |
| `messages.received` | 24730 |
| `messages.status` | 789 |
| `messages.telemetry` | 23493 |
| `readings.stored` | 23493 |
| `validation.failures` | 448 |
| `validation.status.success` | 789 |
| `validation.telemetry.success` | 23493 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 789 | 3.80 | 3.68 | 4.69 | 5.71 |
| `telemetry` | 10000 | 4.04 | 3.97 | 4.83 | 5.38 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 9335 |
| INFO | 61 |
| WARNING | 13054 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 2151 |
