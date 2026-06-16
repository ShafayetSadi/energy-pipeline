#!/usr/bin/env python3
"""Export a Markdown + JSON summary comparing gateway metrics.

Run this after at least one ``run_proposed_test.sh`` (and optionally
``run_baseline_test.sh``) to produce a comparison report in ``results/``.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


def fetch(url: str) -> dict:
    with urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_report(base_url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = fetch(f"{base_url}/api/v1/metrics/summary")
    events_by_sev = fetch(f"{base_url}/api/v1/metrics/events-by-severity")
    quality_by_type = fetch(f"{base_url}/api/v1/metrics/quality-by-type")

    snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "summary": summary,
        "events_by_severity": events_by_sev,
        "quality_by_type": quality_by_type,
    }
    (output_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=2))

    counters = summary["counters"]
    latencies = summary["latencies"]
    lines = [
        "# Edge Gateway Run Report",
        "",
        f"- Captured at: {snapshot['captured_at']}",
        f"- Source: {base_url}",
        f"- Uptime: {summary['uptime_seconds']:.1f}s",
        "",
        "## Counters",
        "",
        "| Counter | Value |",
        "| --- | ---: |",
    ]
    for name, value in sorted(counters.items()):
        lines.append(f"| `{name}` | {value} |")

    lines.extend(
        [
            "",
            "## Latencies (ms)",
            "",
            "| Operation | Count | Avg | p50 | p95 | p99 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for op, stats in sorted(latencies.items()):
        lines.append(
            f"| `{op}` | {int(stats['count'])} | {stats['avg_ms']:.2f} | "
            f"{stats['p50_ms']:.2f} | {stats['p95_ms']:.2f} | {stats['p99_ms']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Events by severity (24h)",
            "",
            "| Severity | Count |",
            "| --- | ---: |",
        ]
    )
    for sev, count in sorted(events_by_sev.items()):
        lines.append(f"| {sev} | {count} |")

    lines.extend(
        [
            "",
            "## Validation errors by type (24h)",
            "",
            "| Error type | Count |",
            "| --- | ---: |",
        ]
    )
    for err, count in sorted(quality_by_type.items()):
        lines.append(f"| `{err}` | {count} |")

    (output_dir / "report.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {output_dir / 'report.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export gateway run report")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if not parsed.scheme:
        print("--base-url must include scheme (e.g. http://localhost:8000)", file=sys.stderr)
        sys.exit(2)
    write_report(args.base_url, Path(args.output_dir))


if __name__ == "__main__":
    main()
