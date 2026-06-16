from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import insert, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import EnergyData
from .schemas import EnergyDataBatchIn, EnergyDataIn, HealthResponse, IngestResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("Health check failed: database unavailable")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable") from exc

    return HealthResponse(status="ok", service="wattflow-backend")


@router.post("/data", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_data(
    payload: EnergyDataIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    handler_started_at = time.perf_counter()
    try:
        execute_started_at = time.perf_counter()
        await db.execute(
            insert(EnergyData).values(
                house_id=payload.house_id,
                voltage=payload.voltage,
                current=payload.current,
                power=payload.power,
                timestamp=payload.timestamp,
            )
        )
        request.state.db_execute_ms = (
            time.perf_counter() - execute_started_at
        ) * 1000.0

        commit_started_at = time.perf_counter()
        await db.commit()
        request.state.db_commit_ms = (
            time.perf_counter() - commit_started_at
        ) * 1000.0
        request.state.total_handler_ms = (
            time.perf_counter() - handler_started_at
        ) * 1000.0
        return IngestResponse(status="accepted")
    except SQLAlchemyError as exc:
        await db.rollback()
        request.state.total_handler_ms = (
            time.perf_counter() - handler_started_at
        ) * 1000.0
        logger.exception("Failed to persist data for house_id=%s", payload.house_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database write failed") from exc


@router.post("/data/batch", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_data_batch(
    payload: EnergyDataBatchIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    handler_started_at = time.perf_counter()
    if not payload.items:
        request.state.total_handler_ms = (
            time.perf_counter() - handler_started_at
        ) * 1000.0
        return IngestResponse(status="accepted:0")

    rows = [
        {
            "house_id": item.house_id,
            "voltage": item.voltage,
            "current": item.current,
            "power": item.power,
            "timestamp": item.timestamp,
        }
        for item in payload.items
    ]

    try:
        execute_started_at = time.perf_counter()
        await db.execute(insert(EnergyData), rows)
        request.state.db_execute_ms = (
            time.perf_counter() - execute_started_at
        ) * 1000.0

        commit_started_at = time.perf_counter()
        await db.commit()
        request.state.db_commit_ms = (
            time.perf_counter() - commit_started_at
        ) * 1000.0
        request.state.total_handler_ms = (
            time.perf_counter() - handler_started_at
        ) * 1000.0
        return IngestResponse(status=f"accepted:{len(rows)}")
    except SQLAlchemyError as exc:
        await db.rollback()
        request.state.total_handler_ms = (
            time.perf_counter() - handler_started_at
        ) * 1000.0
        logger.exception("Failed batch write (%d rows)", len(rows))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database write failed") from exc
