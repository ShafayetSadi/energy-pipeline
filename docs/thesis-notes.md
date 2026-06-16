# Thesis Notes

Working notes for the dissertation accompanying this implementation.

## Chapter mapping

| Chapter | Material in this repo                                      |
| ------- | ---------------------------------------------------------- |
| 3. Architecture | `docs/architecture.md`                                  |
| 4. Implementation | `gateway/`, `simulator/`, `config/`, `database/`         |
| 5. Evaluation | `scripts/`, `docs/evaluation-plan.md`, `results/`         |
| 6. Results | exported snapshots + Grafana screenshots                  |
| 7. Conclusion | future AI/ML hooks: `model_predictions` table, hook points in `gateway/app/services/` |

## Key design decisions

- **Why TimescaleDB over raw PostgreSQL.** Continuous aggregates make the
  dashboard panels fast at 1-minute / 5-minute granularity without separate
  rollup jobs.
- **Why `aiomqtt`.** Native asyncio, no callback-based paho bridge.
- **Why a rule engine before storage.** This is the central thesis
  contribution: storage growth is reduced and event detection latency is
  bounded by MQTT round-trip + rule eval (sub-50ms in the test scenarios).
- **Why `rule_definitions` table even though rules are file-based.** Provides
  a future API path to override the file without losing existing rule state.

## What is intentionally out of scope (per `architecture.md` §2.3)

- Real AI/ML anomaly detection.
- TLS-secured MQTT and per-device credentials.
- Production-grade electrical safety certification.
- Cloud / Kubernetes deployment.

## Future work hooks

- `model_predictions` table exists but is unused in v1.
- `AlertService` already supports a webhook channel; Slack/email are
  drop-in additions.
- The rule engine exposes a `reload()` API and a DB-backed
  `rule_definitions` table, so future per-rule UI work has a path.
