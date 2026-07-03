#!/usr/bin/env bash
# Escalation bandwidth A/B (Phase 2): compare score-gated edge->cloud
# forwarding ("gated") against the naive all-to-cloud baseline ("all") on the
# same labeled anomaly scenarios. Both modes run the identical pipeline
# (rules + async ML scoring + cloud forwarding); the escalation gate is the
# only variable. Captures forwarded reading counts and payload bytes on both
# the gateway (sent) and cloud tier (received) sides.
#
# Requires a trained model artifact at models/anomaly_iforest.joblib:
#   uv run python scripts/train_anomaly_model.py --evaluate
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT="$( cd "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd )"
BASE_OUTPUT="${OUTPUT_DIR:-${ROOT}/results/escalation_bandwidth}"

cd "${ROOT}"

if [[ ! -f "${ROOT}/models/anomaly_iforest.joblib" ]]; then
  echo "Model artifact missing. Run: uv run python scripts/train_anomaly_model.py --evaluate" >&2
  exit 1
fi

run_migrations() {
  DATABASE_URL="${ALEMBIC_DATABASE_URL:-postgresql+asyncpg://energy:energy@127.0.0.1:54329/energy_monitoring}" \
    uv run alembic -c database/migrations/alembic.ini upgrade head
}

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
  echo "Cloud forward mode: ${mode}"
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
  export CLOUD_FORWARD_MODE="${mode}"

  docker compose up -d timescaledb mosquitto cloud-tier
  run_migrations
  docker compose up -d edge-gateway
  wait_for_service "edge gateway" http://localhost:8001/ready
  wait_for_service "cloud tier" http://localhost:8002/health

  run_scenario "${out_dir}" "undervoltage" /app/scenarios/undervoltage.yaml
  run_scenario "${out_dir}" "overload"     /app/scenarios/overload.yaml
  run_scenario "${out_dir}" "power_spike"  /app/scenarios/power_spike.yaml

  # Give the forwarder's batch window time to flush the tail.
  sleep 5

  echo "Capturing escalation evidence for mode ${mode}..."
  curl -s http://localhost:8001/api/v1/metrics/summary \
    | python3 -m json.tool | tee "${out_dir}/gateway-metrics.json"
  curl -s http://localhost:8002/api/v1/metrics/summary \
    | python3 -m json.tool | tee "${out_dir}/cloud-metrics.json"
  curl -s "http://localhost:8002/api/v1/escalations/recent?limit=20" \
    | python3 -m json.tool > "${out_dir}/cloud-recent-escalations.json"

  docker compose stop edge-gateway cloud-tier
}

summarize() {
  python3 - "$BASE_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

base = Path(sys.argv[1])
rows = {}
for mode in ("gated", "all"):
    gw = json.loads((base / mode / "gateway-metrics.json").read_text())
    cloud = json.loads((base / mode / "cloud-metrics.json").read_text())
    g, c = gw["counters"], cloud["counters"]
    rows[mode] = {
        "readings_scored": g.get("ml.scored", 0),
        "readings_forwarded": g.get("cloud.forwarded", 0),
        "batches_sent": g.get("cloud.batches", 0),
        "bytes_sent": g.get("cloud.bytes_sent", 0),
        "forward_failures": g.get("cloud.forward_failed", 0),
        "cloud_readings_received": c.get("escalations.readings", 0),
        "cloud_bytes_received": c.get("escalations.bytes_received", 0),
    }

gated, full = rows["gated"], rows["all"]
summary = {
    "modes": rows,
    "bandwidth_reduction": {
        "bytes_sent_gated": gated["bytes_sent"],
        "bytes_sent_all": full["bytes_sent"],
        "bytes_reduction_pct": round(
            100.0 * (1 - gated["bytes_sent"] / full["bytes_sent"]), 2
        )
        if full["bytes_sent"]
        else None,
        "readings_forwarded_gated": gated["readings_forwarded"],
        "readings_forwarded_all": full["readings_forwarded"],
        "readings_reduction_pct": round(
            100.0 * (1 - gated["readings_forwarded"] / full["readings_forwarded"]), 2
        )
        if full["readings_forwarded"]
        else None,
    },
}
out = base / "bandwidth-summary.json"
out.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
print(f"Wrote {out}")
PY
}

mkdir -p "${BASE_OUTPUT}"
# Rebuild so both images match the working tree (app code is baked into the
# images; only config/ and models/ are bind-mounted into the gateway).
docker compose build edge-gateway cloud-tier
for mode in gated all; do
  run_mode "${mode}"
done
summarize

echo "Escalation bandwidth A/B complete. Results under ${BASE_OUTPUT}/{gated,all}"
