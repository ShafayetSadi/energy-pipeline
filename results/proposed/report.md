# Edge Gateway Run Report

- Captured at: 2026-06-28T08:56:53.417998+00:00
- Source: http://localhost:8001
- Uptime: 846.1s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 317 |
| `events.critical` | 4463 |
| `events.info` | 31 |
| `events.type.device_failure` | 317 |
| `events.type.over_voltage` | 15 |
| `events.type.overload` | 4146 |
| `events.type.power_spike` | 6462 |
| `events.type.under_voltage` | 31 |
| `events.type.voltage_anomaly` | 31 |
| `events.warning` | 6508 |
| `messages.received` | 26628 |
| `messages.status` | 823 |
| `messages.telemetry` | 25162 |
| `readings.stored` | 25162 |
| `validation.failures` | 643 |
| `validation.status.success` | 823 |
| `validation.telemetry.success` | 25162 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `status` | 823 | 4.04 | 3.90 | 5.22 | 5.84 |
| `telemetry` | 10000 | 4.50 | 4.40 | 5.75 | 6.46 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 13798 |
| INFO | 92 |
| WARNING | 19562 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
| `invalid_json` | 2794 |
