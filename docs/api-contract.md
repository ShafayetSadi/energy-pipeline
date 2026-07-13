# HTTP API Contract

This document describes the HTTP interfaces implemented by the current
codebase:

| Service | Docker Compose host URL | Container URL | Implementation |
| --- | --- | --- | --- |
| Edge gateway | `http://localhost:8001` | `http://edge-gateway:8000` | `gateway/app/main.py` |
| Cloud tier | `http://localhost:8002` | `http://cloud-tier:8000` | `cloud/app/main.py` |

The edge gateway owns the operational API backed by TimescaleDB. The cloud tier
receives score-gated escalation batches and optionally verifies them with the
cloud LSTM autoencoder.

This is an HTTP contract only. Device-to-gateway MQTT topics and payloads are
defined by `gateway/app/mqtt/` and `gateway/app/schemas/` and described in
`docs/architecture.md`.

## Common conventions

- Neither service currently requires authentication or an API key.
- Documented application endpoints return JSON. FastAPI also exposes `/docs`
  and `/redoc` as HTML, plus `/openapi.json`, on both services.
- Gateway datetime query parameters use ISO-8601 datetime syntax. Clients
  should include an explicit UTC offset, for example
  `2026-06-15T12:00:00Z`.
- Gateway timestamps read from the database are serialized with
  `datetime.isoformat()`. Nullable database fields are returned as JSON `null`.
- Explicit application errors use FastAPI's `{"detail": "..."}` shape.
  Invalid typed path/query/body values use FastAPI's standard `422` validation
  response unless an endpoint says otherwise.
- Collection endpoints return a bare JSON array. They do not return pagination
  metadata or a total count.

## Edge gateway

### Health and service information

#### `GET /health`

Process liveness. This endpoint does not check the database, MQTT broker, or
background workers.

```json
{
  "status": "ok",
  "service": "edge-gateway"
}
```

#### `GET /ready`

Runs `SELECT 1` against the configured database.

- `200`: `{"status": "ready"}`
- `503`: `{"detail": "db unavailable: <database error>"}`

#### `GET /version`

Returns runtime settings. The values below are defaults and can be overridden
through environment variables.

```json
{
  "service": "edge-gateway",
  "version": "0.1.0",
  "env": "development",
  "processing_mode": "proposed"
}
```

`processing_mode` is either `baseline` or `proposed`.

### Devices

#### `GET /api/v1/devices`

Lists registered devices ordered by `device_id` ascending.

Query parameters:

| Name | Type | Required | Default | Constraint |
| --- | --- | --- | --- | --- |
| `limit` | integer | no | `500` | `1..5000` |

Response:

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

`location`, `firmware_version`, and `last_seen_at` can be `null`. `status` is a
stored string; common values are `unknown`, `online`, `offline`, `maintenance`,
and `error`.

#### `GET /api/v1/devices/{device_id}`

Returns one device using the same shape as a list element.

- `200`: device object
- `404`: `{"detail": "device not found"}`

#### `GET /api/v1/devices/{device_id}/status`

Returns recent status-history rows ordered by `time` descending. An unknown
device produces an empty array rather than `404`.

Query parameters:

| Name | Type | Required | Default | Constraint |
| --- | --- | --- | --- | --- |
| `limit` | integer | no | `50` | `1..500` |

Response:

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

`firmware_version`, `ip_address`, `rssi_dbm`, and `metadata` can be `null`.

### Readings

A reading object has this shape:

```json
{
  "time": "2026-06-15T12:00:00+00:00",
  "device_id": "house_0001",
  "voltage_v": 221.4,
  "current_a": 2.3,
  "power_w": 509.2,
  "temperature_c": 33.5,
  "sequence_no": 1024
}
```

`temperature_c` and `sequence_no` can be `null`.

#### `GET /api/v1/readings`

Lists readings for one device ordered by `time` descending. Both time filters
are inclusive.

Query parameters:

| Name | Type | Required | Default | Constraint |
| --- | --- | --- | --- | --- |
| `device_id` | string | yes | none | non-empty in practice |
| `start_time` | datetime | no | none | returns `time >= start_time` |
| `end_time` | datetime | no | none | returns `time <= end_time` |
| `limit` | integer | no | `200` | `1..5000` |

