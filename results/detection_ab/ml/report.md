# Edge Gateway Run Report

- Captured at: 2026-06-30T09:06:18.406155+00:00
- Source: http://localhost:8001
- Uptime: 604.7s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 10 |
| `events.critical` | 10 |
| `events.type.device_failure` | 10 |
| `events.type.ml_anomaly` | 9 |
| `events.warning` | 9 |
| `messages.received` | 1425 |
| `messages.status` | 49 |
| `messages.telemetry` | 1376 |
| `ml.anomalies` | 104 |
| `ml.scored` | 1376 |
| `readings.stored` | 1376 |
| `validation.status.success` | 49 |
| `validation.telemetry.success` | 1376 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ml_inference` | 1376 | 11.85 | 11.64 | 13.43 | 16.28 |
| `status` | 49 | 5.57 | 5.43 | 6.58 | 7.12 |
| `telemetry` | 1376 | 19.30 | 19.05 | 21.51 | 24.98 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 10 |
| WARNING | 9 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
