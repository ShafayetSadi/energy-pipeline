"""Initial gateway schema.

Revision ID: 20260628_0001
Revises:
Create Date: 2026-06-28
"""
from __future__ import annotations

from collections.abc import Callable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import SQLAlchemyError

revision = "20260628_0001"
down_revision = None
branch_labels = None
depends_on = None


def _best_effort(sql: str, on_error: Callable[[Exception], None] | None = None) -> None:
    bind = op.get_bind()
    if not hasattr(bind, "begin_nested"):
        op.execute(sql)
        return
    try:
        with bind.begin_nested():
            bind.execute(sa.text(sql))
    except SQLAlchemyError as exc:
        if on_error is not None:
            on_error(exc)


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("device_id", sa.Text(), primary_key=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("device_type", sa.Text(), nullable=False),
        sa.Column("firmware_version", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "energy_readings",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column("device_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("voltage_v", sa.Float(), nullable=False),
        sa.Column("current_a", sa.Float(), nullable=False),
        sa.Column("power_w", sa.Float(), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("sequence_no", sa.BigInteger(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.device_id"]),
    )
    op.create_index(
        "idx_energy_readings_device_time",
        "energy_readings",
        ["device_id", "time"],
    )
    op.create_table(
        "events",
        sa.Column("event_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("rule_name", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("reading_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.device_id"]),
    )
    op.create_index("ix_events_time", "events", ["time"])
    op.create_index("idx_events_device_time", "events", ["device_id", "time"])
    op.create_index("idx_events_type_severity", "events", ["event_type", "severity", "time"])
    op.create_table(
        "data_quality_logs",
        sa.Column("log_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("topic", sa.Text(), nullable=True),
        sa.Column("device_id", sa.Text(), nullable=True),
        sa.Column("error_type", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "device_status_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("firmware_version", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("rssi_dbm", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.device_id"]),
    )
    op.create_table(
        "system_metrics",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column("metric_name", sa.Text(), primary_key=True, nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("labels", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "rule_definitions",
        sa.Column("rule_name", sa.Text(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "alert_deliveries",
        sa.Column("alert_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.BigInteger(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
    )
    op.create_table(
        "model_predictions",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column("device_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("model_version", sa.Text(), primary_key=True, nullable=False),
        sa.Column("prediction_type", sa.Text(), primary_key=True, nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("predicted_label", sa.Text(), nullable=True),
        sa.Column("input_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.device_id"]),
    )

    _best_effort("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    for table in (
        "energy_readings",
        "events",
        "system_metrics",
        "device_status_history",
    ):
        _best_effort(
            f"SELECT create_hypertable('{table}', 'time', if_not_exists => TRUE);"
        )
    _best_effort(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS energy_readings_1min
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 minute', time) AS bucket,
            device_id,
            AVG(voltage_v) AS avg_voltage_v,
            AVG(current_a) AS avg_current_a,
            AVG(power_w) AS avg_power_w,
            MAX(power_w) AS max_power_w,
            MIN(voltage_v) AS min_voltage_v,
            COUNT(*) AS sample_count
        FROM energy_readings
        GROUP BY bucket, device_id
        WITH NO DATA
        """
    )


def downgrade() -> None:
    _best_effort("DROP MATERIALIZED VIEW IF EXISTS energy_readings_1min;")
    op.drop_table("model_predictions")
    op.drop_table("alert_deliveries")
    op.drop_table("rule_definitions")
    op.drop_table("system_metrics")
    op.drop_table("device_status_history")
    op.drop_table("data_quality_logs")
    op.drop_index("idx_events_type_severity", table_name="events")
    op.drop_index("idx_events_device_time", table_name="events")
    op.drop_index("ix_events_time", table_name="events")
    op.drop_table("events")
    op.drop_index("idx_energy_readings_device_time", table_name="energy_readings")
    op.drop_table("energy_readings")
    op.drop_table("devices")
