#!/usr/bin/env python3
"""High-performance async IoT energy data simulator.

Simulates many households sending energy telemetry to an HTTP endpoint.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from random import Random

import httpx


@dataclass
class Metrics:
    total_sent: int = 0
    total_success: int = 0
    total_failed: int = 0

    def record_success(self) -> None:
        self.total_sent += 1
        self.total_success += 1

    def record_failure(self) -> None:
        self.total_sent += 1
        self.total_failed += 1


def usage_band(hour: int) -> tuple[float, float]:
    """Return usage range in kW based on time-of-day pattern."""
    if 0 <= hour < 6:  # night: low
        return 0.15, 0.8
    if 6 <= hour < 12:  # morning: medium
        return 0.8, 2.3
    if 12 <= hour < 17:  # afternoon: moderate
        return 0.6, 1.8
    if 17 <= hour < 23:  # evening: peak
        return 2.0, 5.8
    return 0.3, 1.0  # late night wind-down


def generate_energy_data(house_id: str, rng: Random, device_scale: float) -> dict:
    """Generate realistic energy payload for one device."""
    now_local = datetime.now()
    now_utc = datetime.now(timezone.utc)
    min_kw, max_kw = usage_band(now_local.hour)

    # Device-specific behavior + random noise
    power_kw = rng.uniform(min_kw, max_kw) * device_scale
    power_kw = max(0.05, power_kw)

    voltage = 220.0 + rng.uniform(-3.5, 3.5)
    power_w = power_kw * 1000.0

    # Approximate current for household AC load
    power_factor = rng.uniform(0.92, 0.99)
    current = power_w / (voltage * power_factor)

    return {
        "house_id": house_id,
        "voltage": round(voltage, 2),
        "current": round(current, 3),
        "power": round(power_w, 2),
        "timestamp": now_utc.isoformat(),
    }


async def device_worker(
    house_id: str,
    client: httpx.AsyncClient,
    api_url: str,
    interval_s: float,
    stop_event: asyncio.Event,
    metrics: Metrics,
    semaphore: asyncio.Semaphore | None,
    timeout_s: float,
    rng: Random,
) -> None:
    """Coroutine that continuously sends readings for one simulated device."""
    # Spread initial sends to avoid synchronized thundering burst.
    await asyncio.sleep(rng.uniform(0, interval_s))

    # Slightly different average load profile per household.
    device_scale = rng.uniform(0.75, 1.25)

    while not stop_event.is_set():
        payload = generate_energy_data(house_id, rng, device_scale)

        try:
            if semaphore is not None:
                async with semaphore:
                    resp = await client.post(api_url, json=payload, timeout=timeout_s)
            else:
                resp = await client.post(api_url, json=payload, timeout=timeout_s)

            resp.raise_for_status()
            metrics.record_success()
        except Exception:
            # Keep simulation running despite intermittent failures.
            metrics.record_failure()

        sleep_for = interval_s * rng.uniform(0.9, 1.1)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
        except asyncio.TimeoutError:
            pass


async def metrics_logger(
    metrics: Metrics,
    stop_event: asyncio.Event,
    print_every_s: float = 5.0,
) -> None:
    """Print aggregate throughput stats periodically."""
    last_total = 0
    last_time = time.monotonic()

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=print_every_s)
        except asyncio.TimeoutError:
            pass

        now = time.monotonic()
        elapsed = max(now - last_time, 1e-9)
        current_total = metrics.total_sent
        delta = current_total - last_total
        rps = delta / elapsed

        print(
            f"[metrics] total={current_total} success={metrics.total_success} "
            f"failed={metrics.total_failed} rps={rps:.2f}"
        )

        last_total = current_total
        last_time = now


def make_house_id(index: int) -> str:
    return f"H{index:04d}"


async def run_simulation(args: argparse.Namespace) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _shutdown() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _shutdown)

    semaphore = (
        asyncio.Semaphore(args.max_inflight)
        if args.max_inflight and args.max_inflight > 0
        else None
    )

    limits = httpx.Limits(
        max_connections=max(args.max_inflight, 100)
        if args.max_inflight
        else max(args.devices, 100),
        max_keepalive_connections=min(args.devices, 1000),
    )

    metrics = Metrics()
    workers: list[asyncio.Task] = []

    async with httpx.AsyncClient(limits=limits) as client:
        for i in range(1, args.devices + 1):
            house_id = make_house_id(i)
            rng = Random(i * 7919)
            workers.append(
                asyncio.create_task(
                    device_worker(
                        house_id=house_id,
                        client=client,
                        api_url=args.api_url,
                        interval_s=args.interval,
                        stop_event=stop_event,
                        metrics=metrics,
                        semaphore=semaphore,
                        timeout_s=args.timeout,
                        rng=rng,
                    )
                )
            )

        metrics_task = asyncio.create_task(
            metrics_logger(
                metrics=metrics,
                stop_event=stop_event,
                print_every_s=args.metrics_interval,
            )
        )

        print(
            f"Starting simulator: devices={args.devices}, interval={args.interval}s, "
            f"max_inflight={args.max_inflight}, url={args.api_url}"
        )
        print("Press Ctrl+C to stop...")

        try:
            await asyncio.gather(*workers, metrics_task)
        except KeyboardInterrupt:
            stop_event.set()
        finally:
            stop_event.set()
            for task in workers:
                task.cancel()
            metrics_task.cancel()
            await asyncio.gather(*workers, metrics_task, return_exceptions=True)

    print(
        f"Final metrics: total={metrics.total_sent}, success={metrics.total_success}, "
        f"failed={metrics.total_failed}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async IoT energy data simulator")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8001/data",
        help="Target API endpoint URL",
    )
    parser.add_argument(
        "--devices", type=int, default=1000, help="Number of simulated devices"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0, help="Seconds between sends per device"
    )
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="Per-request timeout in seconds"
    )
    parser.add_argument(
        "--max-inflight",
        type=int,
        default=1000,
        help="Global concurrency limiter (requests in-flight)",
    )
    parser.add_argument(
        "--metrics-interval",
        type=float,
        default=5.0,
        help="Print metrics every N seconds",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_simulation(args))


if __name__ == "__main__":
    main()
