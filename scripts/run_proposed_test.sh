#!/usr/bin/env bash
# Run the proposed test: gateway in proposed mode with rule engine + alerts.
set -euo pipefail
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"

cd "${ROOT}"

echo "Restarting stack in proposed mode..."
export PROCESSING_MODE=proposed
export STORE_RAW_READINGS=true
export ENABLE_RULE_ENGINE=true
export ENABLE_AGGREGATION=true
export ENABLE_ALERTS=true

docker compose up -d timescaledb mosquitto grafana
echo "Running database migrations..."
DATABASE_URL="${ALEMBIC_DATABASE_URL:-postgresql+asyncpg://energy:energy@127.0.0.1:54329/energy_monitoring}" \
  uv run alembic -c database/migrations/alembic.ini upgrade head
docker compose up -d edge-gateway
echo "Waiting for edge gateway to be ready..."
for i in {1..30}; do
  if curl -fsS http://localhost:8001/ready >/dev/null 2>&1; then
    echo "Gateway ready."
    break
  fi
  sleep 2
done

echo "Running mixed scenarios..."
docker compose run --rm simulator \
  python mqtt_publisher.py --scenario-file /app/scenarios/undervoltage.yaml
docker compose run --rm simulator \
  python mqtt_publisher.py --scenario-file /app/scenarios/overload.yaml
docker compose run --rm simulator \
  python mqtt_publisher.py --scenario-file /app/scenarios/power_spike.yaml
docker compose run --rm simulator \
  python mqtt_publisher.py --scenario-file /app/scenarios/invalid_payloads.yaml
docker compose run --rm simulator \
  python mqtt_publisher.py --scenario-file /app/scenarios/high_throughput.yaml

echo "Snapshotting counts..."
docker compose exec -T timescaledb \
  psql -U energy -d energy_monitoring -c "SELECT severity, count(*) FROM events GROUP BY severity;"

echo "Snapshotting metric counters..."
curl -s http://localhost:8001/api/v1/metrics/summary | python -m json.tool

echo "Exporting proposed metrics (before in-memory counters are lost)..."
python3 "${SCRIPT_DIR}/export_results.py" \
  --base-url http://localhost:8001 \
  --output-dir "${ROOT}/results/proposed"

echo "Stopping gateway..."
docker compose stop edge-gateway
