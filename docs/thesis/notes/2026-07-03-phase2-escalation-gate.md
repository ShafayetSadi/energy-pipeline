# Phase 2: Score-Gated Edge→Cloud Escalation + Bandwidth A/B

Date: 2026-07-03

## What was implemented

- `gateway/app/workers/cloud_forwarder.py` — `CloudForwarderWorker`. Applies
  the escalation gate (`CLOUD_FORWARD_MODE`: `off` default / `gated` / `all`),
  queues escalated readings, batches them (`CLOUD_FORWARD_BATCH_MAX_SIZE`=64,
  `CLOUD_FORWARD_BATCH_WINDOW_MS`=1000), and POSTs a compact JSON envelope to
  the cloud tier. Counts `cloud.forwarded`, `cloud.batches`,
  `cloud.bytes_sent`, `cloud.dropped`, `cloud.forward_failed`; records a
  `cloud_forward` latency series. Failures are counted and dropped (no retry):
  edge detection never depends on cloud reachability.
- Gate semantics: `gated` escalates readings where `is_anomaly` (score above
  the model's own threshold), or above `CLOUD_ESCALATION_THRESHOLD` if that
  override is set; `all` escalates every scored reading — the naive
  all-to-cloud baseline for the bandwidth A/B. Same pipeline in both modes, so
  the gate is the only variable.
- Hook: `MLScoringWorker._process_batch` offers every scored reading to the
  forwarder (counter `cloud.escalation_candidates`). Forwarding therefore
  requires `ENABLE_ML=true` and async scoring — the scoring worker's queue is
  the substrate, as planned in Phase 1.
- `cloud/app/main.py` — minimal FastAPI cloud-tier receiver (`cloud-tier` in
  compose, port 8002). Validates the envelope, counts batches/readings/bytes
  received (exposed at `/api/v1/metrics/summary`), keeps a bounded in-memory
  buffer of recent escalations (`/api/v1/escalations/recent`). Persists
  nothing; hosts no model (that is Phase 3).
- `scripts/run_escalation_bandwidth_test.sh` — gated-vs-all A/B over the same
  labeled scenarios as the detection A/B; writes
  `results/escalation_bandwidth/{gated,all}/` plus a computed
  `bandwidth-summary.json` (byte + reading reduction percentages). Builds both
  images first (lesson from the stale-image incident).
- Tests: `gateway/tests/workers/test_cloud_forwarder.py` — gate semantics per
  mode, threshold override, invalid-mode rejection, batch forwarding with byte
  counting (httpx MockTransport), failure counted-not-raised. Suite: 57 pass.

## Envelope

```json
{"source": "edge-gateway", "mode": "gated", "readings": [
  {"device_id": "...", "timestamp": "...", "reading_time": "...",
   "voltage_v": 0, "current_a": 0, "power_w": 0, "temperature_c": 0,
   "anomaly_score": 0, "threshold": 0, "model_version": "iforest_v1",
   "rule_fired": false}]}
```

Bytes are counted on both sides (gateway `cloud.bytes_sent`, cloud
`escalations.bytes_received`); the totals must match for a run to be valid.
Measured quantity is application-payload bytes, not wire-level bytes — the
honest comparison statistic is the gated/all payload ratio.

## Smoke verification (2026-07-03)

Live stack, `CLOUD_FORWARD_MODE=gated`: 10 normal readings scored, 0
escalated; 5 overvoltage readings (262 V, score 0.612 > threshold 0.545) all
escalated in 2 batches, 1,581 bytes sent = 1,581 bytes received, envelope
fields correct, `cloud_forward` ~2 ms per batch. Incidental observation: a
152 V undervoltage reading scored 0.5437 — just under the 0.5449 threshold —
a live example of the ~17% undervoltage miss rate from the offline evaluation.

## Pending

Run the bandwidth A/B and fill Section 6.7.2:

```bash
bash scripts/run_escalation_bandwidth_test.sh
```

Expected shape (not claimed until measured): gated volume tracks the model
flag rate (~7% of readings in these scenarios) rather than the full stream.

## Next phases

3. Cloud-tier LSTM failure prediction / forecasting on the escalated stream.
4. Storage optimization (selective retention / downsampling).
