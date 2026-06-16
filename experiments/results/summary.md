# Load Test Results

| Devices | Interval | Expected | Requests/sec | Avg Latency (ms) | P95 Latency (ms) | Failures | Failure Rate | Raw Log | JSON |
|---------|----------|----------|--------------|------------------|------------------|----------|--------------|---------|------|
| 100 | 1s | stable | 99.27 | 5.67 | 7.61 | 33 | 0.28% | `experiments/results/100-devices-1s.log` | `experiments/results/100-devices-1s.json` |
| 300 | 1s | moderate load | 234.07 | 268.89 | 1874.06 | 0 | 0.00% | `experiments/results/300-devices-1s.log` | `experiments/results/300-devices-1s.json` |
| 500 | 1s | stress | 191.14 | 1444.23 | 5535.30 | 106 | 0.46% | `experiments/results/500-devices-1s.log` | `experiments/results/500-devices-1s.json` |
| 1000 | 1s | break point | 142.22 | 5186.99 | 10371.29 | 1613 | 9.28% | `experiments/results/1000-devices-1s.log` | `experiments/results/1000-devices-1s.json` |
