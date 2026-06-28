set dotenv-load := true

db_url := env("ALEMBIC_DATABASE_URL", "postgresql+asyncpg://energy:energy@127.0.0.1:54329/energy_monitoring")

test:
	uv run pytest gateway/tests -q

lint:
	uv run ruff check .

typecheck:
	uv run ty check gateway

up:
	docker compose up -d timescaledb mosquitto grafana
	DATABASE_URL={{db_url}} uv run alembic -c database/migrations/alembic.ini upgrade head
	docker compose up -d edge-gateway

down:
	docker compose down

migrate:
	DATABASE_URL={{db_url}} uv run alembic -c database/migrations/alembic.ini upgrade head

upgrade revision="head":
	DATABASE_URL={{db_url}} uv run alembic -c database/migrations/alembic.ini upgrade {{revision}}

downgrade revision="-1":
	DATABASE_URL={{db_url}} uv run alembic -c database/migrations/alembic.ini downgrade {{revision}}

baseline:
	bash scripts/run_baseline_test.sh

proposed:
	bash scripts/run_proposed_test.sh

export-baseline:
	python3 scripts/export_results.py --base-url http://localhost:8001 --output-dir results/baseline

export-proposed:
	python3 scripts/export_results.py --base-url http://localhost:8001 --output-dir results/proposed

eval: baseline proposed
