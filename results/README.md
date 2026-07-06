# Results

This directory holds curated per-run reports produced by
``scripts/export_results.py`` after running ``scripts/run_baseline_test.sh`` and
``scripts/run_proposed_test.sh``.

Suggested workflow:

1. ``just baseline``
2. ``just proposed``

Compare ``results/baseline/report.md`` with ``results/proposed/report.md`` to
generate the thesis evaluation tables.

The scripts export ``report.md`` automatically. Generated ``snapshot.json``
files and raw logs are local artifacts and are ignored by git.

## Thesis figures (``results/figures/``)

``scripts/make_thesis_figures.py`` renders the headline result charts from the
pinned JSON artifacts in this directory. Each figure is written as both a
vector ``.pdf`` (for LaTeX ``\includegraphics``) and a ``.png`` (for quick
preview / Word). Regenerate after re-measuring:

```bash
uv run --with matplotlib python scripts/make_thesis_figures.py
```

The generator reads only the tracked result JSONs, so the figures stay in sync
with the numbers reported in Chapter 6. Text is embedded as TrueType
(``pdf.fonttype = 42``) so labels remain selectable/searchable in the PDF.

| File | Figure | Source data | Chapter |
| --- | --- | --- | --- |
| ``fig1_two_stage_quality`` | Edge-only vs two-stage precision/recall/F1 (**offline**) | ``cloud_model/offline_evaluation.json`` | 6.7.3 |
| ``fig2_fp_suppression`` | Cloud false-positive suppression (796 → 643 / 153 / 13, **offline**) | ``cloud_model/offline_evaluation.json`` | 6.7.3 |
| ``fig3_bandwidth`` | Score-gated vs all-to-cloud bandwidth (−53.1% bytes, −54.8% readings) | ``escalation_bandwidth/{all,gated}/gateway-metrics.json`` | 6.7.2 |
| ``fig4_async_decoupling`` | Ingest hot path vs async ``ml_queue`` delay across rules/ml/hybrid | ``detection_ab/{rules,ml,hybrid}/metrics-summary.json`` | 6.7.1 |
| ``fig5_ingest_overhead`` | Baseline vs proposed ingest latency at matched throughput (3 runs each) | ``ab/high_throughput/{baseline,proposed}/run-*/snapshot.json`` | 6.2 |

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

Use ``width=\linewidth`` for the two-panel ``fig3_bandwidth``. Caption honesty:
label figs 1–2 as **offline** (labeled held-out set, not the live runs); figs
3–4 are the **online** A/B runs, and fig 4's point is the *decoupling* of ML
cost from the ingest hot path, not batching amortisation.
