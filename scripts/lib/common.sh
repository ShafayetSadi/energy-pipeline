#!/usr/bin/env bash

run_migrations() {
  DATABASE_URL="${ALEMBIC_DATABASE_URL:-postgresql+asyncpg://energy:energy@127.0.0.1:54329/energy_monitoring}" \
    uv run alembic -c database/migrations/alembic.ini upgrade head
}

wait_for_timescaledb() {
  echo "Waiting for timescaledb to be ready..."
  for _ in {1..30}; do
    if docker compose exec -T timescaledb \
      pg_isready -U energy -d energy_monitoring >/dev/null 2>&1; then
      echo "timescaledb ready."
      return 0
    fi
    sleep 2
  done
  echo "timescaledb did not become ready in time." >&2
  return 1
}
