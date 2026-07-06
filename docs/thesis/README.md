# Thesis Writing Guide

This folder contains the working draft of the thesis for the **Energy Edge Monitoring** project.

## Table of contents

See [`00_table_of_contents.md`](./00_table_of_contents.md).

---

## Recommended writing workflow

Write in two layers:

1. **Project notes** while building and testing
2. **Formal thesis text** after enough evidence is collected

For each work session, record:

- what you built
- why it was needed
- files/modules changed
- problems faced
- how you solved them
- test outputs, screenshots, metrics
- which thesis chapter the work supports

## Suggested evidence to collect

- architecture diagrams
- STM32 node photos or block diagrams
- MQTT topic/payload examples
- API screenshots
- database schema snapshots
- Grafana screenshots
- baseline vs proposed reports
- latency / throughput / storage tables
- alert/event examples
- limitations and failed experiments

## Result figures

Publication-ready result charts live in ``results/figures/`` as vector PDFs
(for LaTeX ``\includegraphics``) plus PNG previews, regenerated from the pinned
result JSONs by ``scripts/make_thesis_figures.py``. See ``results/README.md``
for the figure-to-chapter mapping and LaTeX usage snippet.
