"""Model prediction repository (edge ML anomaly scores)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ModelPrediction


async def insert_prediction(
    session: AsyncSession,
    *,
    time: datetime,
    device_id: str,
    model_version: str,
    prediction_type: str,
    anomaly_score: float | None,
    predicted_label: str | None,
    input_window_start: datetime | None = None,
    input_window_end: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Insert a prediction, idempotent on the composite primary key."""
    stmt = (
        pg_insert(ModelPrediction)
        .values(
            time=time,
            device_id=device_id,
            model_version=model_version,
            prediction_type=prediction_type,
            anomaly_score=anomaly_score,
            predicted_label=predicted_label,
            input_window_start=input_window_start,
            input_window_end=input_window_end,
            prediction_metadata=metadata,
        )
        .on_conflict_do_nothing(
            index_elements=[
                ModelPrediction.time,
                ModelPrediction.device_id,
                ModelPrediction.model_version,
                ModelPrediction.prediction_type,
            ]
        )
        .returning(ModelPrediction.device_id)
    )
    result = await session.execute(stmt)
    return result.first() is not None


async def count_predictions(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(ModelPrediction))
    return int(result.scalar_one() or 0)
