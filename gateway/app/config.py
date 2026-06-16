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
    store_raw_readings: bool = True
    enable_rule_engine: bool = True
    enable_aggregation: bool = True
    enable_alerts: bool = True
    enable_ml: bool = False

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
    alert_console_enabled: bool = True
    alert_critical_only: bool = True

    metrics_flush_interval_seconds: int = 10

    @field_validator("processing_mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        if value not in {"baseline", "proposed"}:
            raise ValueError("processing_mode must be 'baseline' or 'proposed'")
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
    def rules_path(self) -> Path:
        return Path(self.rules_file)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
