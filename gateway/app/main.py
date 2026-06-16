"""FastAPI application entry point for the edge gateway."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import devices, events, health, metrics, readings, rules
from .config import get_settings
from .db.models import Base
from .db.session import engine, session_scope
from .db.timescale import ensure_timescale_extension
from .logging_config import configure_logging, get_logger
from .services.alert_service import AlertService
from .services.ingestion_service import IngestionService
from .services.metrics_service import MetricsService
from .services.rule_engine import RuleEngine
from .services.validation_service import ValidationService
from .workers.aggregation_worker import AggregationWorker
from .workers.device_heartbeat import DeviceHeartbeatWorker
from .workers.mqtt_consumer import MQTTConsumerWorker


def _build_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("app.startup")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Database schema + TimescaleDB hypertables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with engine.begin() as conn:
            from sqlalchemy import text

            await conn.execute(text("ANALYZE"))
        async with session_scope() as session:
            await ensure_timescale_extension(session)

        # Services and workers
        validator = ValidationService()
        rule_engine = RuleEngine()
        metrics_svc = MetricsService()
        alert_svc = AlertService()
        ingestion = IngestionService(
            validator=validator,
            rule_engine=rule_engine,
            alert_service=alert_svc,
            metrics=metrics_svc,
        )

        mqtt_worker = MQTTConsumerWorker(ingestion=ingestion, metrics=metrics_svc)
        heartbeat_worker = DeviceHeartbeatWorker(
            rule_engine=rule_engine,
            alert_service=alert_svc,
            metrics=metrics_svc,
        )
        agg_worker = AggregationWorker()

        app.state.settings = settings
        app.state.validator = validator
        app.state.rule_engine = rule_engine
        app.state.metrics = metrics_svc
        app.state.alert_service = alert_svc
        app.state.ingestion = ingestion
        app.state.mqtt_worker = mqtt_worker
        app.state.heartbeat_worker = heartbeat_worker
        app.state.agg_worker = agg_worker

        await metrics_svc.start()
        await alert_svc.start()
        await mqtt_worker.start()
        await heartbeat_worker.start()
        await agg_worker.start()

        logger.info(
            "edge_gateway_started",
            mode=settings.processing_mode,
            store_raw=settings.store_raw_readings,
            rule_engine=settings.enable_rule_engine,
        )
        try:
            yield
        finally:
            logger.info("edge_gateway_stopping")
            for stopper in (agg_worker, heartbeat_worker, mqtt_worker):
                await stopper.stop()
            await alert_svc.stop()
            await metrics_svc.stop()
            await engine.dispose()
            logger.info("edge_gateway_stopped")

    app = FastAPI(
        title="Edge Gateway",
        version=settings.service_version,
        description=(
            "Event-driven edge gateway for IoT-based smart energy monitoring. "
            "Consumes MQTT, validates, applies rule engine, stores in TimescaleDB, "
            "and dispatches alerts."
        ),
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(devices.router)
    app.include_router(readings.router)
    app.include_router(events.router)
    app.include_router(metrics.router)
    app.include_router(rules.router)
    return app


app = _build_app()
