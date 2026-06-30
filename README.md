# Energy Edge Monitoring

Event-driven edge gateway for IoT-based smart energy monitoring. Built
directly from [`docs/architecture.md`](docs/architecture.md).

```mermaid
flowchart LR
    A["Energy node(s)\n(or simulator)"] -->|"MQTT\nenergy/+/telemetry"| B[Mosquitto\nbroker]
    B -->|async pipeline| C["Edge Gateway\n(FastAPI)"]
    C -->|"validate · rule engine\nstorage policy"| D[TimescaleDB]
    C -->|"alert outbox"| F["Alert worker\nconsole/webhook/Slack"]
    D --> E[Grafana]
```

## Stack

- **Edge gateway** — FastAPI, SQLAlchemy 2 (async), `aiomqtt`, Pydantic v2,
  structlog. Subscribes to `energy/+/telemetry`, `energy/+/status`,
  `energy/+/events`, validates payloads, applies the rule engine and storage
  policy, persists to TimescaleDB, and enqueues durable alert deliveries.
- **Edge ML detector** — optional Isolation Forest anomaly detector (Phase 1),
  trained by `scripts/train_anomaly_model.py`, loaded from `/app/models`.
- **MQTT broker** — Eclipse Mosquitto (`config/mosquitto/mosquitto.conf`).
- **Storage** — TimescaleDB hypertables for `energy_readings`, `events`,
  `system_metrics`, `device_status_history`; continuous aggregate
  `energy_readings_1min` is managed by Alembic migrations under
  `database/migrations/`. `STORAGE_POLICY` controls proposed-mode raw reading
  storage, while thesis-safe retention defaults prune raw/operational tables.
- **Dashboards** — Grafana with four provisioned dashboards
  (`config/grafana/dashboards/`).
- **Simulator** — `simulator/mqtt_publisher.py` with scenario YAML files
  (`simulator/scenarios/*.yaml`).

## Repository layout

```text
.
├── architecture.md          # authoritative spec (source of truth)
├── docker-compose.yml
├── .env.example
├── pyproject.toml           # workspace deps + tool config
├── gateway/                 # FastAPI edge gateway
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── logging_config.py
│   │   ├── api/             # health, devices, readings, events, metrics, rules
│   │   ├── db/              # models, session, repositories, timescale helpers
│   │   ├── mqtt/            # aiomqtt client + handlers + topic parser
│   │   ├── schemas/         # Pydantic v2 payload schemas
│   │   ├── services/        # validation, rule engine, ingestion, alert, metrics
│   │   └── workers/         # MQTT consumer, heartbeat, maintenance, alert outbox
│   ├── config/rules.yaml
│   └── tests/               # pytest unit tests
├── config/
│   ├── mosquitto/mosquitto.conf
│   └── grafana/             # provisioning + dashboards
├── database/
│   ├── init.sql             # minimal container bootstrap
│   └── migrations/          # Alembic schema + TimescaleDB setup
├── simulator/
│   ├── mqtt_publisher.py
│   └── scenarios/*.yaml
├── scripts/                 # baseline/proposed test runners + report exporter
└── results/                 # curated reports + ignored raw snapshots
```

## Quickstart

```bash
# 1. copy and adjust env
cp .env.example .env

# 2. start the stack and run migrations
just up

# raw equivalent, if you do not have just installed:
docker compose up -d timescaledb mosquitto grafana
ALEMBIC_DATABASE_URL=postgresql+asyncpg://energy:energy@127.0.0.1:54329/energy_monitoring \
  uv run alembic -c database/migrations/alembic.ini upgrade head
docker compose up -d edge-gateway

# 3. wait for gateway readiness
curl -fsS http://localhost:8001/ready

# 4. build and run the MQTT simulator (one of the built-in scenarios)
docker compose build simulator
docker compose --profile loadtest run --rm simulator

# or run a specific scenario from the host
uv run python simulator/mqtt_publisher.py \
  --host localhost --port 1883 \
  --scenario-file simulator/scenarios/overload.yaml
```

Open:

- Gateway health: <http://localhost:8001/health>
- API docs (Swagger): <http://localhost:8001/docs>
- Grafana: <http://localhost:3001> (admin / admin)

## REST API summary

| Method | Path                                     | Description                       |
| ------ | ---------------------------------------- | --------------------------------- |
| GET    | `/health` / `/ready` / `/version`        | Liveness / readiness / build info |
| GET    | `/api/v1/devices`                        | List registered devices           |
| GET    | `/api/v1/devices/{device_id}`            | One device                        |
| GET    | `/api/v1/devices/{device_id}/status`     | Recent status history             |
| GET    | `/api/v1/readings?device_id=...`         | Recent readings                   |
| GET    | `/api/v1/readings/{device_id}/latest`    | Latest reading                    |
| GET    | `/api/v1/readings/{device_id}/aggregate` | Time-bucketed aggregates          |
| GET    | `/api/v1/events`                         | Filtered events                   |
| GET    | `/api/v1/events/{event_id}`              | One event                         |
| POST   | `/api/v1/events/{event_id}/acknowledge`  | Mark event acknowledged           |
| GET    | `/api/v1/rules`                          | List loaded rules                 |
| GET    | `/api/v1/rules/{rule_name}`              | One rule                          |
| PATCH  | `/api/v1/rules/{rule_name}`              | Toggle enabled flag               |
| POST   | `/api/v1/rules/reload`                   | Reload `rules.yaml`               |
| GET    | `/api/v1/metrics/summary`                | Counters + latencies              |
| GET    | `/api/v1/metrics/throughput`             | Throughput snapshot               |
| GET    | `/api/v1/metrics/data-reduction`         | Data reduction ratio              |
| GET    | `/api/v1/metrics/events-by-severity`     | Events grouped by severity        |
| GET    | `/api/v1/metrics/quality-by-type`        | Validation failures by type       |

