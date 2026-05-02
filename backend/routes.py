from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
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
async def ingest_data(payload: EnergyDataIn, db: AsyncSession = Depends(get_db)) -> IngestResponse:
    try:
        await db.execute(
            insert(EnergyData).values(
                house_id=payload.house_id,
                voltage=payload.voltage,
                current=payload.current,
                power=payload.power,
                timestamp=payload.timestamp,
            )
        )
        await db.commit()
        return IngestResponse(status="accepted")
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to persist data for house_id=%s", payload.house_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database write failed") from exc


@router.post("/data/batch", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_data_batch(payload: EnergyDataBatchIn, db: AsyncSession = Depends(get_db)) -> IngestResponse:
    if not payload.items:
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
        await db.execute(insert(EnergyData), rows)
        await db.commit()
        return IngestResponse(status=f"accepted:{len(rows)}")
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed batch write (%d rows)", len(rows))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database write failed") from exc
