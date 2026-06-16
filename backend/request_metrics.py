from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

CSV_HEADER = [
    "timestamp",
    "method",
    "path",
    "status_code",
    "processing_time_ms",
    "db_execute_ms",
    "db_commit_ms",
    "total_handler_ms",
]


@dataclass(frozen=True)
class RequestMetric:
    timestamp: str
    method: str
    path: str
    status_code: int
    processing_time_ms: float
    db_execute_ms: float
    db_commit_ms: float
    total_handler_ms: float


class RequestMetricsRecorder:
    def __init__(self, csv_path: str) -> None:
        self.path = Path(csv_path)
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def _ensure_header(self) -> None:
        if self.path.exists() and self.path.stat().st_size > 0:
            with self.path.open("r", newline="", encoding="utf-8") as csv_file:
                reader = csv.reader(csv_file)
                existing_header = next(reader, [])
            if existing_header == CSV_HEADER:
                return

        with self.path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(CSV_HEADER)

    def record(self, metric: RequestMetric) -> None:
        row = [
            metric.timestamp,
            metric.method,
            metric.path,
            metric.status_code,
            f"{metric.processing_time_ms:.3f}",
            f"{metric.db_execute_ms:.3f}",
            f"{metric.db_commit_ms:.3f}",
            f"{metric.total_handler_ms:.3f}",
        ]

        with self._lock:
            with self.path.open("a", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(row)


def default_metrics_path() -> str:
    return os.getenv("REQUEST_METRICS_CSV_PATH", "runtime/request_metrics.csv")


def build_request_metric(
    *,
    method: str,
    path: str,
    status_code: int,
    processing_time_ms: float,
    db_execute_ms: float = 0.0,
    db_commit_ms: float = 0.0,
    total_handler_ms: float = 0.0,
) -> RequestMetric:
    return RequestMetric(
        timestamp=datetime.now(timezone.utc).isoformat(),
        method=method,
        path=path,
        status_code=status_code,
        processing_time_ms=processing_time_ms,
        db_execute_ms=db_execute_ms,
        db_commit_ms=db_commit_ms,
        total_handler_ms=total_handler_ms,
    )
