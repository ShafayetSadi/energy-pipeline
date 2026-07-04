#!/usr/bin/env bash
# Run proposed-mode anomaly scenarios as a standalone detection experiment.
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT}/results/anomaly_detection/proposed}"

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

cd "${ROOT}"

wait_for_gateway() {
  echo "Waiting for edge gateway to be ready..."
  for _ in {1..30}; do
    if curl -fsS http://localhost:8001/ready >/dev/null 2>&1; then
      echo "Gateway ready."
      return 0
    fi
    sleep 2
  done

  echo "Gateway did not become ready in time." >&2
  return 1
}

capture_sql() {
  local label="$1"
  local sql="$2"
  docker compose exec -T timescaledb \
    psql -U energy -d energy_monitoring -c "${sql}" \
    | tee "${OUTPUT_DIR}/${label}.txt"
}

run_scenario() {
  local label="$1"
  local file="$2"

  echo "Running anomaly scenario: ${label}"
  docker compose run --rm simulator \
    python mqtt_publisher.py --scenario-file "${file}" \
    | tee "${OUTPUT_DIR}/${label}.simulator.log"
}

echo "Resetting stack for proposed-mode anomaly detection experiment..."
docker compose down -v

export PROCESSING_MODE=proposed
export STORE_RAW_READINGS=true
export ENABLE_RULE_ENGINE=true
export ENABLE_AGGREGATION=true
export ENABLE_ALERTS=true

docker compose up -d timescaledb mosquitto grafana
echo "Running database migrations..."
wait_for_timescaledb
run_migrations
docker compose up -d edge-gateway
wait_for_gateway

mkdir -p "${OUTPUT_DIR}"

capture_sql "db-size-before" "SELECT pg_database_size('energy_monitoring') AS bytes_before;"

run_scenario "undervoltage" /app/scenarios/undervoltage.yaml
run_scenario "overload" /app/scenarios/overload.yaml
run_scenario "power_spike" /app/scenarios/power_spike.yaml
run_scenario "invalid_payloads" /app/scenarios/invalid_payloads.yaml

echo "Capturing anomaly detection evidence..."
curl -s http://localhost:8001/api/v1/metrics/summary \
  | python3 -m json.tool \
  | tee "${OUTPUT_DIR}/metrics-summary.json"

capture_sql "events-by-severity" \
  "SELECT severity, count(*) FROM events GROUP BY severity ORDER BY severity;"

capture_sql "events-by-type" \
  "SELECT event_type, severity, count(*) FROM events GROUP BY event_type, severity ORDER BY event_type, severity;"

capture_sql "validation-errors-by-type" \
  "SELECT error_type, count(*) FROM data_quality_logs GROUP BY error_type ORDER BY error_type;"

capture_sql "db-size-after" "SELECT pg_database_size('energy_monitoring') AS bytes_after;"

echo "Exporting proposed anomaly report..."
python3 "${SCRIPT_DIR}/export_results.py" \
  --base-url http://localhost:8001 \
  --output-dir "${OUTPUT_DIR}"

echo "Stopping gateway..."
docker compose stop edge-gateway

echo "Anomaly detection experiment complete."
echo "Results written under ${OUTPUT_DIR}"
