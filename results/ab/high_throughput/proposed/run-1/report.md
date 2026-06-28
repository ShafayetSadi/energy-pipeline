# Edge Gateway Run Report

- Captured at: 2026-06-28T09:33:15.465208+00:00
- Source: http://localhost:8001
- Uptime: 122.2s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 137 |
| `events.critical` | 4002 |
| `events.type.device_failure` | 137 |
| `events.type.overload` | 3865 |
| `events.type.power_spike` | 5907 |
| `events.warning` | 5907 |
| `messages.received` | 24754 |
| `messages.status` | 818 |
| `messages.telemetry` | 23443 |
| `readings.stored` | 23443 |
| `validation.failures` | 493 |
| `validation.status.success` | 818 |
| `validation.telemetry.success` | 23443 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 818 | 3.89 | 3.79 | 4.77 | 5.56 |
| `telemetry` | 10000 | 4.46 | 4.35 | 5.69 | 6.60 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 4002 |
| WARNING | 5907 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 493 |
