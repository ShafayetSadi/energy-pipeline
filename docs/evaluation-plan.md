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
6. **Event detection counts** — event totals grouped by severity and event type.
7. **Storage optimization readiness** — document the current raw-storage behavior
   and identify selective retention/downsampling as future work, not as a
   measured thesis result.

## Procedure

1. Bring the stack up in baseline mode and run the baseline scenario:

   ```bash
   just baseline
   ```

2. The script starts TimescaleDB/Mosquitto/Grafana, runs Alembic migrations,
   starts the gateway, runs `high_throughput.yaml`, and exports
   `results/baseline/report.md` automatically.

3. Re-run in proposed mode:

   ```bash
   just proposed
   ```

4. Repeat with anomaly scenarios (`undervoltage`, `overload`, `power_spike`,
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
- Validation failure rate matches the configured `invalid_payload_ratio`.

## Storage reduction scope

Storage reduction is intentionally not treated as a final measured result in
the current thesis version. Both baseline and proposed runs keep
`STORE_RAW_READINGS=true`, so a fair storage-reduction claim would require a
separate implementation and experiment using selective raw-data retention,
downsampling, or event-only long-term storage. This remains future work.
