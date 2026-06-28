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

1. Bring the stack up in baseline mode and run the baseline scenario:

   ```bash
   just baseline
   ```

2. The script starts TimescaleDB/Mosquitto/Grafana, runs Alembic migrations,
   starts the gateway, runs `high_throughput.yaml`, and exports
   `results/baseline/report.md` automatically.

3. Optionally snapshot database size:

   ```bash
   psql -h localhost -U energy -d energy_monitoring \
     -c "SELECT pg_database_size('energy_monitoring') AS bytes;"
   ```

4. Re-run in proposed mode:

   ```bash
   just proposed
   ```

5. Repeat with anomaly scenarios (`undervoltage`, `overload`, `power_spike`,
   `invalid_payloads`) to populate events. The proposed script already runs
   these scenarios before exporting `results/proposed/report.md`.

## Outputs

- `results/{baseline,proposed}/report.md` — human-readable summary, tracked.
- `results/{baseline,proposed}/snapshot.json` — raw counters/latencies,
  generated locally and ignored by git.
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
