from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress

from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .database import Base, engine
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

    def increment(self) -> None:
        self.total_requests += 1

    def sample_rps(self) -> tuple[int, float]:
        now = time.monotonic()
        elapsed = max(now - self._last_ts, 1e-9)
        delta = self.total_requests - self._last_total
        rps = delta / elapsed
        self._last_total = self.total_requests
        self._last_ts = now
        return self.total_requests, rps


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.metrics_task = asyncio.create_task(metrics_reporter())
    logger.info("WattFlow backend started")
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


@app.middleware("http")
async def request_metrics_middleware(request: Request, call_next):
    app.state.metrics.increment()
    response = await call_next(request)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error on %s %s: %s", request.method, request.url.path, exc.errors()
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


async def metrics_reporter() -> None:
    while True:
        await asyncio.sleep(5)
        total, rps = app.state.metrics.sample_rps()
        logger.info("metrics total_requests=%d rps=%.2f", total, rps)