- `200`: array of reading objects
- `400`: `{"detail": "device_id query parameter is required"}` when
  `device_id` is missing or empty

An unknown device produces an empty array.

#### `GET /api/v1/readings/{device_id}/latest`

Returns the newest reading for the device.

- `200`: reading object
- `404`: `{"detail": "no readings"}`

#### `GET /api/v1/readings/{device_id}/aggregate`

Returns TimescaleDB `time_bucket` aggregates ordered by bucket ascending.

Query parameters:

| Name | Type | Required | Default | Semantics |
| --- | --- | --- | --- | --- |
| `start_time` | datetime | yes | none | inclusive lower bound |
| `end_time` | datetime | yes | none | exclusive upper bound |
| `interval` | string | no | `1 minute` | PostgreSQL interval text |

Example:

```text
GET /api/v1/readings/house_0001/aggregate?start_time=2026-06-15T12:00:00Z&end_time=2026-06-15T13:00:00Z&interval=1%20minute
```

Response:

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

This endpoint requires TimescaleDB's `time_bucket()` function. The application
does not currently validate `interval` against an allowlist before passing it
as a PostgreSQL interval value.

### Events

An event object has this shape:

```json
{
  "event_id": 42,
  "time": "2026-06-15T12:00:05+00:00",
  "device_id": "house_0001",
  "event_type": "OVERLOAD",
  "severity": "CRITICAL",
  "rule_name": "overload",
  "message": "current_a=12.5 gt 10 (rule=overload)",
  "reading_time": "2026-06-15T12:00:05+00:00",
  "event_value": 12.5,
  "threshold_value": 10.0,
  "metadata": {
    "field": "current_a",
    "operator": "gt"
  },
  "acknowledged": false
}
```

`device_id`, `rule_name`, `message`, `reading_time`, `event_value`,
`threshold_value`, and `metadata` can be `null`.

#### `GET /api/v1/events`

Lists events ordered by `time` descending. Supplied filters are exact stored
string matches; the application does not normalize case.

Query parameters:

| Name | Type | Required | Default | Semantics |
| --- | --- | --- | --- | --- |
| `device_id` | string | no | none | exact match |
| `event_type` | string | no | none | exact match |
| `severity` | string | no | none | exact match |
| `start_time` | datetime | no | none | inclusive lower bound |
| `end_time` | datetime | no | none | inclusive upper bound |
| `limit` | integer | no | `100` | `1..1000` |

Response: an array of event objects.

#### `GET /api/v1/events/{event_id}`

- `200`: event object
- `404`: `{"detail": "event not found"}`

`event_id` must be an integer; otherwise FastAPI returns `422`.

#### `POST /api/v1/events/{event_id}/acknowledge`

Sets `acknowledged` to `true` and commits the change. The operation is
idempotent for an existing event.

```json
{
  "event_id": 42,
  "acknowledged": true
}
```

- `200`: acknowledgement object
- `404`: `{"detail": "event not found"}`

### Rules

Rules are loaded into memory from the configured YAML file. The bundled file is
`gateway/config/rules.yaml`. Rule names are returned alphabetically.

A threshold-rule response looks like this:

```json
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
```

The exact object after `rule_name` comes from the YAML rule configuration. The
bundled rules use `threshold` and `percentage_increase` conditions.

#### `GET /api/v1/rules`

Returns all rules currently loaded in the in-process rule engine.

#### `GET /api/v1/rules/{rule_name}`

- `200`: rule object
- `404`: `{"detail": "rule not found"}`

#### `PATCH /api/v1/rules/{rule_name}`

Request body:

```json
{
  "enabled": false
}
```

`enabled` is optional and nullable. If it is a boolean, the endpoint updates
the in-memory rule, upserts its definition in the database, commits, and
returns the full updated rule object. An empty body object or `{"enabled":
null}` returns the current rule without changing it.

- `200`: full rule object
- `404`: `{"detail": "rule not found"}`
- `422`: missing or malformed JSON body, or an `enabled` value that Pydantic
  cannot parse as a boolean

