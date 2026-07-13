set dotenv-load := true

db_url := env("ALEMBIC_DATABASE_URL", "postgresql+asyncpg://energy:energy@127.0.0.1:54329/energy_monitoring")

test:
	uv run pytest gateway/tests cloud/tests -q

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

ab-high-throughput:
	bash scripts/run_high_throughput_ab_test.sh

anomaly-detection:
	bash scripts/run_anomaly_detection_test.sh

export-baseline:
	python3 scripts/export_results.py --base-url http://localhost:8001 --output-dir results/baseline

export-proposed:
	python3 scripts/export_results.py --base-url http://localhost:8001 --output-dir results/proposed

eval: baseline proposed

# Regenerate the thesis result figures (PDF + PNG) from pinned results/ JSONs.
figures:
	uv run --with matplotlib python scripts/make_thesis_figures.py

# Build the thesis PDF from the chapter markdown with pandoc-crossref
# (auto-numbers figures and resolves [@fig:...] cross-references). Depends on
# the figures existing under results/figures/ — run `just figures` first.
# Requires pandoc, pandoc-crossref, and a LaTeX engine (xelatex) on PATH.
thesis-pdf: figures
	pandoc docs/thesis/0[1-7]_*.md \
		--from markdown --resource-path=.:docs/thesis \
		--filter pandoc-crossref --citeproc \
		--pdf-engine=xelatex --number-sections \
		-V mainfont="TeX Gyre Termes" \
		-V mathfont="TeX Gyre Termes Math" \
		-M figureTitle=Figure -M figPrefix=fig. \
		-o results/thesis.pdf
	@echo "Wrote results/thesis.pdf"