## Rule engine

Rules live in `gateway/config/rules.yaml` and can be reloaded at runtime via
`POST /api/v1/rules/reload`. Each rule has a `type` of `threshold` or
`percentage_increase` (plus `heartbeat_timeout` which is handled by the
heartbeat worker). Examples:

```yaml
rules:
  undervoltage:
    enabled: true
    event_type: UNDER_VOLTAGE
    severity: WARNING
    condition:
      type: threshold
      field: voltage_v
      operator: lt
      value: 200
  power_spike:
    enabled: true
    event_type: POWER_SPIKE
    severity: WARNING
    condition:
      type: percentage_increase
      field: power_w
      percent: 30
      window_seconds: 60
```

Supported operators: `lt`, `le`, `gt`, `ge`, `eq`, `ne`.

## Processing modes

Set `PROCESSING_MODE=baseline` or `PROCESSING_MODE=proposed` in `.env`.

- **baseline** — every valid reading is stored; no rule engine runs (this
  matches `Section 14.1` of the architecture doc).
- **proposed** — validate, run the rule engine, apply `STORAGE_POLICY`, store
  events, and enqueue async alerts (matches `Section 14.2`).

Storage policy defaults to `raw` to avoid surprising data loss. Supported
values are `raw`, `hybrid`, `event_only`, and `aggregate_only`; `baseline`
always stores raw readings. Retention defaults keep raw readings, system
metrics, status history, alert deliveries, and completed outbox rows for 30
days, quality logs for 14 days, and events indefinitely.

## Edge ML anomaly detection (Phase 1)

Beyond the rule engine, the gateway can run an unsupervised **Isolation Forest**
anomaly detector at the edge (Phase 1 of a hybrid edge↔cloud direction). It is
disabled by default; enable it with `ENABLE_ML=true`.

```bash
# Train + offline-evaluate the detector (writes models/anomaly_iforest.joblib
# and results/anomaly_model/offline_evaluation.json)
uv run python scripts/train_anomaly_model.py --evaluate

# Online detection A/B: rules-only vs ml-only vs hybrid on labeled anomalies
bash scripts/run_detection_ab_test.sh
```

The detector scores physics-informed features `[voltage_v, current_a, power_w,
temperature_c, |voltage-220|, power - voltage*current]`, writes scores to
`model_predictions`, and (with `ML_EMIT_EVENTS=true`) raises `ML_ANOMALY`
events through the same path as rules. The artifact is mounted read-only into
the gateway at `/app/models`. If ML is off or the artifact is missing, the
detector disables itself and the gateway runs exactly as the rule-based system.

## Thesis validation and experiments

```bash
# 1. check shell experiment scripts parse
UV_CACHE_DIR=/tmp/uv-cache uv run pytest gateway/tests/scripts/test_scripts.py -q

# 2. run the full gateway test suite
UV_CACHE_DIR=/tmp/uv-cache uv run pytest gateway/tests -q

# 3. run clean high-throughput A/B tests
REPETITIONS=3 just ab-high-throughput

# 4. run proposed-mode anomaly detection evidence
just anomaly-detection

# 5. train the edge ML detector and run the detection A/B
uv run python scripts/train_anomaly_model.py --evaluate
bash scripts/run_detection_ab_test.sh
```

Run tests before the Docker experiments so broken scripts or gateway logic fail
quickly. `ab-high-throughput` resets the database for each run and compares
baseline vs proposed using only `high_throughput.yaml`. `anomaly-detection`
resets the database once and runs proposed-mode anomaly scenarios separately for
event-detection evidence.

The older `just baseline` and `just proposed` commands are still available for
single exploratory runs. The thesis-focused outputs are written under
`results/ab/high_throughput/` and `results/anomaly_detection/proposed/`.

## Tests

```bash
just test

# raw equivalent
uv run pytest gateway/tests -q
```

Unit tests cover the validator, rule engine, topic parser, services, workers,
repositories, scripts, and API smoke behavior.

## Extending the system

- Add new event types by appending a rule to `gateway/config/rules.yaml` and
  `POST /api/v1/rules/reload`.
- Drop an additional Grafana dashboard JSON into
  `config/grafana/dashboards/` — provisioning picks it up automatically.
- Plug a new alert channel into `gateway/app/services/alert_service.py`
  (the webhook and Slack clients are already there; add an email
  implementation alongside them by setting `ALERT_SLACK_WEBHOOK_URL`).
- Retrain the edge anomaly detector with
  `uv run python scripts/train_anomaly_model.py --evaluate`; the gateway loads
  the artifact from `/app/models/anomaly_iforest.joblib`.
- Extend `model_predictions` toward forecasting / a cloud tier — the schema and
  the edge scoring path are already in place.
