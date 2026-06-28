"""FastAPI lifespan orchestration."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .container import AppContainer
from .db.session import engine
from .logging_config import get_logger

logger = get_logger("app.startup")


def attach_container(app: FastAPI, container: AppContainer) -> None:
    app.state.settings = container.settings
    app.state.validator = container.validator
    app.state.rule_engine = container.rule_engine
    app.state.metrics = container.metrics
    app.state.alert_service = container.alert_service
    app.state.ingestion = container.ingestion
    app.state.mqtt_worker = container.mqtt_worker
    app.state.heartbeat_worker = container.heartbeat_worker
    app.state.alert_outbox_worker = container.alert_outbox_worker
    app.state.agg_worker = container.agg_worker


def make_lifespan(container: AppContainer):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        attach_container(app, container)

        await container.metrics.start()
        await container.alert_service.start()
        await container.alert_outbox_worker.start()
        await container.mqtt_worker.start()
        await container.heartbeat_worker.start()
        await container.agg_worker.start()

        logger.info(
            "edge_gateway_started",
            mode=container.settings.processing_mode,
            store_raw=container.settings.store_raw_readings,
            rule_engine=container.settings.enable_rule_engine,
        )
        try:
            yield
        finally:
            logger.info("edge_gateway_stopping")
            await container.agg_worker.stop()
            await container.heartbeat_worker.stop()
            await container.mqtt_worker.stop()
            await container.alert_outbox_worker.stop()
            await container.alert_service.stop()
            await container.metrics.stop()
            await engine.dispose()
            logger.info("edge_gateway_stopped")

    return lifespan
