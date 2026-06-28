#!/usr/bin/env bash
# Run the baseline test: gateway in baseline mode + heavy load.
set -euo pipefail
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"

cd "${ROOT}"

echo "Restarting stack in baseline mode..."
export PROCESSING_MODE=baseline
export STORE_RAW_READINGS=true
export ENABLE_RULE_ENGINE=false
export ENABLE_AGGREGATION=false
export ENABLE_ALERTS=false

docker compose up -d timescaledb mosquitto edge-gateway grafana
echo "Waiting for edge gateway to be ready..."
for i in {1..30}; do
  if curl -fsS http://localhost:8001/ready >/dev/null 2>&1; then
    echo "Gateway ready."
    break
  fi
  sleep 2
done

echo "Running high-throughput scenario for 60s..."
docker compose run --rm simulator \
  python mqtt_publisher.py --scenario-file /app/scenarios/high_throughput.yaml

echo "Snapshotting DB size..."
docker compose exec -T timescaledb \
  psql -U energy -d energy_monitoring -c "SELECT count(*) AS readings FROM energy_readings;"

echo "Exporting baseline metrics (before in-memory counters are lost)..."
python3 "${SCRIPT_DIR}/export_results.py" \
  --base-url http://localhost:8001 \
  --output-dir "${ROOT}/results/baseline"

echo "Stopping gateway..."
docker compose stop edge-gateway
