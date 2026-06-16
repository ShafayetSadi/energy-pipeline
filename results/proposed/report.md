# Edge Gateway Run Report

- Captured at: 2026-06-16T09:31:15.259188+00:00
- Source: http://localhost:8000
- Uptime: 176.9s

## Counters

| Counter | Value |
| --- | ---: |
| `events.type.power_spike` | 5 |
| `events.warning` | 5 |
| `messages.received` | 74 |
| `messages.telemetry` | 74 |
| `readings.stored` | 74 |
| `validation.telemetry.success` | 74 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `telemetry` | 74 | 12.13 | 9.63 | 23.67 | 84.68 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 46 |
| INFO | 30 |
| WARNING | 332 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 151 |
