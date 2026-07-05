#!/usr/bin/env bash
# Cloud verification experiment (Phase 3): run the pipeline in gated mode with
# the cloud-tier LSTM-AE verifier active, drive the labeled anomaly scenarios,
# and capture how the cloud confirms or suppresses the readings the edge
# escalated. This measures the online behaviour of the two-stage detector; the
# offline detection quality is produced by scripts/train_cloud_lstm.py.
#
# Requires both model artifacts:
#   uv run python scripts/train_anomaly_model.py --evaluate
#   uv run --group ml-train python scripts/train_cloud_lstm.py --evaluate
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"
OUT_DIR="${OUTPUT_DIR:-${ROOT}/results/cloud_verification}"

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

cd "${ROOT}"

for artifact in models/anomaly_iforest.joblib models/cloud_lstm_ae.npz; do
  if [[ ! -f "${ROOT}/${artifact}" ]]; then
    echo "Model artifact missing: ${artifact}" >&2
    exit 1
  fi
done

wait_for_service() {
  local name="$1" url="$2"
  echo "Waiting for ${name} to be ready..."
  for _ in {1..30}; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "${name} ready."
      return 0
    fi
    sleep 2
  done
  echo "${name} did not become ready in time." >&2
  return 1
}

run_scenario() {
  local label="$1" file="$2"
  echo "  scenario: ${label}"
  docker compose run --rm simulator \
    python mqtt_publisher.py --scenario-file "${file}" \
    | tee "${OUT_DIR}/${label}.simulator.log"
}

mkdir -p "${OUT_DIR}"
docker compose build edge-gateway cloud-tier

echo "=================================================="
echo "Phase 3: cloud verification (gated mode + LSTM-AE)"
echo "=================================================="
docker compose down -v

export PROCESSING_MODE=proposed
export STORE_RAW_READINGS=true
export ENABLE_AGGREGATION=true
export ENABLE_ALERTS=true
export ENABLE_RULE_ENGINE=true
export ENABLE_ML=true
export ML_EMIT_EVENTS=true
export ML_ASYNC_SCORING=true
export CLOUD_FORWARD_MODE=gated

docker compose up -d timescaledb mosquitto cloud-tier
wait_for_timescaledb
run_migrations
docker compose up -d edge-gateway
wait_for_service "edge gateway" http://localhost:8001/ready
wait_for_service "cloud tier" http://localhost:8002/health

run_scenario "undervoltage" /app/scenarios/undervoltage.yaml
run_scenario "overload"     /app/scenarios/overload.yaml
run_scenario "power_spike"  /app/scenarios/power_spike.yaml

# Let the forwarder flush and the verifier drain its windows.
sleep 5

echo "Capturing cloud verification evidence..."
curl -s http://localhost:8001/api/v1/metrics/summary \
  | python3 -m json.tool | tee "${OUT_DIR}/gateway-metrics.json"
curl -s http://localhost:8002/api/v1/metrics/summary \
  | python3 -m json.tool | tee "${OUT_DIR}/cloud-metrics.json"
curl -s "http://localhost:8002/api/v1/verdicts/recent?limit=50" \
  | python3 -m json.tool > "${OUT_DIR}/cloud-verdicts.json"

docker compose stop edge-gateway cloud-tier

echo "Phase 3 cloud verification complete. Results under ${OUT_DIR}"
