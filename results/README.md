# Results

This directory holds per-run snapshots produced by ``scripts/export_results.py``
after running ``scripts/run_baseline_test.sh`` and
``scripts/run_proposed_test.sh``.

Suggested workflow:

1. ``./scripts/run_baseline_test.sh``
2. ``python scripts/export_results.py --output-dir results/baseline``
3. ``./scripts/run_proposed_test.sh``
4. ``python scripts/export_results.py --output-dir results/proposed``

Compare ``results/baseline/report.md`` with ``results/proposed/report.md`` to
generate the thesis evaluation tables.
