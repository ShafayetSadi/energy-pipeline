"""Async MQTT energy data simulator.

Publishes telemetry, status, and anomaly events to an MQTT broker. Scenarios
are configured via YAML files (see ``simulator/scenarios/``) or command-line
arguments for ad-hoc load tests.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import random
import signal
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiomqtt
import yaml


@dataclass
class Anomaly:
    device_id: str
    start_after_seconds: float
    duration_seconds: float
    type: str  # overload | undervoltage | overvoltage | power_spike | invalid | sensor_error
    current_a: float | None = None
    voltage_v: float | None = None
    power_w: float | None = None


@dataclass
class Scenario:
    name: str
    num_devices: int
    duration_seconds: float
    publish_interval_seconds: float
    anomalies: list[Anomaly] = field(default_factory=list)
    invalid_payload_ratio: float = 0.0
    base_voltage: float = 220.0


def usage_band(hour: int) -> tuple[float, float]:
    if 0 <= hour < 6:
        return 0.15, 0.8
    if 6 <= hour < 12:
        return 0.8, 2.3
    if 12 <= hour < 17:
        return 0.6, 1.8
    if 17 <= hour < 23:
        return 2.0, 5.8
    return 0.3, 1.0


def _device_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:04d}"


def make_scenario_from_args(args: argparse.Namespace) -> Scenario:
    return Scenario(
        name=args.scenario,
        num_devices=args.devices,
        duration_seconds=args.duration,
        publish_interval_seconds=args.interval,
        anomalies=[],
        invalid_payload_ratio=args.invalid_ratio,
        base_voltage=args.base_voltage,
    )


def load_scenario(path: Path) -> Scenario:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    anomalies = [
        Anomaly(
            device_id=a["device_id"],
            start_after_seconds=float(a["start_after_seconds"]),
            duration_seconds=float(a["duration_seconds"]),
            type=a["type"],
            current_a=a.get("current_a"),
            voltage_v=a.get("voltage_v"),
            power_w=a.get("power_w"),
        )
        for a in payload.get("anomalies", [])
    ]
    return Scenario(
        name=payload.get("scenario_name", path.stem),
        num_devices=int(payload.get("num_devices", 3)),
        duration_seconds=float(payload.get("duration_seconds", 300)),
        publish_interval_seconds=float(payload.get("publish_interval_seconds", 1)),
        anomalies=anomalies,
        invalid_payload_ratio=float(payload.get("invalid_payload_ratio", 0.0)),
        base_voltage=float(payload.get("base_voltage", 220.0)),
    )


def generate_telemetry(
    device_id: str,
    rng: random.Random,
    *,
    base_voltage: float,
    device_scale: float,
    anomaly_override: dict[str, Any] | None = None,
    force_invalid: bool = False,
) -> bytes:
    """Generate a single telemetry payload as encoded JSON bytes."""
    if force_invalid:
        return b'{"schema_version":"1.0","device_id":"' + device_id.encode() + b'","voltage_v":"oops"'

    now_utc = datetime.now(UTC)
    hour = datetime.now().hour
    min_kw, max_kw = usage_band(hour)
    power_kw = rng.uniform(min_kw, max_kw) * device_scale
    power_w = power_kw * 1000.0
    voltage = base_voltage + rng.uniform(-3.5, 3.5)
    pf = rng.uniform(0.92, 0.99)
    current = power_w / (voltage * pf)
    temperature = rng.uniform(25.0, 45.0)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "device_id": device_id,
        "timestamp": now_utc.isoformat(),
        "voltage_v": round(voltage, 2),
        "current_a": round(current, 3),
        "power_w": round(power_w, 2),
        "temperature_c": round(temperature, 1),
        "sequence_no": rng.randint(1, 1_000_000),
    }
    if anomaly_override:
        payload.update({k: v for k, v in anomaly_override.items() if v is not None})
    return json.dumps(payload).encode("utf-8")


def anomaly_payload(anomaly: Anomaly, base_voltage: float, rng: random.Random) -> dict[str, Any]:
    if anomaly.type == "overload":
        return {"current_a": anomaly.current_a or 12.5, "power_w": 2800.0}
    if anomaly.type == "undervoltage":
        v = anomaly.voltage_v or 180.0
        return {"voltage_v": v, "power_w": 1500.0}
    if anomaly.type == "overvoltage":
        v = anomaly.voltage_v or 260.0
        return {"voltage_v": v, "power_w": 1500.0}
    if anomaly.type == "power_spike":
        return {"power_w": anomaly.power_w or 5000.0}
    if anomaly.type == "sensor_error":
        return {"voltage_v": None}
    return {}


def generate_status(device_id: str, status: str = "online", rng: random.Random | None = None) -> bytes:
    rng = rng or random.Random()
    payload = {
        "schema_version": "1.0",
        "device_id": device_id,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        "firmware_version": "0.1.0",
        "rssi_dbm": rng.randint(-75, -45),
    }
    return json.dumps(payload).encode("utf-8")


@dataclass
class SimMetrics:
    sent: int = 0
    failed: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def rps(self) -> float:
        elapsed = max(time.monotonic() - self.started_at, 1e-9)
        return self.sent / elapsed


async def device_worker(
    *,
    device_id: str,
    client: aiomqtt.Client,
    base_topic: str,
    scenario: Scenario,
    rng: random.Random,
    stop_event: asyncio.Event,
    metrics: SimMetrics,
) -> None:
    """Publish telemetry + status for one device according to the scenario."""
    device_scale = rng.uniform(0.75, 1.25)
    # Stagger initial sends.
    await asyncio.sleep(rng.uniform(0, scenario.publish_interval_seconds))

    while not stop_event.is_set():
        now = time.monotonic()
        scenario_start = metrics.started_at

        # Pick the most recent applicable anomaly.
        active: Anomaly | None = None
        for anomaly in scenario.anomalies:
            if anomaly.device_id not in {device_id, "*"}:
                continue
            t = scenario_start + anomaly.start_after_seconds
            if t <= now <= t + anomaly.duration_seconds:
                active = anomaly
                break

        force_invalid = rng.random() < scenario.invalid_payload_ratio
        override: dict[str, Any] | None = None
        if active is not None:
            override = anomaly_payload(active, scenario.base_voltage, rng)

        payload = generate_telemetry(
            device_id,
            rng,
            base_voltage=scenario.base_voltage,
            device_scale=device_scale,
            anomaly_override=override,
            force_invalid=force_invalid,
        )
        topic = f"{base_topic}/{device_id}/telemetry"
        try:
            await client.publish(topic, payload, qos=0)
            metrics.sent += 1
        except Exception:
            metrics.failed += 1

        # Periodic status heartbeat.
        if int(now * 2) % 30 == 0:
            try:
                await client.publish(
                    f"{base_topic}/{device_id}/status",
                    generate_status(device_id, "online", rng),
                    qos=1,
                )
            except Exception:
                metrics.failed += 1

        sleep_for = scenario.publish_interval_seconds * rng.uniform(0.85, 1.15)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
        except TimeoutError:
            pass


async def metrics_logger(
    metrics: SimMetrics, stop_event: asyncio.Event, interval: float = 5.0
) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            pass
        if stop_event.is_set():
            break
        print(
            f"[sim] sent={metrics.sent} failed={metrics.failed} rps={metrics.rps():.2f}",
            flush=True,
        )


async def run(args: argparse.Namespace) -> None:
    scenario = (
        load_scenario(Path(args.scenario_file))
        if args.scenario_file
        else make_scenario_from_args(args)
    )
    print(
        f"Starting simulator: scenario={scenario.name} devices={scenario.num_devices} "
        f"interval={scenario.publish_interval_seconds}s host={args.host}:{args.port}",
        flush=True,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _shutdown(*_: Any) -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _shutdown)

    metrics = SimMetrics()
    workers: list[asyncio.Task] = []

    async with aiomqtt.Client(
        hostname=args.host,
        port=args.port,
        identifier=f"simulator-{int(time.time())}",
    ) as client:
        for i in range(1, scenario.num_devices + 1):
            device_id = _device_id(args.device_prefix, i)
            workers.append(
                asyncio.create_task(
                    device_worker(
                        device_id=device_id,
                        client=client,
                        base_topic=args.base_topic,
                        scenario=scenario,
                        rng=random.Random(i * 7919),
                        stop_event=stop_event,
                        metrics=metrics,
                    )
                )
            )

        workers.append(asyncio.create_task(metrics_logger(metrics, stop_event)))

        if scenario.duration_seconds > 0:
            async def _stop_after() -> None:
                await asyncio.sleep(scenario.duration_seconds)
                stop_event.set()

            workers.append(asyncio.create_task(_stop_after()))

        try:
            await asyncio.gather(*workers)
        except KeyboardInterrupt:
            stop_event.set()
        finally:
            stop_event.set()
            for t in workers:
                t.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    print(
        f"Simulator finished. total_sent={metrics.sent} failed={metrics.failed} "
        f"rps={metrics.rps():.2f}",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async MQTT energy data simulator")
    parser.add_argument("--host", default="mosquitto", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port (container-internal: 1883, host: 18831)")
    parser.add_argument("--device-prefix", default="house")
    parser.add_argument("--base-topic", default="energy")
    parser.add_argument("--devices", type=int, default=10)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--scenario", default="custom")
    parser.add_argument("--scenario-file", default="", help="YAML scenario file path")
    parser.add_argument("--invalid-ratio", type=float, default=0.0)
    parser.add_argument("--base-voltage", type=float, default=220.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
