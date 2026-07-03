# Edge Gateway Run Report

- Captured at: 2026-07-03T04:58:52.577301+00:00
- Source: http://localhost:8001
- Uptime: 605.4s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 10 |
| `events.critical` | 10 |
| `events.type.device_failure` | 10 |
| `events.type.ml_anomaly` | 6 |
| `events.warning` | 6 |
| `messages.received` | 1425 |
| `messages.status` | 46 |
| `messages.telemetry` | 1379 |
| `ml.anomalies` | 93 |
| `ml.batches` | 1256 |
| `ml.scored` | 1379 |
| `readings.stored` | 1379 |
| `validation.status.success` | 46 |
| `validation.telemetry.success` | 1379 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ml_inference` | 1379 | 10.42 | 11.02 | 13.11 | 15.63 |
| `ml_queue` | 1379 | 48.75 | 50.82 | 51.74 | 54.97 |
| `status` | 46 | 5.72 | 5.19 | 7.62 | 9.47 |
| `telemetry` | 1379 | 6.35 | 6.24 | 7.64 | 10.35 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 10 |
| WARNING | 6 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
