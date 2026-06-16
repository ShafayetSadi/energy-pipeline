"""SQL schema bootstrap. Idempotent: safe to run on every gateway start."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..logging_config import get_logger

logger = get_logger(__name__)


HYPERTABLES_SQL = [
    "SELECT create_hypertable('energy_readings', 'time', if_not_exists => TRUE);",
    "SELECT create_hypertable('events', 'time', if_not_exists => TRUE);",
    "SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);",
    "SELECT create_hypertable('device_status_history', 'time', if_not_exists => TRUE);",
]


async def ensure_timescale_extension(session: AsyncSession) -> None:
    settings = get_settings()
    if not settings.enable_timescale:
        return
    try:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        await session.commit()
        logger.info("timescaledb_extension_ensured")
    except Exception as exc:  # pragma: no cover - depends on extension availability
        await session.rollback()
        logger.warning("timescale_extension_unavailable", error=str(exc))
        return

    for stmt in HYPERTABLES_SQL:
        try:
            await session.execute(text(stmt))
            await session.commit()
        except Exception as exc:
            await session.rollback()
            # Hypertable already exists, FK constraint blocks it, or
            # extension missing. None of these are fatal; the gateway
            # continues to work with regular PostgreSQL tables.
            logger.info("hypertable_create_skipped", statement=stmt, error=str(exc))
            continue

    # Continuous aggregate (best-effort, only meaningful when the underlying
    # table is a hypertable and has data).
    try:
        await session.execute(
            text(
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS energy_readings_1min
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('1 minute', time) AS bucket,
                    device_id,
                    AVG(voltage_v) AS avg_voltage_v,
                    AVG(current_a) AS avg_current_a,
                    AVG(power_w)   AS avg_power_w,
                    MAX(power_w)   AS max_power_w,
                    MIN(voltage_v) AS min_voltage_v,
                    COUNT(*)       AS sample_count
                FROM energy_readings
                GROUP BY bucket, device_id
                WITH NO DATA
                """
            )
        )
        await session.commit()
        logger.info("continuous_aggregate_ensured", view="energy_readings_1min")
    except Exception as exc:
        await session.rollback()
        logger.info("continuous_aggregate_skipped", error=str(exc))
