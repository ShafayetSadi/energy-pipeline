#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "experiments" / "results"
SIMULATOR_PATH = ROOT / "simulator" / "simulator.py"


@dataclass(frozen=True)
class Experiment:
    devices: int
    interval_s: float = 1.0
    duration_s: int = 120
    max_inflight: int | None = None

    @property
    def label(self) -> str:
        interval_label = (
            str(int(self.interval_s))
            if self.interval_s.is_integer()
            else str(self.interval_s)
        )
        return f"{self.devices}-devices-{interval_label}s"

    @property
    def verdict(self) -> str:
        if self.devices == 100:
            return "stable"
        if self.devices == 300:
            return "moderate load"
        if self.devices == 500:
            return "stress"
        if self.devices == 1000:
            return "break point"
        return "custom"


EXPERIMENTS = [
    Experiment(devices=100, max_inflight=100),
    Experiment(devices=300, max_inflight=300),
    Experiment(devices=500, max_inflight=500),
    Experiment(devices=1000, max_inflight=1000),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the required load-test matrix.")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8001/data",
        help="Target ingestion endpoint.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="Per-experiment duration in seconds.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(RESULTS_DIR),
        help="Directory for logs, JSON summaries, and summary.md.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands without executing them.",
    )
    return parser


def resolve_python_command() -> list[str]:
    if shutil.which("uv"):
        return ["uv", "run", "python3"]
    return [sys.executable]


def run_experiment(
    experiment: Experiment,
    api_url: str,
    output_dir: Path,
    dry_run: bool,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / f"{experiment.label}.log"
    summary_path = output_dir / f"{experiment.label}.json"

    cmd = [
        *resolve_python_command(),
        str(SIMULATOR_PATH),
        "--api-url",
        api_url,
        "--devices",
        str(experiment.devices),
        "--interval",
        str(experiment.interval_s),
        "--max-inflight",
        str(experiment.max_inflight or experiment.devices),
        "--metrics-interval",
        "5",
        "--duration",
        str(experiment.duration_s),
        "--summary-json",
        str(summary_path),
    ]

    print(f"Running {experiment.label}: {' '.join(cmd)}")
    if dry_run:
        return {
            "label": experiment.label,
            "devices": experiment.devices,
            "interval_s": experiment.interval_s,
            "expected": experiment.verdict,
            "log_path": str(log_path.relative_to(ROOT)),
            "summary_path": str(summary_path.relative_to(ROOT)),
            "requests_per_second": 0.0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "failed_requests": 0,
            "failure_rate": 0.0,
        }

    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        log_file.write(process.stdout)

    if process.returncode != 0:
        raise SystemExit(
            f"Experiment {experiment.label} failed with exit code {process.returncode}. "
            f"Inspect {log_path}."
        )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["label"] = experiment.label
    summary["expected"] = experiment.verdict
    summary["log_path"] = str(log_path.relative_to(ROOT))
    summary["summary_path"] = str(summary_path.relative_to(ROOT))
    return summary


def write_markdown_summary(results: list[dict], output_dir: Path) -> None:
    summary_md = output_dir / "summary.md"
    lines = [
        "# Load Test Results",
        "",
        "| Devices | Interval | Expected | Requests/sec | Avg Latency (ms) | P95 Latency (ms) | Failures | Failure Rate | Raw Log | JSON |",
        "|---------|----------|----------|--------------|------------------|------------------|----------|--------------|---------|------|",
    ]

    for result in results:
        lines.append(
            "| {devices} | {interval_s:.0f}s | {expected} | {requests_per_second:.2f} | "
            "{avg_latency_ms:.2f} | {p95_latency_ms:.2f} | {failed_requests} | "
            "{failure_rate:.2%} | `{log_path}` | `{summary_path}` |".format(**result)
        )

    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir).resolve()

    results = [
        run_experiment(
            Experiment(
                devices=experiment.devices,
                interval_s=experiment.interval_s,
                duration_s=args.duration,
                max_inflight=experiment.max_inflight,
            ),
            api_url=args.api_url,
            output_dir=output_dir,
            dry_run=args.dry_run,
        )
        for experiment in EXPERIMENTS
    ]
    write_markdown_summary(results, output_dir)
    print(f"Wrote {output_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
