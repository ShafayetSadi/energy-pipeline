from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EnergyDataIn(BaseModel):
    house_id: str
    voltage: float
    current: float
    power: float
    timestamp: datetime


class EnergyDataBatchIn(BaseModel):
    items: list[EnergyDataIn]


class IngestResponse(BaseModel):
    status: str


class HealthResponse(BaseModel):
    status: str
    service: str


class ErrorResponse(BaseModel):
    detail: str


class EnergyDataOut(EnergyDataIn):
    id: int

    model_config = ConfigDict(from_attributes=True)
