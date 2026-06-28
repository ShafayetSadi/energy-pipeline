# Edge Gateway Run Report

- Captured at: 2026-06-28T09:37:39.878392+00:00
- Source: http://localhost:8001
- Uptime: 122.2s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 109 |
| `events.critical` | 3908 |
| `events.type.device_failure` | 109 |
| `events.type.overload` | 3799 |
| `events.type.power_spike` | 6136 |
| `events.warning` | 6136 |
| `messages.received` | 24726 |
| `messages.status` | 786 |
| `messages.telemetry` | 23479 |
| `readings.stored` | 23478 |
| `validation.failures` | 461 |
| `validation.status.success` | 786 |
| `validation.telemetry.success` | 23479 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 786 | 3.88 | 3.80 | 4.68 | 5.13 |
| `telemetry` | 10000 | 4.54 | 4.44 | 5.76 | 6.53 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 3908 |
| WARNING | 6137 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 461 |
