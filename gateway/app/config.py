"""Edge gateway configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the edge gateway."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    service_name: str = "edge-gateway"
    service_version: str = "0.1.0"

    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_client_id: str = "edge-gateway"
    mqtt_keepalive: int = 60
    mqtt_telemetry_topic: str = "energy/+/telemetry"
    mqtt_status_topic: str = "energy/+/status"
    mqtt_events_topic: str = "energy/+/events"
    mqtt_qos_telemetry: int = 0
    mqtt_qos_status: int = 1
    mqtt_qos_events: int = 1

    database_url: str = (
        "postgresql+asyncpg://energy:energy@localhost:5432/energy_monitoring"
    )
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_echo: bool = False
    enable_timescale: bool = True

    processing_mode: str = "proposed"
    storage_policy: str = "raw"
    store_raw_readings: bool = True
    enable_rule_engine: bool = True
    enable_aggregation: bool = True
    enable_alerts: bool = True
    enable_ml: bool = False

    # Edge ML anomaly detection (Phase 1: Isolation Forest at the edge).
    ml_model_path: str = "/app/models/anomaly_iforest.joblib"
    ml_model_version: str = "iforest_v1"
    ml_features: str = "voltage_v,current_a,power_w,temperature_c"
    # Anomaly score above this flags a reading. Empty -> use threshold baked
    # into the model artifact at training time.
    ml_score_threshold: float | None = None
    # When true, ML anomalies are written to the events table (hybrid/ml-only
    # detection). When false, scores are still written to model_predictions but
    # no event is generated (silent scoring).
    ml_emit_events: bool = False
    ml_event_type: str = "ML_ANOMALY"
    ml_event_severity: str = "WARNING"
    # Score readings in an async micro-batch worker (off the ingestion hot path)
    # rather than inline per message. Batching amortizes scikit-learn's
    # per-call overhead. Set false to score inline (for inline-vs-batched A/B).
    ml_async_scoring: bool = True
    ml_batch_max_size: int = 128
    ml_batch_window_ms: int = 50
    ml_queue_max_size: int = 20000

    # Edge->cloud escalation (Phase 2). Scored readings can be forwarded to a
    # cloud tier: "off" forwards nothing, "gated" forwards only readings whose
    # anomaly score crosses the escalation threshold, "all" forwards every
    # scored reading (the naive all-to-cloud baseline for the bandwidth A/B).
    # Forwarding runs off the scoring worker, so it requires ENABLE_ML and
    # ML_ASYNC_SCORING.
    cloud_forward_mode: str = "off"
    cloud_endpoint_url: str = "http://cloud-tier:8000/api/v1/escalations"
    # Score at or above which a reading is escalated in "gated" mode. Empty ->
    # use the model's own anomaly threshold (escalate exactly the flagged set).
    cloud_escalation_threshold: float | None = None
    cloud_forward_batch_max_size: int = 64
    cloud_forward_batch_window_ms: int = 1000
    cloud_forward_queue_max_size: int = 20000
    cloud_forward_timeout_seconds: float = 5.0

    voltage_min: float = 0.0
    voltage_max: float = 300.0
    current_min: float = 0.0
    current_max: float = 100.0
    power_min: float = 0.0
    power_max: float = 20000.0
    temperature_min: float = -20.0
    temperature_max: float = 100.0
    max_future_skew_seconds: int = 60
    max_past_skew_seconds: int = 86400
    supported_schema_versions: str = "1.0"

    rules_file: str = "/app/config/rules.yaml"
    alert_cooldown_seconds: int = 300
    heartbeat_timeout_seconds: int = 30
    heartbeat_check_interval_seconds: int = 5

    alert_webhook_url: str = ""
    alert_slack_webhook_url: str = ""
    alert_console_enabled: bool = True
    alert_critical_only: bool = True
    alert_outbox_enabled: bool = True
    alert_outbox_poll_seconds: int = 5
    alert_outbox_batch_size: int = 50
    alert_outbox_max_attempts: int = 5

    retention_enabled: bool = True
    retention_raw_readings_days: int = 30
    retention_quality_logs_days: int = 14
    retention_system_metrics_days: int = 30
    retention_status_history_days: int = 30
    retention_alert_deliveries_days: int = 30
    retention_alert_outbox_days: int = 30

    metrics_flush_interval_seconds: int = 10

    @field_validator("processing_mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        if value not in {"baseline", "proposed"}:
            raise ValueError("processing_mode must be 'baseline' or 'proposed'")
        return value

    @field_validator("storage_policy")
    @classmethod
    def _validate_storage_policy(cls, value: str) -> str:
        if value not in {"raw", "hybrid", "event_only", "aggregate_only"}:
            raise ValueError(
                "storage_policy must be one of: raw, hybrid, event_only, aggregate_only"
            )
        return value

    @field_validator("cloud_forward_mode")
    @classmethod
    def _validate_cloud_forward_mode(cls, value: str) -> str:
        if value not in {"off", "gated", "all"}:
            raise ValueError("cloud_forward_mode must be one of: off, gated, all")
        return value

    @field_validator("supported_schema_versions")
    @classmethod
    def _split_versions(cls, value: str) -> str:
        return value.strip()

    @property
    def supported_schema_version_set(self) -> set[str]:
        return {v.strip() for v in self.supported_schema_versions.split(",") if v.strip()}

    @property
    def is_proposed(self) -> bool:
        return self.processing_mode == "proposed"

    @property
    def ml_feature_list(self) -> list[str]:
        return [f.strip() for f in self.ml_features.split(",") if f.strip()]

    @property
    def rules_path(self) -> Path:
        return Path(self.rules_file)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
