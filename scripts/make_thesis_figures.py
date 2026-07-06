#!/usr/bin/env python3
"""Generate vector (PDF) result figures for the thesis from pinned results/ data.

Reads the same pinned artifacts used in Chapter 6 and emits one PDF per figure
under results/figures/, styled for print (LaTeX \\includegraphics). Values are
direct-labeled; the baseline/edge arm is orange and the proposed/improved arm is
blue, matching the interactive figure sheet.

Run:
    uv run --with matplotlib python scripts/make_thesis_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
OUT = RESULTS / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# Palette (print / light surface) — matches the validated interactive sheet.
ARM_A = "#eb6834"   # baseline / edge-only / all-to-cloud
ARM_B = "#2a78d6"   # proposed / two-stage / gated
MUTED = "#898781"
GOOD = "#006300"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e1e0d9"

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 10,
    "axes.edgecolor": "#c3c2b7",
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.labelcolor": INK2,
    "text.color": INK,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "ytick.left": False,
    "pdf.fonttype": 42,   # embed TrueType so text stays selectable/searchable
    "ps.fonttype": 42,
})


def _read(path: str):
    return json.loads((RESULTS / path).read_text())


def _style_ax(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _label_bars(ax, bars, fmt, dy=0.01, fs=9):
    top = ax.get_ylim()[1]
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + dy * top, fmt(h),
                ha="center", va="bottom", fontsize=fs, fontweight="bold", color=INK)


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=150)
    plt.close(fig)
    print(f"  wrote {name}.pdf / .png")


# ---------------------------------------------------------------- Fig 1
def fig1_two_stage():
    d = _read("cloud_model/offline_evaluation.json")
    e, t = d["edge_only"], d["two_stage_edge_then_cloud"]
    cats = ["Precision", "Recall", "F1"]
    edge = [e["precision"], e["recall"], e["f1"]]
    two = [t["precision"], t["recall"], t["f1"]]
    x = range(len(cats)); w = 0.38
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    _style_ax(ax)
    b1 = ax.bar([i - w / 2 for i in x], edge, w, color=ARM_A, zorder=3,
                label="Edge-only (Isolation Forest)")
    b2 = ax.bar([i + w / 2 for i in x], two, w, color=ARM_B, zorder=3,
                label="Two-stage (edge + cloud LSTM-AE)")
    _label_bars(ax, b1, lambda v: f"{v:.2f}")
    _label_bars(ax, b2, lambda v: f"{v:.2f}")
    ax.set_xticks(list(x)); ax.set_xticklabels(cats)
    ax.set_ylim(0, 1.0); ax.set_ylabel("Score")
    ax.legend(frameon=False, fontsize=8.5, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), ncol=2)
    save(fig, "fig1_two_stage_quality")


# ---------------------------------------------------------------- Fig 2
def fig2_fp_suppression():
    d = _read("cloud_model/offline_evaluation.json")
    fp_edge = d["edge_only"]["false_positives"]
    supp = d["edge_fp_suppressed_by_cloud"]
    fp_two = d["two_stage_edge_then_cloud"]["false_positives"]
    dropped = d["true_anomalies_dropped_by_cloud"]
    cats = ["Edge FPs", "Suppressed\nby cloud", "Remaining\nFPs", "True anom.\ndropped"]
    vals = [fp_edge, supp, fp_two, dropped]
    cols = [ARM_A, ARM_B, MUTED, MUTED]
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    _style_ax(ax)
    bars = ax.bar(cats, vals, color=cols, width=0.6, zorder=3)
    ax.set_ylim(0, max(vals) * 1.18); ax.set_ylabel("Readings")
    _label_bars(ax, bars, lambda v: f"{int(v)}")
    save(fig, "fig2_fp_suppression")


# ---------------------------------------------------------------- Fig 3
def fig3_bandwidth():
    g = _read("escalation_bandwidth/gated/gateway-metrics.json")["counters"]
    a = _read("escalation_bandwidth/all/gateway-metrics.json")["counters"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.6, 3.3))
    for ax in (ax1, ax2):
        _style_ax(ax)
    # bytes
    bv = [a["cloud.bytes_sent"], g["cloud.bytes_sent"]]
    b = ax1.bar(["All", "Gated"], bv, color=[ARM_A, ARM_B], width=0.55, zorder=3)
    ax1.set_ylim(0, max(bv) * 1.2)
    ax1.set_title("Payload bytes", fontsize=10, color=INK)
    _label_bars(ax1, b, lambda v: f"{int(v):,}", fs=8.5)
    red_b = 100 * (1 - bv[1] / bv[0])
    ax1.text(1, bv[1] + 0.11 * max(bv), f"−{red_b:.1f}%",
             ha="center", va="bottom", color=GOOD, fontsize=9.5, fontweight="bold")
    # readings
    rv = [a["cloud.forwarded"], g["cloud.forwarded"]]
    b = ax2.bar(["All", "Gated"], rv, color=[ARM_A, ARM_B], width=0.55, zorder=3)
    ax2.set_ylim(0, max(rv) * 1.2)
    ax2.set_title("Readings forwarded", fontsize=10, color=INK)
    _label_bars(ax2, b, lambda v: f"{int(v):,}", fs=8.5)
    red_r = 100 * (1 - rv[1] / rv[0])
    ax2.text(1, rv[1] + 0.11 * max(rv), f"−{red_r:.1f}%",
             ha="center", va="bottom", color=GOOD, fontsize=9.5, fontweight="bold")
    fig.tight_layout()
    save(fig, "fig3_bandwidth")


# ---------------------------------------------------------------- Fig 4
def fig4_decoupling():
    modes = ["rules", "ml", "hybrid"]
    tele, queue = [], []
    for m in modes:
        lt = _read(f"detection_ab/{m}/metrics-summary.json")["latencies"]
        tele.append(lt["telemetry"]["avg_ms"])
        queue.append(lt.get("ml_queue", {}).get("avg_ms", 0.0))
    x = range(len(modes)); w = 0.38
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    _style_ax(ax)
    b1 = ax.bar([i - w / 2 for i in x], tele, w, color=ARM_A, zorder=3,
                label="Ingest hot-path latency (telemetry)")
    b2 = ax.bar([i + w / 2 for i in x], queue, w, color=ARM_B, zorder=3,
                label="Async scoring delay (ml_queue)")
    _label_bars(ax, b1, lambda v: f"{v:.2f}")
    _label_bars(ax, [bb for bb, bv in zip(b2, queue) if bv > 0 for bb in [bb]],
                lambda v: f"{v:.2f}")
    ax.set_xticks(list(x)); ax.set_xticklabels(modes)
    ax.set_ylim(0, max(queue) * 1.2); ax.set_ylabel("Latency (ms)")
    ax.legend(frameon=False, fontsize=8.5, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), ncol=2)
    save(fig, "fig4_async_decoupling")


# ---------------------------------------------------------------- Fig 5
def fig5_overhead():
    def avg(mode):
        runs = []
        for r in (1, 2, 3):
            s = _read(f"ab/high_throughput/{mode}/run-{r}/snapshot.json")["summary"]
            runs.append(s["latencies"]["telemetry"]["avg_ms"])
        return runs
    base, prop = avg("baseline"), avg("proposed")
    means = [sum(base) / 3, sum(prop) / 3]
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    _style_ax(ax)
    bars = ax.bar(["Baseline", "Proposed"], means, color=[ARM_A, ARM_B],
                  width=0.5, zorder=3)
    ax.set_ylim(0, max(max(base), max(prop)) * 1.45)
    ax.set_ylabel("Ingest latency (ms)")
    # mean value labels inside the bars (white), clear of the dots above
    for b, v in zip(bars, means):
        ax.text(b.get_x() + b.get_width() / 2, v - 0.06 * ax.get_ylim()[1],
                f"{v:.2f}", ha="center", va="top", color="white",
                fontsize=9.5, fontweight="bold", zorder=6)
    # individual run dots above each bar
    for i, runs in enumerate((base, prop)):
        ax.scatter([i] * 3, runs, s=30, facecolor="white", edgecolor=INK,
                   linewidth=1.2, zorder=5, label="individual runs" if i == 0 else None)
    delta = means[1] - means[0]
    ax.text(1, max(prop) + 0.10 * ax.get_ylim()[1], f"+{delta:.2f} ms",
            ha="center", color=GOOD, fontsize=9.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.text(0.5, -0.16, "matched throughput ≈ 202 msg/s (3 runs each)",
            transform=ax.transAxes, ha="center", fontsize=8, color=INK2)
    save(fig, "fig5_ingest_overhead")


def main():
    print(f"Writing figures to {OUT}")
    fig1_two_stage()
    fig2_fp_suppression()
    fig3_bandwidth()
    fig4_decoupling()
    fig5_overhead()
    print("Done.")


if __name__ == "__main__":
    main()
