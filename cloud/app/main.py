"""Cloud-tier receiver + verifier for edge->cloud escalations (Phase 2/3).

Phase 2 made this a minimal receiver that terminates the escalation path and
counts batches, readings, and payload bytes for the bandwidth A/B. Phase 3
adds a heavier cloud-side model: an LSTM autoencoder (``verifier.py``) that
re-examines the escalated readings and confirms or suppresses each one by
reconstruction error. Verdict counts and inference latency are exposed
alongside the Phase 2 counters at ``/api/v1/metrics/summary``. The verifier
disables itself cleanly if its artifact is absent, so the receiver behaves
exactly as in Phase 2 when no cloud model is shipped.
"""
from __future__ import annotations

import time
from collections import Counter, deque
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from .verifier import CloudVerifier

app = FastAPI(title="cloud-tier", version="0.2.0")

RECENT_MAX = 500

verifier = CloudVerifier()

state: dict[str, Any] = {
    "started_at": time.monotonic(),
    "counters": Counter(),
    "recent": deque(maxlen=RECENT_MAX),
    "verdicts": deque(maxlen=RECENT_MAX),
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
    verdict_buf: deque = state["verdicts"]
    for reading in envelope.readings:
        counters[f"escalations.device.{reading.device_id}"] += 1
        payload = reading.model_dump()
        recent.append(payload)
        if verifier.available:
            infer_start = time.perf_counter()
            verdicts = verifier.add(payload)
            if verdicts:
                counters["verify.inference_ms"] += (time.perf_counter() - infer_start) * 1000.0
                counters["verify.windows"] += 1
                for v in verdicts:
                    counters["verify.scored"] += 1
                    if v["confirmed"]:
                        counters["verify.confirmed"] += 1
                    else:
                        counters["verify.suppressed"] += 1
                    verdict_buf.append(v)
    return {"accepted": len(envelope.readings)}


@app.get("/api/v1/escalations/recent")
async def recent_escalations(limit: int = 50) -> list[dict[str, Any]]:
    recent: deque = state["recent"]
    return list(recent)[-limit:]


@app.get("/api/v1/verdicts/recent")
async def recent_verdicts(limit: int = 50) -> list[dict[str, Any]]:
    verdicts: deque = state["verdicts"]
    return list(verdicts)[-limit:]


@app.get("/api/v1/metrics/summary")
async def metrics_summary() -> dict[str, Any]:
    counters = dict(state["counters"])
    windows = counters.get("verify.windows", 0)
    if windows:
        counters["verify.avg_inference_ms"] = round(
            counters["verify.inference_ms"] / windows, 4
        )
    return {
        "uptime_seconds": time.monotonic() - state["started_at"],
        "verifier": {"available": verifier.available, "version": verifier.version},
        "counters": counters,
    }
