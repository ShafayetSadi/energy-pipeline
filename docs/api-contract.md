# API Contract

The HTTP API exposed by the FastAPI edge gateway. Backed by TimescaleDB.

All response bodies are JSON. Timestamps are ISO-8601 strings with explicit
UTC offsets.

## Health

### `GET /health`

- 200: `{"status": "ok", "service": "edge-gateway"}`

### `GET /ready`

- 200 when database is reachable: `{"status": "ready"}`
- 503 otherwise

### `GET /version`

```json
{
  "service": "edge-gateway",
  "version": "0.1.0",
  "env": "development",
  "processing_mode": "proposed"
}
```

## Devices

### `GET /api/v1/devices?limit=500`

List devices known to the gateway.

```json
[
  {
    "device_id": "house_0001",
    "location": null,
    "device_type": "energy_node",
    "firmware_version": "0.1.0",
    "status": "online",
    "last_seen_at": "2026-06-15T12:00:00+00:00"
  }
]
```

### `GET /api/v1/devices/{device_id}`

Same shape as the list element.

### `GET /api/v1/devices/{device_id}/status?limit=50`

Returns the recent `device_status_history` rows.

```json
[
  {
    "time": "2026-06-15T12:00:00+00:00",
    "status": "online",
    "firmware_version": "0.1.0",
    "ip_address": null,
    "rssi_dbm": -55.0,
    "metadata": null
  }
]
```

## Readings

### `GET /api/v1/readings?device_id=house_0001&start_time=...&end_time=...&limit=200`

`device_id` is required. Returns up to `limit` readings (default 200, max 5000).

```json
[
  {
    "time": "2026-06-15T12:00:00+00:00",
    "device_id": "house_0001",
    "voltage_v": 221.4,
    "current_a": 2.3,
    "power_w": 509.2,
    "temperature_c": 33.5,
    "sequence_no": 1024
  }
]
```

### `GET /api/v1/readings/{device_id}/latest`

The most recent reading, or 404.

### `GET /api/v1/readings/{device_id}/aggregate?start_time=...&end_time=...&interval=1 minute`

Returns bucketed aggregates (`time_bucket` over the interval). Requires
TimescaleDB.

```json
[
  {
    "bucket": "2026-06-15T12:00:00+00:00",
    "avg_voltage_v": 220.5,
    "avg_current_a": 2.1,
    "avg_power_w": 463.0,
    "max_power_w": 480.0,
    "min_voltage_v": 218.2,
    "sample_count": 60
  }
]
```

## Events

### `GET /api/v1/events?device_id=...&event_type=...&severity=...&start_time=...&end_time=...&limit=100`

Returns at most `limit` events ordered by time DESC.

```json
[
  {
    "event_id": 42,
    "time": "2026-06-15T12:00:05+00:00",
    "device_id": "house_0001",
    "event_type": "OVERLOAD",
    "severity": "CRITICAL",
    "rule_name": "overload",
    "message": "current_a=12.5 gt 10.0 (rule=overload)",
    "reading_time": "2026-06-15T12:00:05+00:00",
    "event_value": 12.5,
    "threshold_value": 10.0,
    "metadata": { "field": "current_a", "operator": "gt" },
    "acknowledged": false
  }
]
```

### `GET /api/v1/events/{event_id}`

One event.

### `POST /api/v1/events/{event_id}/acknowledge`

Marks the event acknowledged. Returns `{"event_id": 42, "acknowledged": true}`.

## Rules

### `GET /api/v1/rules`

```json
[
  {
    "rule_name": "undervoltage",
    "enabled": true,
    "event_type": "UNDER_VOLTAGE",
    "severity": "WARNING",
    "condition": {
      "type": "threshold",
      "field": "voltage_v",
      "operator": "lt",
      "value": 200
    }
  }
]
```

### `GET /api/v1/rules/{rule_name}`

### `PATCH /api/v1/rules/{rule_name}` `{"enabled": false}`

### `POST /api/v1/rules/reload` — reload from disk

## Metrics

### `GET /api/v1/metrics/summary`

```json
{
  "uptime_seconds": 123.4,
  "counters": { "messages.received": 5000, "validation.failures": 3, ... },
  "latencies": {
    "telemetry": { "count": 5000, "avg_ms": 4.1, "p50_ms": 3.2, "p95_ms": 12.0, "p99_ms": 25.0 }
  }
}
```

### `GET /api/v1/metrics/throughput`

```json
{
  "uptime_seconds": 123.4,
  "messages_per_second": 40.5,
  "readings_per_second": 38.1,
  "events_per_second": 0.5
}
```

### `GET /api/v1/metrics/data-reduction`

```json
{
  "raw_readings_stored": 5000,
  "total_events": 12,
  "data_reduction_ratio": 0.9976
}
```

### `GET /api/v1/metrics/events-by-severity?hours=24`

```json
{ "CRITICAL": 4, "WARNING": 8, "INFO": 12 }
```

### `GET /api/v1/metrics/quality-by-type?hours=24`

```json
{ "invalid_json": 3, "voltage_out_of_range": 2 }
```