The rule engine does not load definitions back from the database. A process
restart or `POST /api/v1/rules/reload` replaces the in-memory configuration
with the YAML file, so callers must update the YAML file separately for a
durable configuration change.

#### `POST /api/v1/rules/reload`

Reloads the configured YAML file into the in-process rule engine.

```json
{
  "rules_loaded": 6
}
```

### Metrics

Gateway operational counters and latency samples are process-local and reset
when the process restarts. Counters are dynamic: a key is absent until that
activity has occurred. The service also periodically persists metric samples,
but the endpoints below read the current in-memory snapshot unless explicitly
described as a database query.

A latency summary has this shape:

```json
{
  "count": 5000.0,
  "avg_ms": 4.1,
  "p50_ms": 3.2,
  "p95_ms": 12.0,
  "p99_ms": 25.0
}
```

The in-memory sample window retains at most 10,000 values per operation.
Observed operation names can include `telemetry`, `status`, `event`,
`ml_inference`, `ml_batch`, and `cloud_forward`, depending on enabled features.

#### `GET /api/v1/metrics/summary`

```json
{
  "uptime_seconds": 123.4,
  "counters": {
    "messages.received": 5000,
    "readings.stored": 4980,
    "validation.failures": 3
  },
  "latencies": {
    "telemetry": {
      "count": 5000.0,
      "avg_ms": 4.1,
      "p50_ms": 3.2,
      "p95_ms": 12.0,
      "p99_ms": 25.0
    }
  }
}
```

#### `GET /api/v1/metrics/latency`

Returns only the current latency summaries.

```json
{
  "latencies_ms": {
    "telemetry": {
      "count": 5000.0,
      "avg_ms": 4.1,
      "p50_ms": 3.2,
      "p95_ms": 12.0,
      "p99_ms": 25.0
    }
  }
}
```

#### `GET /api/v1/metrics/throughput`

Rates are lifetime process counters divided by current process uptime; they are
not rolling-window rates.

```json
{
  "uptime_seconds": 123.4,
  "messages_per_second": 40.5,
  "readings_per_second": 38.1,
  "events_per_second": 0.5
}
```

`events_per_second` sums the `events.<severity>` counters and excludes
`events.type.<event_type>` counters to avoid counting the same event twice.

#### `GET /api/v1/metrics/data-reduction`

Computes a process-lifetime event-to-stored-reading ratio from in-memory
`events.type.*` and `readings.stored` counters. It does not calculate database
storage bytes. When no raw readings have been stored, the ratio is `0.0`.

```json
{
  "raw_readings_stored": 5000,
  "total_events": 12,
  "data_reduction_ratio": 0.9976
}
```

#### `GET /api/v1/metrics/events-by-severity`

Counts persisted database events by their stored severity since the beginning
of the requested lookback window.

| Name | Type | Required | Default | Constraint |
| --- | --- | --- | --- | --- |
| `hours` | integer | no | `24` | no explicit bounds |

```json
{
  "CRITICAL": 4,
  "WARNING": 8,
  "INFO": 12
}
```

Only severities present in the queried window appear in the object.

#### `GET /api/v1/metrics/quality-by-type`

Counts persisted data-quality log rows by their stored `error_type` over the
requested lookback window.

| Name | Type | Required | Default | Constraint |
| --- | --- | --- | --- | --- |
| `hours` | integer | no | `24` | no explicit bounds |

```json
{
  "invalid_json": 3,
  "voltage_out_of_range": 2
}
```

Only error types present in the queried window appear in the object.

## Cloud tier

The cloud tier keeps counters, recent escalations, verifier buffers, and recent
verdicts in process memory. All are reset on restart. Recent escalation and
verdict buffers each retain at most 500 entries.

The service performs cloud verification only when the configured model artifact
(`models/cloud_lstm_ae.npz` by default) loads successfully. Escalation intake
continues when the verifier is unavailable.

### `GET /health`

Process liveness only. It does not assert that the verifier artifact is loaded.

```json
{
  "status": "ok"
}
```

### `POST /api/v1/escalations`

Accepts one edge-to-cloud escalation batch. The current gateway cloud forwarder
sends this exact envelope:

