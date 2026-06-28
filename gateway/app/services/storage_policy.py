"""Storage policy decisions for telemetry persistence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..config import Settings

StoragePolicy = Literal["raw", "hybrid", "event_only", "aggregate_only"]


@dataclass(frozen=True)
class ReadingStorageDecision:
    store_raw: bool
    reason: str


class StoragePolicyService:
    """Centralizes raw-reading storage decisions across operating modes."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def decide_reading_storage(self, *, event_triggering: bool) -> ReadingStorageDecision:
        if self._settings.processing_mode == "baseline":
            return ReadingStorageDecision(store_raw=True, reason="baseline_forces_raw")

        policy = self._settings.storage_policy
        if policy == "raw":
            return ReadingStorageDecision(store_raw=True, reason="policy_raw")
        if policy == "hybrid":
            if event_triggering or self._settings.store_raw_readings:
                return ReadingStorageDecision(store_raw=True, reason="policy_hybrid_store")
            return ReadingStorageDecision(store_raw=False, reason="policy_hybrid_skip")
        if policy == "event_only":
            return ReadingStorageDecision(
                store_raw=event_triggering,
                reason="policy_event_only_event" if event_triggering else "policy_event_only_skip",
            )
        return ReadingStorageDecision(store_raw=False, reason="policy_aggregate_only_skip")
