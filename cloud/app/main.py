"""Cloud-tier receiver for edge->cloud escalations (Phase 2).

This service is intentionally minimal: it terminates the escalation path so
the edge gateway's gated forwarding can be exercised and its bandwidth
measured end to end. It counts every batch, reading, and payload byte it
receives and exposes those counters at ``/api/v1/metrics/summary`` for the
bandwidth A/B script. It keeps a bounded in-memory buffer of recent
escalations for inspection but persists nothing.

The heavier cloud-side model (LSTM forecasting / failure prediction) is a
later phase and deliberately not part of this service yet.
"""
from __future__ import annotations

import time
from collections import Counter, deque
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

app = FastAPI(title="cloud-tier", version="0.1.0")

RECENT_MAX = 500

state: dict[str, Any] = {
    "started_at": time.monotonic(),
    "counters": Counter(),
    "recent": deque(maxlen=RECENT_MAX),
}


class EscalatedReading(BaseModel):
    device_id: str
    timestamp: str
    reading_time: str
    voltage_v: float
    current_a: float
    power_w: float
    temperature_c: float | None = None
    anomaly_score: float
    threshold: float
    model_version: str
    rule_fired: bool = False


class EscalationEnvelope(BaseModel):
    source: str
    mode: str
    readings: list[EscalatedReading] = Field(default_factory=list)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/escalations")
async def receive_escalations(request: Request) -> dict[str, int]:
    body = await request.body()
    envelope = EscalationEnvelope.model_validate_json(body)
    counters: Counter = state["counters"]
    counters["escalations.batches"] += 1
    counters["escalations.readings"] += len(envelope.readings)
    counters["escalations.bytes_received"] += len(body)
    counters[f"escalations.mode.{envelope.mode}"] += len(envelope.readings)
    recent: deque = state["recent"]
    for reading in envelope.readings:
        counters[f"escalations.device.{reading.device_id}"] += 1
        recent.append(reading.model_dump())
    return {"accepted": len(envelope.readings)}


@app.get("/api/v1/escalations/recent")
async def recent_escalations(limit: int = 50) -> list[dict[str, Any]]:
    recent: deque = state["recent"]
    return list(recent)[-limit:]


@app.get("/api/v1/metrics/summary")
async def metrics_summary() -> dict[str, Any]:
    return {
        "uptime_seconds": time.monotonic() - state["started_at"],
        "counters": dict(state["counters"]),
    }