```json
{
  "source": "edge-gateway",
  "mode": "gated",
  "readings": [
    {
      "device_id": "house_0001",
      "timestamp": "2026-06-15T12:00:00+00:00",
      "reading_time": "2026-06-15T12:00:00+00:00",
      "voltage_v": 180.0,
      "current_a": 2.3,
      "power_w": 414.0,
      "temperature_c": 33.5,
      "anomaly_score": 1.42,
      "threshold": 1.1,
      "model_version": "iforest_v1",
      "rule_fired": true
    }
  ]
}
```

Envelope fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `source` | string | yes | gateway service name in normal operation |
| `mode` | string | yes | gateway sends `gated` or `all` |
| `readings` | array | no | defaults to `[]` |

Reading fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `device_id` | string | yes | no explicit length constraint |
| `timestamp` | string | yes | accepted as a string, not parsed as datetime |
| `reading_time` | string | yes | accepted as a string, not parsed as datetime |
| `voltage_v` | number | yes | no explicit range constraint |
| `current_a` | number | yes | no explicit range constraint |
| `power_w` | number | yes | no explicit range constraint |
| `temperature_c` | number or `null` | no | defaults to `null` |
| `anomaly_score` | number | yes | edge-model score |
| `threshold` | number | yes | edge-model decision threshold |
| `model_version` | string | yes | edge-model artifact version |
| `rule_fired` | boolean | no | defaults to `false` |

Success response:

```json
{
  "accepted": 1
}
```

`accepted` is the number of readings in the validated envelope. A successful
request increments in-memory batch, reading, byte, mode, and per-device
counters. If the verifier is available, readings are also buffered per device
until a complete model window can be scored.

The endpoint parses and validates the raw request body inside the route rather
than declaring the envelope as a FastAPI body parameter. Consequently, the
generated OpenAPI operation does not include this request schema, and invalid
JSON/envelopes do not currently have a stable documented client-error response.

### `GET /api/v1/escalations/recent`

Returns the most recently accepted reading objects in insertion order within
the selected tail of the buffer.

| Name | Type | Required | Default | Constraint |
| --- | --- | --- | --- | --- |
| `limit` | integer | no | `50` | no explicit bounds; clients should send a positive value |

The response is an array of the reading shape accepted by the escalation
endpoint, including defaulted `temperature_c` and `rule_fired` fields. At most
500 entries are retained.

### `GET /api/v1/verdicts/recent`

Returns the most recent cloud-verifier verdicts in insertion order within the
selected tail of the buffer.

| Name | Type | Required | Default | Constraint |
| --- | --- | --- | --- | --- |
| `limit` | integer | no | `50` | no explicit bounds; clients should send a positive value |

```json
[
  {
    "device_id": "house_0001",
    "recon_error": 1.37,
    "threshold": 1.1,
    "confirmed": true
  }
]
```

The response is empty until the verifier is available and a per-device input
window has filled. The current artifact normally uses an eight-reading window,
but the value is loaded from model metadata rather than fixed by the API.

### `GET /api/v1/metrics/summary`

Returns process-lifetime cloud-tier counters and verifier availability.

```json
{
  "uptime_seconds": 123.4,
  "verifier": {
    "available": true,
    "version": "lstm_ae_v1"
  },
  "counters": {
    "escalations.batches": 5,
    "escalations.readings": 40,
    "escalations.bytes_received": 12400,
    "escalations.mode.gated": 40,
    "escalations.device.house_0001": 40,
    "verify.inference_ms": 3.84,
    "verify.windows": 5,
    "verify.scored": 40,
    "verify.confirmed": 6,
    "verify.suppressed": 34,
    "verify.avg_inference_ms": 0.768
  }
}
```

Counter keys are dynamic and absent until used. When the verifier is disabled,
`verifier.version` is `"disabled"` and verification counters are absent.
`verify.inference_ms` is cumulative inference time, while
`verify.avg_inference_ms` is derived as cumulative time divided by completed
verification windows.

## Interfaces not implemented

The current HTTP applications do not expose create/update endpoints for devices
or readings, a delete API, a login/authentication API, WebSockets, or a generic
gateway-to-cloud proxy. Device and reading state enters the gateway through
MQTT ingestion rather than REST mutation endpoints.
