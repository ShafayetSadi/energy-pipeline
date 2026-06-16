-- TimescaleDB extension (loaded if available; the gateway also tries to
-- create it idempotently on startup, so this is best-effort).
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Initial database creation is handled by the postgres container env vars.
-- The gateway runs SQLAlchemy create_all() on startup, then attempts
-- create_hypertable() for time-series tables.
-- The continuous aggregate is created here so it persists across restarts.
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
WITH NO DATA;
