"""Rule management endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repositories import rules as rule_repo
from ..db.session import get_db
from ..services.rule_engine import RuleEngine

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


def _engine(request: Request) -> RuleEngine:
    return request.app.state.rule_engine


@router.get("")
async def list_rules(request: Request) -> list[dict[str, Any]]:
    engine = _engine(request)
    out: list[dict[str, Any]] = []
    for name in engine.rule_names:
        rule = engine.get_rule(name) or {}
        out.append({"rule_name": name, **rule})
    return out


@router.get("/{rule_name}")
async def get_rule(rule_name: str, request: Request) -> dict[str, Any]:
    engine = _engine(request)
    rule = engine.get_rule(rule_name)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule not found")
    return {"rule_name": rule_name, **rule}


class RulePatch(BaseModel):
    enabled: bool | None = None


@router.patch("/{rule_name}", status_code=status.HTTP_200_OK)
async def patch_rule(
    rule_name: str,
    patch: RulePatch,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    engine = _engine(request)
    rule = engine.get_rule(rule_name)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule not found")
    if patch.enabled is not None:
        rule["enabled"] = patch.enabled
        await rule_repo.upsert_rule_definition(
            db,
            rule_name=rule_name,
            enabled=patch.enabled,
            event_type=rule.get("event_type", rule_name.upper()),
            severity=rule.get("severity", "WARNING"),
            config=rule.get("condition", {}),
        )
        await db.commit()
    return {"rule_name": rule_name, **rule}


@router.post("/reload", status_code=status.HTTP_200_OK)
async def reload_rules(request: Request) -> dict[str, Any]:
    engine = _engine(request)
    await engine.reload()
    return {"rules_loaded": len(engine.rule_names)}
