#!/usr/bin/env bash
# Detection A/B: compare rule-based vs ML (Isolation Forest) vs hybrid detection
# on the same labeled anomaly scenarios. Captures detection counts, ML scores,
# latency (including ML inference), and database growth per mode.
#
# Requires a trained model artifact at models/anomaly_iforest.joblib:
#   uv run python scripts/train_anomaly_model.py --evaluate
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"
BASE_OUTPUT="${OUTPUT_DIR:-${ROOT}/results/detection_ab}"

cd "${ROOT}"

if [[ ! -f "${ROOT}/models/anomaly_iforest.joblib" ]]; then
  echo "Model artifact missing. Run: uv run python scripts/train_anomaly_model.py --evaluate" >&2
  exit 1
fi

run_migrations() {
  DATABASE_URL="${ALEMBIC_DATABASE_URL:-postgresql+asyncpg://energy:energy@127.0.0.1:54329/energy_monitoring}" \
    uv run alembic -c database/migrations/alembic.ini upgrade head
}

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
  local out_dir="$1" label="$2" sql="$3"
  docker compose exec -T timescaledb \
    psql -U energy -d energy_monitoring -c "${sql}" \
    | tee "${out_dir}/${label}.txt"
}

run_scenario() {
  local out_dir="$1" label="$2" file="$3"
  echo "  scenario: ${label}"
  docker compose run --rm simulator \
    python mqtt_publisher.py --scenario-file "${file}" \
    | tee "${out_dir}/${label}.simulator.log"
}

run_mode() {
  local mode="$1"
  local out_dir="${BASE_OUTPUT}/${mode}"
  mkdir -p "${out_dir}"

  echo "=================================================="
  echo "Detection mode: ${mode}"
  echo "=================================================="
  docker compose down -v

  export PROCESSING_MODE=proposed
  export STORE_RAW_READINGS=true
  export ENABLE_AGGREGATION=true
  export ENABLE_ALERTS=true
  case "${mode}" in
    rules)  export ENABLE_RULE_ENGINE=true  ENABLE_ML=false ML_EMIT_EVENTS=false ;;
    ml)     export ENABLE_RULE_ENGINE=false ENABLE_ML=true  ML_EMIT_EVENTS=true ;;
    hybrid) export ENABLE_RULE_ENGINE=true  ENABLE_ML=true  ML_EMIT_EVENTS=true ;;
    *) echo "unknown mode ${mode}" >&2; return 1 ;;
  esac

  docker compose up -d timescaledb mosquitto grafana
  run_migrations
  docker compose up -d edge-gateway
  wait_for_gateway

  capture_sql "${out_dir}" "db-size-before" \
    "SELECT pg_database_size('energy_monitoring') AS bytes_before;"

  run_scenario "${out_dir}" "undervoltage" /app/scenarios/undervoltage.yaml
  run_scenario "${out_dir}" "overload"     /app/scenarios/overload.yaml
  run_scenario "${out_dir}" "power_spike"  /app/scenarios/power_spike.yaml

  echo "Capturing detection evidence for mode ${mode}..."
  curl -s http://localhost:8001/api/v1/metrics/summary \
    | python3 -m json.tool | tee "${out_dir}/metrics-summary.json"

  capture_sql "${out_dir}" "events-by-type" \
    "SELECT event_type, severity, count(*) FROM events GROUP BY event_type, severity ORDER BY event_type;"
  capture_sql "${out_dir}" "predictions-by-label" \
    "SELECT predicted_label, count(*) FROM model_predictions GROUP BY predicted_label ORDER BY predicted_label;"
  capture_sql "${out_dir}" "prediction-score-stats" \
    "SELECT count(*) AS n, round(avg(anomaly_score)::numeric,4) AS avg_score, round(max(anomaly_score)::numeric,4) AS max_score FROM model_predictions;"
  capture_sql "${out_dir}" "db-size-after" \
    "SELECT pg_database_size('energy_monitoring') AS bytes_after;"

  python3 "${SCRIPT_DIR}/export_results.py" \
    --base-url http://localhost:8001 --output-dir "${out_dir}"

  docker compose stop edge-gateway
}

mkdir -p "${BASE_OUTPUT}"
# Rebuild so the gateway image matches the working tree (app code is baked
# into the image; only config/ and models/ are bind-mounted).
docker compose build edge-gateway
for mode in rules ml hybrid; do
  run_mode "${mode}"
done

echo "Detection A/B complete. Results under ${BASE_OUTPUT}/{rules,ml,hybrid}"
