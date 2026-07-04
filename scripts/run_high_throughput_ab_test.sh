#!/usr/bin/env bash
# Run clean baseline/proposed A/B tests using the same high-throughput scenario.
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"
REPETITIONS="${REPETITIONS:-3}"
SCENARIO_FILE="${SCENARIO_FILE:-/app/scenarios/high_throughput.yaml}"
BASE_OUTPUT_DIR="${BASE_OUTPUT_DIR:-${ROOT}/results/ab/high_throughput}"

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

run_single() {
  local mode="$1"
  local iteration="$2"
  local output_dir="${BASE_OUTPUT_DIR}/${mode}/run-${iteration}"

  echo "============================================================"
  echo "A/B run ${iteration}/${REPETITIONS}: mode=${mode}"
  echo "Output: ${output_dir}"
  echo "============================================================"

  # Reset the database volume for isolated DB-backed counts and storage metrics.
  docker compose down -v

  if [[ "${mode}" == "baseline" ]]; then
    export PROCESSING_MODE=baseline
    export STORE_RAW_READINGS=true
    export ENABLE_RULE_ENGINE=false
    export ENABLE_AGGREGATION=false
    export ENABLE_ALERTS=false
  elif [[ "${mode}" == "proposed" ]]; then
    export PROCESSING_MODE=proposed
    export STORE_RAW_READINGS=true
    export ENABLE_RULE_ENGINE=true
    export ENABLE_AGGREGATION=true
    export ENABLE_ALERTS=true
  else
    echo "Unknown mode: ${mode}" >&2
    return 2
  fi

  docker compose up -d timescaledb mosquitto grafana
  echo "Running database migrations..."
  wait_for_timescaledb
  run_migrations
  docker compose up -d edge-gateway
  wait_for_gateway

  mkdir -p "${output_dir}"

  echo "Capturing database size before scenario..."
  docker compose exec -T timescaledb \
    psql -U energy -d energy_monitoring \
      -c "SELECT pg_database_size('energy_monitoring') AS bytes_before;" \
      | tee "${output_dir}/db-size-before.txt"

  echo "Running high-throughput scenario only..."
  docker compose run --rm simulator \
    python mqtt_publisher.py --scenario-file "${SCENARIO_FILE}" \
    | tee "${output_dir}/simulator.log"

  echo "Capturing database size after scenario..."
  docker compose exec -T timescaledb \
    psql -U energy -d energy_monitoring \
      -c "SELECT pg_database_size('energy_monitoring') AS bytes_after;" \
      | tee "${output_dir}/db-size-after.txt"

  echo "Exporting run metrics..."
  python3 "${SCRIPT_DIR}/export_results.py" \
    --base-url http://localhost:8001 \
    --output-dir "${output_dir}"

  echo "Stopping gateway..."
  docker compose stop edge-gateway
}

for i in $(seq 1 "${REPETITIONS}"); do
  run_single baseline "${i}"
  run_single proposed "${i}"
done

echo "A/B high-throughput test complete."
echo "Results written under ${BASE_OUTPUT_DIR}"
