"""Rule definition repository functions."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RuleDefinition


async def upsert_rule_definition(
    session: AsyncSession,
    *,
    rule_name: str,
    enabled: bool,
    event_type: str,
    severity: str,
    config: dict[str, Any],
) -> None:
    stmt = pg_insert(RuleDefinition).values(
        rule_name=rule_name,
        enabled=enabled,
        event_type=event_type,
        severity=severity,
        config=config,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[RuleDefinition.rule_name],
        set_={
            "enabled": stmt.excluded.enabled,
            "event_type": stmt.excluded.event_type,
            "severity": stmt.excluded.severity,
            "config": stmt.excluded.config,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)


async def list_rule_definitions(session: AsyncSession) -> Sequence[RuleDefinition]:
    result = await session.execute(
        select(RuleDefinition).order_by(RuleDefinition.rule_name)
    )
    return result.scalars().all()
