# Edge Gateway Run Report

- Captured at: 2026-07-03T05:09:10.118218+00:00
- Source: http://localhost:8001
- Uptime: 604.9s

## Counters

| Counter | Value |
| --- | ---: |
| `devices.offline_detected` | 10 |
| `events.critical` | 32 |
| `events.info` | 30 |
| `events.type.device_failure` | 10 |
| `events.type.ml_anomaly` | 5 |
| `events.type.over_voltage` | 16 |
| `events.type.overload` | 22 |
| `events.type.power_spike` | 428 |
| `events.type.under_voltage` | 30 |
| `events.type.voltage_anomaly` | 30 |
| `events.warning` | 479 |
| `messages.received` | 1421 |
| `messages.status` | 45 |
| `messages.telemetry` | 1376 |
| `ml.anomalies` | 88 |
| `ml.batches` | 1268 |
| `ml.scored` | 1376 |
| `readings.stored` | 1376 |
| `validation.status.success` | 45 |
| `validation.telemetry.success` | 1376 |

## Latencies (ms)

| Operation | Count | Avg | p50 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ml_inference` | 1376 | 10.41 | 11.05 | 12.61 | 13.82 |
| `ml_queue` | 1376 | 49.02 | 50.92 | 51.71 | 54.87 |
| `status` | 45 | 5.47 | 5.31 | 6.74 | 7.53 |
| `telemetry` | 1376 | 6.65 | 6.47 | 8.17 | 9.96 |

## Events by severity (24h)

| Severity | Count |
| --- | ---: |
| CRITICAL | 32 |
| INFO | 30 |
| WARNING | 479 |

## Validation errors by type (24h)

| Error type | Count |
| --- | ---: |
