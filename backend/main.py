from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress

from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.responses import JSONResponse

from .database import Base, engine
from .request_metrics import (
    RequestMetricsRecorder,
    build_request_metric,
    default_metrics_path,
)
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("wattflow")


class Metrics:
    def __init__(self) -> None:
        self.total_requests = 0
        self._last_total = 0
        self._last_ts = time.monotonic()
        self.total_processing_time_ms = 0.0

    def increment(self) -> None:
        self.total_requests += 1

    def record_processing_time(self, duration_ms: float) -> None:
        self.total_processing_time_ms += duration_ms

    def sample_rps(self) -> tuple[int, float]:
        now = time.monotonic()
        elapsed = max(now - self._last_ts, 1e-9)
        delta = self.total_requests - self._last_total
        rps = delta / elapsed
        self._last_total = self.total_requests
        self._last_ts = now
        return self.total_requests, rps

    @property
    def avg_processing_time_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_processing_time_ms / self.total_requests


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.request_metrics = RequestMetricsRecorder(default_metrics_path())
    app.state.metrics_task = asyncio.create_task(metrics_reporter())
    logger.info(
        "WattFlow backend started; request metrics csv=%s",
        app.state.request_metrics.path,
    )
    try:
        yield
    finally:
        task = app.state.metrics_task
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await engine.dispose()
        logger.info("WattFlow backend stopped")


app = FastAPI(title="WattFlow Backend", version="0.1.0", lifespan=lifespan)
app.include_router(router)
app.state.metrics = Metrics()
app.state.metrics_task = None
app.state.request_metrics = None


@app.middleware("http")
async def request_metrics_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    app.state.metrics.increment()
    request.state.db_execute_ms = 0.0
    request.state.db_commit_ms = 0.0
    request.state.total_handler_ms = 0.0
    response = None

    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - started_at) * 1000.0
        status_code = response.status_code if response is not None else 500
        app.state.metrics.record_processing_time(duration_ms)
        app.state.request_metrics.record(
            build_request_metric(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                processing_time_ms=duration_ms,
                db_execute_ms=request.state.db_execute_ms,
                db_commit_ms=request.state.db_commit_ms,
                total_handler_ms=request.state.total_handler_ms,
            )
        )
        


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error on %s %s: %s", request.method, request.url.path, exc.errors()
    )
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(FastAPIHTTPException)
async def fastapi_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


async def metrics_reporter() -> None:
    while True:
        await asyncio.sleep(5)
        total, rps = app.state.metrics.sample_rps()
        logger.info(
            "metrics total_requests=%d rps=%.2f avg_processing_time_ms=%.2f",
            total,
            rps,
            app.state.metrics.avg_processing_time_ms,
        )
