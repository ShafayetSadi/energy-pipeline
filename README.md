# Energy Pipeline

## Load testing

Run the backend first:

```bash
docker compose up --build
```

Then run the controlled experiments:

```bash
python3 experiments/run_load_experiments.py
```

This executes four profiles against `http://localhost:8001/data`:

- `100` devices at `1s`
- `300` devices at `1s`
- `500` devices at `1s`
- `1000` devices at `1s`

Artifacts are written to `experiments/results/`:

- one raw `.log` file per run
- one `.json` summary per run
- `summary.md` with requests/sec, response time, and failures

## Request timing metrics

The backend now records one CSV row per request with:

- `timestamp`
- `method`
- `path`
- `status_code`
- `processing_time_ms`
- `db_execute_ms`
- `db_commit_ms`
- `total_handler_ms`

When you run with Docker Compose, the file is written to:

```bash
runtime/request_metrics.csv
```

Start the stack and generate traffic:

```bash
docker compose up --build -d
python3 experiments/run_load_experiments.py
```

Inspect the newest timing rows:

```bash
tail -n 20 runtime/request_metrics.csv
```

Use the DB timing columns to identify whether the bottleneck is in statement execution or commit latency under load.
