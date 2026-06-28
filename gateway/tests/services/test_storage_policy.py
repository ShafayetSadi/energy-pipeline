"""Tests for telemetry storage policy decisions."""
from __future__ import annotations

from gateway.app.config import Settings
from gateway.app.services.storage_policy import StoragePolicyService


def _service(
    *,
    mode: str = "proposed",
    policy: str = "raw",
    store_raw: bool = True,
) -> StoragePolicyService:
    return StoragePolicyService(
        Settings(
            processing_mode=mode,
            storage_policy=policy,
            store_raw_readings=store_raw,
        )
    )


def test_baseline_forces_raw_storage() -> None:
    service = _service(mode="baseline", policy="aggregate_only", store_raw=False)

    assert service.decide_reading_storage(event_triggering=False).store_raw is True


def test_raw_policy_stores_all_readings() -> None:
    service = _service(policy="raw", store_raw=False)

    assert service.decide_reading_storage(event_triggering=False).store_raw is True
    assert service.decide_reading_storage(event_triggering=True).store_raw is True


def test_hybrid_uses_store_raw_for_normal_readings() -> None:
    service = _service(policy="hybrid", store_raw=False)

    assert service.decide_reading_storage(event_triggering=False).store_raw is False
    assert service.decide_reading_storage(event_triggering=True).store_raw is True


def test_event_only_stores_only_event_triggering_readings() -> None:
    service = _service(policy="event_only", store_raw=True)

    assert service.decide_reading_storage(event_triggering=False).store_raw is False
    assert service.decide_reading_storage(event_triggering=True).store_raw is True


def test_aggregate_only_skips_all_raw_readings() -> None:
    service = _service(policy="aggregate_only", store_raw=True)

    assert service.decide_reading_storage(event_triggering=False).store_raw is False
    assert service.decide_reading_storage(event_triggering=True).store_raw is False
