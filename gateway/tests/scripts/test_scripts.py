"""Script smoke tests."""
from __future__ import annotations

import subprocess
from pathlib import Path


def test_shell_scripts_parse() -> None:
    scripts = [
        "scripts/lib/common.sh",
        "scripts/run_anomaly_detection_test.sh",
        "scripts/run_baseline_test.sh",
        "scripts/run_cloud_verification_test.sh",
        "scripts/run_detection_ab_test.sh",
        "scripts/run_escalation_bandwidth_test.sh",
        "scripts/run_high_throughput_ab_test.sh",
        "scripts/run_proposed_test.sh",
    ]
    result = subprocess.run(["bash", "-n", *scripts], check=False, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_export_script_mentions_report_and_snapshot_paths() -> None:
    source = Path("scripts/export_results.py").read_text()
    assert '"snapshot.json"' in source
    assert '"report.md"' in source
