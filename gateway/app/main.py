"""FastAPI application entry point for the edge gateway."""
from __future__ import annotations

from fastapi import FastAPI

from .api import devices, events, health, metrics, readings, rules
from .container import build_container
from .lifespan import make_lifespan


def _build_app() -> FastAPI:
    container = build_container()

    app = FastAPI(
        title="Edge Gateway",
        version=container.settings.service_version,
        description=(
            "Event-driven edge gateway for IoT-based smart energy monitoring. "
            "Consumes MQTT, validates, applies rule engine, stores in TimescaleDB, "
            "and dispatches alerts."
        ),
        lifespan=make_lifespan(container),
    )
    app.include_router(health.router)
    app.include_router(devices.router)
    app.include_router(readings.router)
    app.include_router(events.router)
    app.include_router(metrics.router)
    app.include_router(rules.router)
    return app


app = _build_app()
