# Edge Gateway Run Report

- Captured at: 2026-06-22T07:49:52.606029+00:00
- Source: http://localhost:8001
- Uptime: 7466.5s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 308 |
| `events.critical` | 327 |
| `events.type.device_failure` | 308 |
| `events.type.overload` | 19 |
| `events.type.power_spike` | 7342 |
| `events.warning` | 7342 |
| `messages.received` | 24788 |
| `messages.status` | 836 |
| `messages.telemetry` | 23495 |
| `readings.stored` | 23495 |
| `validation.failures` | 457 |
| `validation.status.success` | 836 |
| `validation.telemetry.success` | 23495 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 836 | 3.70 | 3.57 | 4.61 | 5.26 |
| `telemetry` | 10000 | 4.12 | 4.04 | 5.03 | 5.52 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 327 |
| WARNING | 7342 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 457 |
