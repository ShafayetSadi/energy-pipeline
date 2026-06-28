"""Tests for AlertService Slack delivery."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
import pytest
from gateway.app.services import alert_service as alert_service_module
from gateway.app.services.alert_service import AlertService
from gateway.app.services.rule_engine import RuleHit


@asynccontextmanager
async def _noop_session_scope():
    yield None


@pytest.fixture(autouse=True)
def _stub_session_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(alert_service_module, "session_scope", _noop_session_scope)


def _hit() -> RuleHit:
    return RuleHit(
        rule_name="overload",
        event_type="OVERLOAD",
        severity="CRITICAL",
        message="Current exceeded configured threshold",
        event_value=12.5,
        threshold_value=10.0,
    )


async def test_slack_delivery_posts_text_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    service = AlertService()
    service._settings.alert_slack_webhook_url = "https://hooks.slack.test/services/x"
    service._settings.alert_webhook_url = ""
    service._settings.alert_critical_only = True
    service._settings.alert_outbox_enabled = False
    service._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    delivered = await service.maybe_alert(
        _hit(), event_id=1, device_id="house_0001", event_time=datetime.now(UTC)
    )

    assert delivered is True
    assert captured["url"] == "https://hooks.slack.test/services/x"
    assert "OVERLOAD" in captured["body"]["text"]
    assert "house_0001" in captured["body"]["text"]

    await service._client.aclose()


async def test_slack_delivery_skipped_when_unconfigured() -> None:
    service = AlertService()
    service._settings.alert_slack_webhook_url = ""
    service._settings.alert_webhook_url = ""
    service._settings.alert_critical_only = True
    service._settings.alert_outbox_enabled = False

    delivered = await service.maybe_alert(
        _hit(), event_id=2, device_id="house_0002", event_time=datetime.now(UTC)
    )

    assert delivered is True
