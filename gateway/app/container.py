"""Application composition helpers."""
from __future__ import annotations

from dataclasses import dataclass

from .config import Settings, get_settings
from .logging_config import configure_logging
from .services.alert_service import AlertService
from .services.ingestion import IngestionService
from .services.metrics_service import MetricsService
from .services.rule_engine import RuleEngine
from .services.storage_policy import StoragePolicyService
from .services.validation_service import ValidationService
from .workers.aggregation_worker import AggregationWorker
from .workers.alert_outbox import AlertOutboxWorker
from .workers.device_heartbeat import DeviceHeartbeatWorker
from .workers.mqtt_consumer import MQTTConsumerWorker


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    validator: ValidationService
    rule_engine: RuleEngine
    metrics: MetricsService
    storage_policy: StoragePolicyService
    alert_service: AlertService
    ingestion: IngestionService
    mqtt_worker: MQTTConsumerWorker
    heartbeat_worker: DeviceHeartbeatWorker
    alert_outbox_worker: AlertOutboxWorker
    agg_worker: AggregationWorker


def build_container() -> AppContainer:
    settings = get_settings()
    configure_logging(settings.log_level)

    validator = ValidationService()
    rule_engine = RuleEngine()
    metrics = MetricsService()
    storage_policy = StoragePolicyService(settings)
    alert_service = AlertService()
    ingestion = IngestionService(
        validator=validator,
        rule_engine=rule_engine,
        alert_service=alert_service,
        metrics=metrics,
        storage_policy=storage_policy,
    )

    return AppContainer(
        settings=settings,
        validator=validator,
        rule_engine=rule_engine,
        metrics=metrics,
        storage_policy=storage_policy,
        alert_service=alert_service,
        ingestion=ingestion,
        mqtt_worker=MQTTConsumerWorker(ingestion=ingestion, metrics=metrics),
        heartbeat_worker=DeviceHeartbeatWorker(
            rule_engine=rule_engine,
            alert_service=alert_service,
            metrics=metrics,
        ),
        alert_outbox_worker=AlertOutboxWorker(alert_service=alert_service),
        agg_worker=AggregationWorker(),
    )
