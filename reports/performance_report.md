# Performance Report

Benchmark results measure deterministic synthetic event replay through the Python matching engine.
Results depend on CPU, Python version, operating system, and current machine load.

## Results

| event_count | processed_events | runtime_seconds | events_per_second | avg_latency_us | p50_latency_us | p95_latency_us | p99_latency_us | peak_memory_mb | trades | resting_orders |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | 1000 | 0.091 | 11021.725 | 16.238 | 12 | 36.710 | 62.150 | 0.639 | 742 | 113 |
| 10000 | 10000 | 0.843 | 11868.575 | 15.890 | 12.800 | 37 | 57.101 | 6.131 | 8159 | 415 |
| 100000 | 100000 | 8.696 | 11499.863 | 17.040 | 14 | 39.700 | 63.500 | 60.919 | 86118 | 929 |

## Methodology

- Synthetic market events are generated with a fixed random seed.
- Each event is converted into the same order/cancel/modify models used by market replay.
- Latency is measured around matching-engine event processing only.
- Peak memory is measured with `tracemalloc` during each benchmark run.
