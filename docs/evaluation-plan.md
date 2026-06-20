# Evaluation Plan

Reproduce the comparison described in `architecture.md` Section 14.

## Metrics collected

1. **End-to-end latency** — `event.time - device.timestamp` for events
   with a `reading_time` set.
2. **Event detection latency** — `event.created_at - reading.time` (logged
   in `system_metrics` via `latency.telemetry`).
3. **Alert latency** — `alert_deliveries.sent_at - event.created_at`.
4. **Throughput** — `messages.received` / uptime (see `/api/v1/metrics/throughput`).
5. **Validation failure rate** — `validation.failures / messages.received`.
6. **Data reduction ratio** — `1 - total_events / raw_readings_stored`
   (see `/api/v1/metrics/data-reduction`).
7. **Storage growth** — `pg_database_size('energy_monitoring')` sampled
   before/after a fixed load.

## Procedure

1. Bring the stack up in baseline mode:

   ```bash
   PROCESSING_MODE=baseline \
     STORE_RAW_READINGS=true \
     ENABLE_RULE_ENGINE=false \
     ENABLE_ALERTS=false \
     docker compose up -d --build
   ```

2. Run the `high_throughput.yaml` scenario (200 devices × 1s × 120s):

   ```bash
   uv run python simulator/mqtt_publisher.py \
     --host localhost --port 1883 \
     --scenario-file simulator/scenarios/high_throughput.yaml
   ```

3. Snapshot baseline metrics:

   ```bash
   python scripts/export_results.py --output-dir results/baseline
   psql -h localhost -U energy -d energy_monitoring \
     -c "SELECT pg_database_size('energy_monitoring') AS bytes;"
   ```

4. Stop the gateway, change `PROCESSING_MODE=proposed` and re-run with
   the same scenario. Snapshot again into `results/proposed/`.

5. Repeat with anomaly scenarios (`undervoltage`, `overload`, `power_spike`,
   `invalid_payloads`) to populate events.

## Outputs

- `results/{baseline,proposed}/snapshot.json` — raw counters/latencies.
- `results/{baseline,proposed}/report.md` — human-readable summary.
- (Optional) export `system_metrics` and `events` tables to CSV for
  plotting in the thesis.

## Acceptance criteria

A run is acceptable when:

- The baseline scenario records `readings.stored == messages.received`.
- The proposed scenario records `events.critical > 0` and
  `events.warning > 0` when anomaly scenarios are run.
- The data reduction ratio in proposed mode is `> 0.5` for the
  `high_throughput.yaml` scenario (every overload event replaces many
  stored rows in dashboard view).
- Validation failure rate matches the configured `invalid_payload_ratio`.
