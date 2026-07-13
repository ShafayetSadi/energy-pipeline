# Results

This directory holds the curated evidence produced by the current evaluation
workflow. Human-readable reports and selected JSON evidence are tracked;
simulator logs, raw snapshots, and other reproducible run artifacts are ignored.

## Recommended evaluation order

Run fast validation before the Docker experiments:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest gateway/tests/scripts/test_scripts.py -q
UV_CACHE_DIR=/tmp/uv-cache uv run pytest gateway/tests cloud/tests -q
```

Then run only the lanes whose evidence is being refreshed:

| Order | Evaluation lane | Command | Primary output |
| ---: | --- | --- | --- |
| 1 | Clean baseline vs proposed overhead | `REPETITIONS=3 just ab-high-throughput` | `ab/high_throughput/{baseline,proposed}/run-*` |
| 2 | Proposed rule/validation evidence | `just anomaly-detection` | `anomaly_detection/proposed/` |
| 3 | Edge-model offline quality | `uv run python scripts/train_anomaly_model.py --evaluate` | `anomaly_model/offline_evaluation.json` |
| 4 | Rules vs ML vs hybrid | `bash scripts/run_detection_ab_test.sh` | `detection_ab/{rules,ml,hybrid}/` |
| 5 | Gated vs all-to-cloud bandwidth | `bash scripts/run_escalation_bandwidth_test.sh` | `escalation_bandwidth/{gated,all}/` |
| 6 | Cloud-model offline quality | `uv run --group ml-train python scripts/train_cloud_lstm.py --evaluate` | `cloud_model/offline_evaluation.json` |
| 7 | Live cloud verification | `bash scripts/run_cloud_verification_test.sh` | `cloud_verification/` |
| 8 | Thesis figures | `just figures` | `figures/` |

The legacy `results/baseline/` and `results/proposed/` reports come from the
older exploratory `just baseline` / `just proposed` workflow. Keep them as
historical evidence, but use the isolated repeated A/B folders for headline
comparisons.

## Evidence boundaries

- High-throughput A/B runs reset the database for every arm and use the same
  scenario. They support ingestion-overhead and throughput comparisons.
- The proposed anomaly run is functionality evidence, not a baseline
  performance comparison.
- Edge/cloud precision, recall, and false-positive claims come from labeled
  offline evaluation; the online runs primarily measure operational behavior.
- Bandwidth numbers are JSON application-payload bytes, not full wire bytes.
- Storage reduction, field metering accuracy, production readiness, and
  Kubernetes elasticity are not established by the current results.

## Thesis figures (`results/figures/`)

`scripts/make_thesis_figures.py` renders the headline result charts from the
pinned JSON artifacts in this directory. Each figure is written as both a
vector `.pdf` (for LaTeX `\includegraphics`) and a `.png` (for quick
preview / Word). Regenerate after re-measuring:

```bash
uv run --with matplotlib python scripts/make_thesis_figures.py
```

The generator reads only the tracked result JSONs, so the figures stay in sync
with the numbers reported in Chapter 6. Text is embedded as TrueType
(`pdf.fonttype = 42`) so labels remain selectable/searchable in the PDF.

| File | Figure | Source data | Chapter |
| --- | --- | --- | --- |
| `fig1_two_stage_quality` | Edge-only vs two-stage precision/recall/F1 (**offline**) | `cloud_model/offline_evaluation.json` | 6.7.3 |
| `fig2_fp_suppression` | Cloud false-positive suppression (796 → 643 / 153 / 13, **offline**) | `cloud_model/offline_evaluation.json` | 6.7.3 |
| `fig3_bandwidth` | Score-gated vs all-to-cloud bandwidth (−53.1% bytes, −54.8% readings) | `escalation_bandwidth/{all,gated}/gateway-metrics.json` | 6.7.2 |
| `fig4_async_decoupling` | Ingest hot path vs async `ml_queue` delay across rules/ml/hybrid | `detection_ab/{rules,ml,hybrid}/metrics-summary.json` | 6.7.1 |
| `fig5_ingest_overhead` | Baseline vs proposed ingest latency at matched throughput (3 runs each) | `ab/high_throughput/{baseline,proposed}/run-*/snapshot.json` | 6.2 |

Palette: baseline/edge/all arm in orange, proposed/improved/gated arm in blue;
every value is direct-labeled. An interactive theme-aware version of the same
five charts (with per-figure data tables) is also available as a Claude
Artifact.

### LaTeX usage

```latex
% preamble: \usepackage{graphicx}
\begin{figure}[t]
  \centering
  \includegraphics[width=0.85\linewidth]{results/figures/fig1_two_stage_quality.pdf}
  \caption{Offline two-stage detection quality on the held-out set
           (8\,000 normal / 2\,000 anomalies): the cloud LSTM-AE verifier
           raises precision from 0.66 to 0.91 at near-identical recall.}
  \label{fig:two-stage}
\end{figure}
```

Use `width=\linewidth` for the two-panel `fig3_bandwidth`. Caption honesty:
label figs 1–2 as **offline** (labeled held-out set, not the live runs); figs
3–4 are the **online** A/B runs, and fig 4's point is the *decoupling* of ML
cost from the ingest hot path, not batching amortisation.
