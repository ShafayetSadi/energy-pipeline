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
